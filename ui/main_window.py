"""
Cotizador SAP B1 - Versión sin logs
"""
import re
import sys
import os
import tempfile
import time
import subprocess
import pandas as pd
from datetime import datetime
from PyPDF2 import PdfWriter, PdfReader
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QTableWidget, 
                            QTableWidgetItem, QMessageBox, QLineEdit, QGroupBox, 
                            QDialog, QDoubleSpinBox, QComboBox, QFileDialog, 
                            QGridLayout, QHeaderView, QFormLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QEvent
from PyQt6.QtGui import QFont, QColor
from pathlib import Path
from reportlab.pdfgen import canvas
import fitz
import win32com.client as win32
from api.sap_client import SAPClient
from config.settings import (SESSION_TIMEOUT_MINUTES, COMPANY_NAME, COMPANY_RFC, 
                           COMPANY_ADDRESS, COMPANY_PHONE, COMPANY_EMAIL, 
                           COMPANY_WEBSITE, DESCUENTOS_MAXIMOS_POR_GRUPO, 
                           ALERTA_DESCUENTO_COLOR, DESCUENTO_BLOQUEADO_COLOR)

try:
    import qrcode
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, 
                                   Paragraph, Spacer, Image, PageBreak)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
except ImportError:
    QMessageBox.critical(None, "Error", "Faltan librerías de reportes")
    sys.exit(1)


class TablaMejorada(QTableWidget):
    """Tabla mejorada con copiar/pegar"""
    
    def __init__(self):
        super().__init__()
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: white;
                alternate-background-color: #f9f9f9;
            }
            QHeaderView::section {
                background-color: #455A64;
                color: white;
                padding: 4px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
        """)
    
    def keyPressEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_C:
            self.copiar_seleccion()
        else:
            super().keyPressEvent(event)
    
    def copiar_seleccion(self):
        rangos = self.selectedRanges()
        if not rangos:
            return
        
        lineas = []
        for r in rangos:
            for i in range(r.topRow(), r.bottomRow() + 1):
                datos = [self.item(i, j).text() if self.item(i, j) else "" 
                        for j in range(r.leftColumn(), r.rightColumn() + 1)]
                lineas.append("\t".join(datos))
        
        QApplication.clipboard().setText("\n".join(lineas))


class BusquedaWorker(QThread):
    """Worker thread para búsqueda de artículos"""
    finalizado = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, sap_client, termino):
        super().__init__()
        self.sap_client = sap_client
        self.termino = termino
    
    def run(self):
        try:
            filter_str = f"contains(ItemCode, '{self.termino}') or contains(ItemName, '{self.termino}')"
            filter_str += f" and Frozen eq 'tNO' and Valid eq 'tYES'"
            
            articulos = self.sap_client.search_items(self.termino, filter_str)
            self.finalizado.emit(articulos)
        except Exception as e:
            self.error.emit(f"Error búsqueda: {str(e)}")


class VentanaPrincipal(QMainWindow):
    """Ventana principal del cotizador"""
    
    def __init__(self, credenciales):
        super().__init__()
        self.sap_client = SAPClient()
        self.credenciales = credenciales
        self.articulos_cotizacion = []
        self.articulos_datos_completos = []
        self.ultimo_pdf_generado = None
        
        self.descuentos_maximos = DESCUENTOS_MAXIMOS_POR_GRUPO
        self.nombre_agente = "Agente"
        self.email_agente = COMPANY_EMAIL
        
        from config.settings import CLIENTES_AUTORIZADOS
        self.clientes_autorizados = CLIENTES_AUTORIZADOS
        
        self.init_ui()
        
        # Timer de inactividad
        self.timer_inactividad = QTimer(self)
        self.timer_inactividad.timeout.connect(self.timeout_sesion)
        self.tiempo_limite_ms = SESSION_TIMEOUT_MINUTES * 60 * 1000
        self.timer_inactividad.start(self.tiempo_limite_ms)
        
        QApplication.instance().installEventFilter(self)
        self.conectar_sap()
    
    def eventFilter(self, source, event):
        if event.type() in (QEvent.Type.MouseMove, QEvent.Type.KeyPress, 
                           QEvent.Type.MouseButtonPress):
            if self.timer_inactividad.isActive():
                self.timer_inactividad.start(self.tiempo_limite_ms)
        return super().eventFilter(source, event)
    
    def timeout_sesion(self):
        self.timer_inactividad.stop()
        self.sap_client.logout()
        QMessageBox.warning(
            self, "Sesión Expirada",
            f"Inactividad detectada ({SESSION_TIMEOUT_MINUTES} min).\nSesión cerrada."
        )
        self.ejecutar_relogin()
    
    def ejecutar_relogin(self):
        from ui.login_dialog import LoginDialog
        self.setEnabled(False)
        login_dialog = LoginDialog(self)
        
        if login_dialog.exec() == QDialog.DialogCode.Accepted:
            self.credenciales = login_dialog.credenciales
            self.setEnabled(True)
            self.conectar_sap()
            self.timer_inactividad.start(self.tiempo_limite_ms)
        else:
            sys.exit()
    
    def closeEvent(self, event):
        self.sap_client.logout()
        event.accept()
    
    def init_ui(self):
        self.setWindowTitle("Cotizador SAP B1 - Versión Segura")
        self.resize(1150, 800)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Encabezado
        top_layout = QHBoxLayout()
        self.lbl_status = QLabel("Conectando...")
        self.lbl_status.setStyleSheet("font-weight: bold; color: #FF9800;")
        
        btn_logout = QPushButton("Cerrar Sesión")
        btn_logout.setStyleSheet("background-color: #f44336; color: white;")
        btn_logout.clicked.connect(lambda: (self.sap_client.logout(), self.ejecutar_relogin()))
        
        top_layout.addWidget(self.lbl_status)
        top_layout.addStretch()
        top_layout.addWidget(btn_logout)
        layout.addLayout(top_layout)
        
        # Datos del Cliente
        grp_cli = QGroupBox("Datos del Cliente")
        grp_cli.setFixedHeight(140)
        grid = QGridLayout()
        grid.setContentsMargins(5, 5, 5, 5)
        
        self.cmb_cliente = QComboBox()
        self.cmb_cliente.addItem("-- Seleccionar Cliente --", None)
        for cliente in self.clientes_autorizados:
            self.cmb_cliente.addItem(
                f"{cliente['CardCode']} - {cliente['CardName']}", cliente
            )
        self.cmb_cliente.currentIndexChanged.connect(self.on_cliente_seleccionado)
        self.cmb_cliente.setMinimumWidth(400)
        
        self.btn_refresh_cliente = QPushButton("↻ Actualizar desde SAP")
        self.btn_refresh_cliente.setStyleSheet("background-color: #2196F3; color: white;")
        self.btn_refresh_cliente.clicked.connect(self.refrescar_cliente_desde_sap)
        self.btn_refresh_cliente.setEnabled(False)
        
        self.txt_cod_cli = QLineEdit()
        self.txt_cod_cli.setPlaceholderText("Código")
        self.txt_cod_cli.setReadOnly(True)
        self.txt_cod_cli.setFixedWidth(100)
        
        self.txt_nom_cli = QLineEdit()
        self.txt_nom_cli.setPlaceholderText("Nombre Cliente")
        self.txt_nom_cli.setReadOnly(True)
        
        self.txt_rfc = QLineEdit()
        self.txt_rfc.setPlaceholderText("RFC")
        self.txt_rfc.setReadOnly(True)
        
        self.txt_dir = QLineEdit()
        self.txt_dir.setPlaceholderText("Dirección")
        self.txt_dir.setReadOnly(True)
        
        self.txt_cond = QLineEdit()
        self.txt_cond.setPlaceholderText("Condiciones de Pago")
        self.txt_cond.setReadOnly(True)
        
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("Email")
        self.txt_email.setReadOnly(True)
        
        self.txt_tel = QLineEdit()
        self.txt_tel.setPlaceholderText("Teléfono")
        self.txt_tel.setReadOnly(True)
        
        grid.addWidget(QLabel("Seleccionar Cliente:"), 0, 0)
        grid.addWidget(self.cmb_cliente, 0, 1, 1, 3)
        grid.addWidget(self.btn_refresh_cliente, 0, 4, 1, 2)
        grid.addWidget(QLabel("Código:"), 1, 0)
        grid.addWidget(self.txt_cod_cli, 1, 1)
        grid.addWidget(QLabel("Nombre:"), 1, 2)
        grid.addWidget(self.txt_nom_cli, 1, 3, 1, 3)
        grid.addWidget(QLabel("RFC:"), 2, 0)
        grid.addWidget(self.txt_rfc, 2, 1)
        grid.addWidget(QLabel("Dirección:"), 2, 2)
        grid.addWidget(self.txt_dir, 2, 3, 1, 3)
        grid.addWidget(QLabel("Condición:"), 3, 0)
        grid.addWidget(self.txt_cond, 3, 1)
        grid.addWidget(QLabel("Email:"), 3, 2)
        grid.addWidget(self.txt_email, 3, 3)
        grid.addWidget(QLabel("Tel:"), 3, 4)
        grid.addWidget(self.txt_tel, 3, 5)
        
        grp_cli.setLayout(grid)
        layout.addWidget(grp_cli)
        
        # Búsqueda de Artículos
        grp_art = QGroupBox("Búsqueda de Artículos (Solo Activos)")
        lay_art = QVBoxLayout()
        
        h_search = QHBoxLayout()
        self.txt_search_art = QLineEdit()
        self.txt_search_art.setPlaceholderText("Código o Nombre del artículo...")
        self.txt_search_art.returnPressed.connect(self.buscar_articulos)
        h_search.addWidget(self.txt_search_art)
        
        self.btn_search = QPushButton("Buscar")
        self.btn_search.clicked.connect(self.buscar_articulos)
        h_search.addWidget(self.btn_search)
        lay_art.addLayout(h_search)
        
        self.tbl_search = TablaMejorada()
        self.tbl_search.setColumnCount(9)
        self.tbl_search.setHorizontalHeaderLabels([
            "Código", "Nombre", "Grupo", "Stock Total", "Comprometido", 
            "Pedido", "Disponible", "L1 MXN", "L3 USD"
        ])
        self.tbl_search.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_search.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay_art.addWidget(self.tbl_search)
        
        h_opts = QHBoxLayout()
        self.spin_cant = QDoubleSpinBox()
        self.spin_cant.setValue(1)
        self.spin_cant.setRange(0.01, 99999)
        
        self.cmb_lista = QComboBox()
        self.cmb_lista.addItems(["Lista 1 MXN", "Lista 3 USD"])
        self.cmb_lista.currentIndexChanged.connect(self.update_currency)
        
        self.cmb_moneda = QComboBox()
        self.cmb_moneda.addItems(["MXN", "USD"])
        self.cmb_moneda.setEnabled(False)
        
        self.btn_add = QPushButton("➕ Agregar a Cotización")
        self.btn_add.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_add.clicked.connect(self.agregar_a_cotizacion)
        
        h_opts.addWidget(QLabel("Cantidad:"))
        h_opts.addWidget(self.spin_cant)
        h_opts.addWidget(QLabel("Lista:"))
        h_opts.addWidget(self.cmb_lista)
        h_opts.addWidget(self.cmb_moneda)
        h_opts.addStretch()
        h_opts.addWidget(self.btn_add)
        lay_art.addLayout(h_opts)
        
        grp_art.setLayout(lay_art)
        layout.addWidget(grp_art, stretch=1)
        
        # Artículos en Cotización
        grp_cot = QGroupBox("Artículos en Cotización")
        lay_cot = QVBoxLayout()
        
        self.tbl_cot = TablaMejorada()
        self.tbl_cot.setColumnCount(11)
        self.tbl_cot.setHorizontalHeaderLabels([
            "Código", "Grupo", "Desc Max %", "Cant.", "Unidad", "Moneda", 
            "Precio Lista", "Desc %", "Precio c/Descuento", "Subtotal", "Total"
        ])
        self.tbl_cot.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_cot.itemChanged.connect(self.recalcular_celda)
        lay_cot.addWidget(self.tbl_cot)
        
        h_bottom = QHBoxLayout()
        self.btn_del = QPushButton("Eliminar Fila")
        self.btn_del.setStyleSheet("background-color: #f44336; color: white;")
        self.btn_del.clicked.connect(self.eliminar_fila)
        
        self.btn_clean = QPushButton("Limpiar Todo")
        self.btn_clean.clicked.connect(self.limpiar_todo)
        
        self.lbl_totals = QLabel("Subtotal: $0.00 | IVA: $0.00 | TOTAL: $0.00")
        self.lbl_totals.setStyleSheet(
            "font-size: 14px; font-weight: bold; padding: 5px; "
            "border: 1px solid #ccc; background-color: #E3F2FD;"
        )
        
        self.btn_pdf = QPushButton("📄 Generar PDF")
        self.btn_pdf.setStyleSheet(
            "background-color: #673AB7; color: white; font-weight: bold; padding: 8px;"
        )
        self.btn_pdf.clicked.connect(self.generar_pdf)
        
        self.btn_excel = QPushButton("📊 Descargar Excel")
        self.btn_excel.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;"
        )
        self.btn_excel.clicked.connect(self.descargar_excel)
        self.btn_excel.setEnabled(False)
        
        self.btn_email = QPushButton("📧 Preparar Email")
        self.btn_email.setStyleSheet(
            "background-color: #FF9800; color: white; font-weight: bold; padding: 8px;"
        )
        self.btn_email.clicked.connect(self.preparar_email_outlook)
        self.btn_email.setEnabled(False)
        
        h_bottom.addWidget(self.btn_del)
        h_bottom.addWidget(self.btn_clean)
        h_bottom.addStretch()
        h_bottom.addWidget(self.lbl_totals)
        h_bottom.addWidget(self.btn_excel)
        h_bottom.addWidget(self.btn_pdf)
        h_bottom.addWidget(self.btn_email)
        lay_cot.addLayout(h_bottom)
        
        grp_cot.setLayout(lay_cot)
        layout.addWidget(grp_cot, stretch=1)
    
    def conectar_sap(self):
        try:
            success = self.sap_client.login(self.credenciales)
            if not success:
                raise Exception("Login rechazado por SAP B1")
            
            user_info = self.sap_client.get_user_info(self.credenciales["UserName"])
            if user_info:
                self.nombre_agente = user_info.get("UserName", self.credenciales["UserName"])
                self.email_agente = user_info.get("eMail", COMPANY_EMAIL)
            
            self.lbl_status.setText(f"✓ Conectado como {self.nombre_agente}")
            self.lbl_status.setStyleSheet("font-weight: bold; color: #4CAF50;")
        except Exception as e:
            QMessageBox.critical(self, "Error Fatal", f"No se pudo conectar:\n{e}")
    
    def update_currency(self):
        self.cmb_moneda.setCurrentIndex(1 if self.cmb_lista.currentIndex() == 1 else 0)
    
    def on_cliente_seleccionado(self, index):
        if index == 0:
            self.limpiar_datos_cliente()
            self.btn_refresh_cliente.setEnabled(False)
            return
        
        cliente = self.cmb_cliente.currentData()
        if cliente:
            self.cargar_datos_cliente(cliente)
            self.btn_refresh_cliente.setEnabled(True)
            self.timer_inactividad.start(self.tiempo_limite_ms)
    
    def obtener_descuento_maximo(self, grupo_codigo: str) -> float:
        descuento_max = self.descuentos_maximos.get(
            str(grupo_codigo), 
            self.descuentos_maximos.get("DEFAULT", 50.0)
        )
        return descuento_max
    
    def cargar_datos_cliente(self, cliente: dict):
        self.txt_cod_cli.setText(cliente.get("CardCode", ""))
        self.txt_nom_cli.setText(cliente.get("CardName", ""))
        self.txt_rfc.setText(cliente.get("FederalTaxID", ""))
        self.txt_email.setText(cliente.get("EmailAddress", ""))
        self.txt_tel.setText(cliente.get("Phone1", ""))
        self.txt_cond.setText(str(cliente.get("PaymentTermsCode", "")))
        
        addr = f"{cliente.get('Address', '')}, {cliente.get('City', '')}, {cliente.get('State', '')}"
        self.txt_dir.setText(addr)
    
    def limpiar_datos_cliente(self):
        self.txt_cod_cli.clear()
        self.txt_nom_cli.clear()
        self.txt_rfc.clear()
        self.txt_email.clear()
        self.txt_tel.clear()
        self.txt_cond.clear()
        self.txt_dir.clear()
    
    def refrescar_cliente_desde_sap(self):
        codigo_cliente = self.txt_cod_cli.text().strip()
        if not codigo_cliente:
            return
        
        try:
            self.btn_refresh_cliente.setEnabled(False)
            self.btn_refresh_cliente.setText("Actualizando...")
            
            clientes = self.sap_client.search_business_partners(codigo_cliente)
            if not clientes:
                QMessageBox.warning(self, "Sin Resultados", "No se encontró el cliente en SAP")
                return
            
            cliente_actualizado = clientes[0]
            self.cargar_datos_cliente(cliente_actualizado)
            QMessageBox.information(self, "Actualizado", "Datos actualizados desde SAP correctamente")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo actualizar desde SAP:\n{e}")
        finally:
            self.btn_refresh_cliente.setEnabled(True)
            self.btn_refresh_cliente.setText("↻ Actualizar desde SAP")
            self.timer_inactividad.start(self.tiempo_limite_ms)
    
    def buscar_articulos(self):
        term = self.txt_search_art.text().strip()
        if not term:
            return
        
        term = term[:20]
        if not re.match(r"^[\w\sáéíóúñÁÉÍÓÚÑ\-]+$", term, re.UNICODE):
            QMessageBox.warning(
                self, "Entrada inválida", 
                "Solo se permiten letras, números, espacios y guiones."
            )
            self.txt_search_art.setFocus()
            return
        
        self.btn_search.setEnabled(False)
        self.txt_search_art.setEnabled(False)
        
        self.worker = BusquedaWorker(self.sap_client, term)
        self.worker.finalizado.connect(self.mostrar_resultados)
        self.worker.error.connect(lambda e: QMessageBox.warning(self, "Error", e))
        self.worker.finished.connect(lambda: self.btn_search.setEnabled(True))
        self.worker.finished.connect(lambda: self.txt_search_art.setEnabled(True))
        self.worker.finished.connect(lambda: self.txt_search_art.setFocus())
        self.worker.start()
        
        self.timer_inactividad.start(self.tiempo_limite_ms)
    
    def mostrar_resultados(self, data):
        self.articulos_datos_completos = data
        self.tbl_search.setRowCount(len(data))
        
        if not data:
            QMessageBox.information(self, "Info", "No se encontraron artículos activos.")
            return
        
        for i, row in enumerate(data):
            stk = float(row.get("QuantityOnStock", 0))
            cmp = float(row.get("QuantityOrderedByCustomers", 0))
            ped = float(row.get("QuantityOrderedFromVendors", 0))
            disp = stk - cmp + ped
            grupo = row.get("ItemsGroupCode", "NA")
            
            prices = {
                p["PriceList"]: p.get("Price", 0) if p["PriceList"] == 2 
                               else p.get("AdditionalPrice1", 0)
                for p in row.get("ItemPrices", [])
            }
            
            color_fila = QColor("red") if disp <= 0 else QColor("green")
            fuente_fila = QFont()
            fuente_fila.setBold(True)
            
            items_fila = [
                QTableWidgetItem(row.get("ItemCode")),
                QTableWidgetItem(row.get("ItemName", "")),
                QTableWidgetItem(str(grupo)),
                QTableWidgetItem(f"{stk:.2f}"),
                QTableWidgetItem(f"{cmp:.2f}"),
                QTableWidgetItem(f"{ped:.2f}"),
                QTableWidgetItem(f"{disp:.2f}"),
                QTableWidgetItem(f"{prices.get(1, 0):.2f}"),
                QTableWidgetItem(f"{prices.get(3, 0):.2f}")
            ]
            
            for col, item in enumerate(items_fila):
                item.setForeground(color_fila)
                item.setFont(fuente_fila)
                self.tbl_search.setItem(i, col, item)
        
        self.tbl_search.resizeColumnsToContents()
        self.tbl_search.scrollToTop()
    
    def agregar_a_cotizacion(self):
        row = self.tbl_search.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Aviso", "Selecciona un artículo primero")
            return
        
        raw = self.articulos_datos_completos[row]
        idx_list = self.cmb_lista.currentIndex()
        col_price = 7 + idx_list
        
        try:
            p_txt = self.tbl_search.item(row, col_price).text()
            precio = float(p_txt.replace("$", "").replace(",", ""))
        except:
            precio = 0.0
        
        cant = self.spin_cant.value()
        grupo_codigo = raw.get("ItemsGroupCode", "NA")
        descuento_maximo = self.obtener_descuento_maximo(grupo_codigo)
        
        item = {
            "codigo": raw.get("ItemCode", ""),
            "nombre": raw.get("ItemName", ""),
            "grupo": grupo_codigo,
            "descuento_maximo": descuento_maximo,
            "unidad": raw.get("SalesUnit", "PZA"),
            "cantidad": cant,
            "moneda": self.cmb_moneda.currentText(),
            "precio": precio,
            "descuento_pct": 0.0,
            "precio_con_descuento": precio,
            "subtotal": precio * cant,
            "iva": 0.0,
            "total": 0.0
        }
        
        item["iva"] = item["subtotal"] * 0.16
        item["total"] = item["subtotal"] + item["iva"]
        
        self.articulos_cotizacion.append(item)
        self.actualizar_tabla_cotizacion()
        
        QMessageBox.information(
            self, "Descuento Máximo",
            f"Artículo agregado correctamente.\n\n"
            f"Grupo: {grupo_codigo}\n"
            f"Descuento máximo permitido: {descuento_maximo}%"
        )
        
        self.timer_inactividad.start(self.tiempo_limite_ms)
    
    def actualizar_tabla_cotizacion(self):
        self.tbl_cot.blockSignals(True)
        self.tbl_cot.setRowCount(len(self.articulos_cotizacion))
        
        total_sub = 0
        total_iva = 0
        total_net = 0
        
        for i, art in enumerate(self.articulos_cotizacion):
            def ro(v, color=None):
                it = QTableWidgetItem(str(v))
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if color:
                    it.setBackground(QColor(color))
                return it
            
            def ed(v, color=None):
                it = QTableWidgetItem(str(v))
                if color:
                    it.setBackground(QColor(color))
                return it
            
            desc_pct = art["descuento_pct"]
            desc_max = art["descuento_maximo"]
            desc_color = None
            if desc_pct > desc_max:
                desc_color = DESCUENTO_BLOQUEADO_COLOR
            elif desc_pct > desc_max * 0.9:
                desc_color = ALERTA_DESCUENTO_COLOR
            
            self.tbl_cot.setItem(i, 0, ro(art["codigo"]))
            self.tbl_cot.setItem(i, 1, ro(art["grupo"]))
            self.tbl_cot.setItem(i, 2, ro(f"{art['descuento_maximo']:.1f}%", "#E3F2FD"))
            self.tbl_cot.setItem(i, 3, ed(f"{art['cantidad']:.2f}"))
            self.tbl_cot.setItem(i, 4, ro(art["unidad"]))
            self.tbl_cot.setItem(i, 5, ro(art["moneda"]))
            self.tbl_cot.setItem(i, 6, ro(f"${art['precio']:,.2f}"))
            self.tbl_cot.setItem(i, 7, ed(f"{art['descuento_pct']:.2f}", desc_color))
            self.tbl_cot.setItem(i, 8, ed(f"{art['precio_con_descuento']:.2f}"))
            self.tbl_cot.setItem(i, 9, ro(f"${art['subtotal']:,.2f}"))
            self.tbl_cot.setItem(i, 10, ro(f"${art['total']:,.2f}"))
            
            total_sub += art["subtotal"]
            total_iva += art["iva"]
            total_net += art["total"]
        
        self.tbl_cot.resizeColumnsToContents()
        self.tbl_cot.blockSignals(False)
        
        self.lbl_totals.setText(
            f"Subtotal: ${total_sub:,.2f} | IVA: ${total_iva:,.2f} | TOTAL: ${total_net:,.2f}"
        )
    
    def recalcular_celda(self, item):
        row = item.row()
        col = item.column()
        
        if row < 0:
            return
        
        art = self.articulos_cotizacion[row]
        
        try:
            txt_limpio = item.text().replace("$", "").replace(",", "").replace("%", "")
            val = float(txt_limpio)
        except:
            return
        
        if col == 3:  # Cantidad
            art["cantidad"] = val
            art["subtotal"] = art["precio_con_descuento"] * val
        elif col == 7:  # Descuento %
            descuento_maximo = art["descuento_maximo"]
            if val > descuento_maximo:
                QMessageBox.warning(
                    self, "Descuento Excedido",
                    f"El descuento ingresado ({val:.2f}%) supera el máximo permitido.\n\n"
                    f"Grupo: {art['grupo']}\n"
                    f"Descuento máximo: {descuento_maximo}%\n\n"
                    f"Se aplicará el descuento máximo permitido."
                )
                val = descuento_maximo
            
            art["descuento_pct"] = val
            art["precio_con_descuento"] = art["precio"] * (1 - val / 100)
            art["subtotal"] = art["precio_con_descuento"] * art["cantidad"]
        elif col == 8:  # Precio con descuento
            art["precio_con_descuento"] = val
            if art["precio"] > 0:
                nuevo_desc_pct = ((art["precio"] - val) / art["precio"]) * 100
                descuento_maximo = art["descuento_maximo"]
                
                if nuevo_desc_pct > descuento_maximo:
                    QMessageBox.warning(
                        self, "Descuento Excedido",
                        f"El precio ingresado equivale a un descuento de {nuevo_desc_pct:.2f}%\n"
                        f"que supera el máximo permitido de {descuento_maximo}%.\n\n"
                        f"Se aplicará el descuento máximo permitido."
                    )
                    art["descuento_pct"] = descuento_maximo
                    art["precio_con_descuento"] = art["precio"] * (1 - descuento_maximo / 100)
                else:
                    art["descuento_pct"] = nuevo_desc_pct
            else:
                art["descuento_pct"] = 0.0
            
            art["subtotal"] = art["precio_con_descuento"] * art["cantidad"]
        
        art["iva"] = art["subtotal"] * 0.16
        art["total"] = art["subtotal"] + art["iva"]
        
        self.actualizar_tabla_cotizacion()
        self.timer_inactividad.start(self.tiempo_limite_ms)
    
    def eliminar_fila(self):
        r = self.tbl_cot.currentRow()
        if r >= 0:
            self.articulos_cotizacion.pop(r)
            self.actualizar_tabla_cotizacion()
    
    def limpiar_todo(self):
        respuesta = QMessageBox.question(
            self, "Confirmar Limpieza",
            "¿Estás seguro de limpiar toda la cotización?\n\n"
            "Esto eliminará:\n"
            "• Todos los artículos de la cotización\n"
            "• Datos del cliente seleccionado\n"
            "• Referencias a archivos PDF/Excel generados\n"
            "• Archivos temporales",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.No:
            return
        
        try:
            self.articulos_cotizacion = []
            self.actualizar_tabla_cotizacion()
            
            self.cmb_cliente.setCurrentIndex(0)
            self.limpiar_datos_cliente()
            self.btn_refresh_cliente.setEnabled(False)
            
            if hasattr(self, 'ultimo_pdf_generado'):
                self.ultimo_pdf_generado = None
            
            self.btn_excel.setEnabled(False)
            self.btn_email.setEnabled(False)
            
            self.tbl_search.setRowCount(0)
            self.articulos_datos_completos = []
            self.txt_search_art.clear()
            
            self.spin_cant.setValue(1)
            self.cmb_lista.setCurrentIndex(0)
            self.cmb_moneda.setCurrentIndex(0)
            
            self.timer_inactividad.start(self.tiempo_limite_ms)
            
            QMessageBox.information(
                self, "Limpieza Completada",
                "Toda la información ha sido limpiada correctamente.\n\n"
                "Puedes comenzar una nueva cotización."
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error durante la limpieza:\n{e}")
    
    def buscar_archivo_logo(self):
        import sys
        if getattr(sys, 'frozen', False):
            basepath = sys._MEIPASS
        else:
            basepath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        posibles_nombres = ["logo_tubos.jpg", "logo_tubos.png", "logo_tubos.jpg"]
        
        for nombre in posibles_nombres:
            ruta_logo = os.path.join(basepath, "resources", nombre)
            if os.path.exists(ruta_logo) and os.path.isfile(ruta_logo):
                return ruta_logo
        
        return None
    
    def generar_excel_temporal(self):
        try:
            if not self.articulos_cotizacion:
                return None
            
            df = pd.DataFrame(self.articulos_cotizacion)
            
            columnas_ordenadas = [
                "codigo", "nombre", "cantidad", "unidad", "precio", 
                "descuento_pct", "precio_con_descuento", "subtotal", "iva", "total"
            ]
            df = df[columnas_ordenadas]
            df.columns = [
                "Código", "Descripción", "Cantidad", "Unidad", "Precio Lista", 
                "Desc %", "Precio Unitario Final", "Subtotal", "IVA", "Total Línea"
            ]
            
            temp_fd, excel_path = tempfile.mkstemp(suffix=".xlsx", prefix="Cotizacion_Detalle_")
            os.close(temp_fd)
            
            with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Detalle Cotización")
                
                worksheet = writer.sheets["Detalle Cotización"]
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    try:
                        for cell in column:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                    except:
                        pass
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
            
            return excel_path
        except Exception as e:
            return None
    
    def numero_a_letras(self, numero, moneda="MXN"):
        unidades = ("", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve")
        decenas = ("", "", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa")
        centenas = ("", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos")
        
        def tres_digitos(n):
            if n == 0:
                return ""
            elif n < 10:
                return unidades[n]
            elif n < 20:
                return ("diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve")[n - 10]
            elif n < 100:
                d = n // 10
                u = n % 10
                if u == 0:
                    return decenas[d]
                else:
                    return decenas[d] + " y " + unidades[u]
            else:
                c = n // 100
                r = n % 100
                if r == 0:
                    return "cien" if c == 1 else centenas[c]
                elif r < 10:
                    return centenas[c] + " " + unidades[r]
                else:
                    return centenas[c] + " " + tres_digitos(r)
        
        partes = str(numero).split(".")
        pesos = int(partes[0])
        centavos = int(partes[1][:2].ljust(2, "0")) if len(partes) > 1 else 0
        
        if pesos == 0:
            texto_pesos = "cero"
        elif pesos == 1:
            texto_pesos = "uno"
        elif pesos < 1000:
            texto_pesos = tres_digitos(pesos)
        elif pesos < 1000000:
            miles = pesos // 1000
            resto = pesos % 1000
            if miles == 1:
                texto_pesos = "mil"
            else:
                texto_pesos = tres_digitos(miles) + " mil"
            if resto > 0:
                texto_pesos += " " + tres_digitos(resto)
        else:
            millones = pesos // 1000000
            resto = pesos % 1000000
            if millones == 1:
                texto_pesos = "un millón"
            else:
                texto_pesos = tres_digitos(millones) + " millones"
            if resto > 0:
                if resto < 1000:
                    texto_pesos += " " + tres_digitos(resto)
                else:
                    miles = resto // 1000
                    r = resto % 1000
                    if miles == 1:
                        texto_pesos += " mil"
                    else:
                        texto_pesos += " " + tres_digitos(miles) + " mil"
                    if r > 0:
                        texto_pesos += " " + tres_digitos(r)
        
        if moneda.upper() == "USD":
            return f"{texto_pesos.upper()} DÓLARES CON {centavos:02d}/100"
        else:
            return f"{texto_pesos.upper()} PESOS CON {centavos:02d}/100 M.N."
    
    def generar_qr_cotizacion(self, datos: dict):
        try:
            detalle_partidas = ""
            items = datos.get("items", [])
            items_a_mostrar = items[:15]
            
            for item in items_a_mostrar:
                cant = item["cantidad"]
                precio_final = item["precio_con_descuento"]
                subtotal = item["subtotal"]
                desc_pct = item.get("descuento_pct", 0.0)
                texto_desc = f" (-{desc_pct:.2f}%)" if desc_pct > 0 else ""
                linea = f"{item['codigo']}: {cant:.2f} x ${precio_final:.2f}{texto_desc} = ${subtotal:.2f}\n"
                detalle_partidas += linea
            
            if len(items) > 15:
                detalle_partidas += f"\n... y {len(items) - 15} partidas más ...\n"
            
            contenido_qr = f"""VALIDACIÓN TUBOS MONTERREY
{datos.get('cliente', 'NA')}
{datos.get('rfc', 'NA')}
{datos.get('fecha', 'NA')}
------------------
Cod: Cant x Precio = Subtotal
{detalle_partidas}------------------
${datos.get('subtotal', 0.00)}
${datos.get('iva', 0.00)}
${datos.get('total', 0.00)} {datos.get('moneda', 'MXN')}"""
            
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=8,
                border=2
            )
            qr.add_data(contenido_qr)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            temp_fd, qr_temp_path = tempfile.mkstemp(suffix=".png", prefix="qr_verification_")
            os.close(temp_fd)
            img.save(qr_temp_path)
            
            return qr_temp_path, contenido_qr
        except Exception as e:
            return None, None
    
    def generar_pdf(self):
        if not self.articulos_cotizacion:
            QMessageBox.warning(self, "Aviso", "Cotización vacía")
            return
        
        download_folder = str(Path.home() / "Downloads")
        default_name = f"Cotizacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        full_path = os.path.join(download_folder, default_name)
        
        path_save, _ = QFileDialog.getSaveFileName(
            self, "Guardar Cotización", full_path, "PDF Files (*.pdf)"
        )
        
        if not path_save:
            return
        
        try:
            ruta_excel_temp = self.generar_excel_temporal()
            self.crear_pdf_cotizacion(path_save, rutaexcel=ruta_excel_temp)
            
            if ruta_excel_temp and os.path.exists(ruta_excel_temp):
                try:
                    os.remove(ruta_excel_temp)
                except:
                    pass
            
            resp = QMessageBox.question(
                self, "Éxito",
                f"PDF guardado con Excel adjunto en:\n{path_save}\n\n"
                f"El PDF contiene el Excel adjunto. Puedes extraerlo con el botón 'Descargar Excel'.\n\n"
                f"¿Abrir PDF ahora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if resp == QMessageBox.StandardButton.Yes:
                if sys.platform == "win32":
                    os.startfile(path_save)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", path_save])
                else:
                    subprocess.Popen(["xdg-open", path_save])
        except Exception as e:
            QMessageBox.critical(self, "Error PDF", f"Fallo al crear PDF:\n{e}")
    
    def crear_pdf_cotizacion(self, nombrearchivo: str, rutaexcel: str = None):
        """Crea PDF compatible con Adobe Reader con Excel adjunto usando PyMuPDF"""
        try:
            temp_fd, temp_pdf = tempfile.mkstemp(suffix=".pdf", prefix="cotizacion_temp_")
            os.close(temp_fd)
            
            self.generar_contenido_pdf(temp_pdf, rutaexcel=rutaexcel)
            
            if not os.path.exists(temp_pdf):
                raise Exception(f"El PDF temporal no se creó: {temp_pdf}")
            
            if rutaexcel and os.path.exists(rutaexcel):
                pdf_document = fitz.open(temp_pdf)
                
                with open(rutaexcel, "rb") as excel_file:
                    excel_data = excel_file.read()
                
                pdf_document.embfile_add(
                    "Cotizacion_Detalle.xlsx",
                    excel_data,
                    filename="Cotizacion_Detalle.xlsx",
                    desc="Detalle completo de la cotización en formato Excel"
                )
                
                pdf_document.save(nombrearchivo, garbage=4, deflate=True, clean=True)
                pdf_document.close()
                
                self.ultimo_pdf_generado = nombrearchivo
                self.btn_excel.setEnabled(True)
                self.btn_email.setEnabled(True)
            else:
                import shutil
                shutil.copy(temp_pdf, nombrearchivo)
                self.ultimo_pdf_generado = None
                self.btn_excel.setEnabled(False)
            
            if os.path.exists(temp_pdf):
                try:
                    os.remove(temp_pdf)
                except Exception:
                    pass
        except Exception as e:
            raise
    
    def generar_contenido_pdf(self, nombrearchivo: str, rutaexcel: str = None):
        """Genera el contenido del PDF usando ReportLab"""
        try:
            directorio = os.path.dirname(nombrearchivo)
            if directorio and not os.path.exists(directorio):
                os.makedirs(directorio)
            
            doc = SimpleDocTemplate(
                nombrearchivo,
                pagesize=letter,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch,
                leftMargin=0.5*inch,
                rightMargin=0.5*inch
            )
            
            elementos = []
            estilos = getSampleStyleSheet()
            
            estilo_empresa = ParagraphStyle(
                'Empresa',
                parent=estilos['Normal'],
                fontSize=14,
                textColor=colors.HexColor("#000000"),
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                spaceAfter=2
            )
            
            estilo_datos_empresa = ParagraphStyle(
                'DatosEmpresa',
                parent=estilos['Normal'],
                fontSize=8,
                textColor=colors.HexColor("#000000"),
                alignment=TA_CENTER,
                spaceAfter=1
            )
            
            estilo_titulo_seccion = ParagraphStyle(
                'TituloSeccion',
                parent=estilos['Normal'],
                fontSize=9,
                fontName='Helvetica-Bold',
                textColor=colors.black
            )
            
            estilo_datos = ParagraphStyle(
                'Datos',
                parent=estilos['Normal'],
                fontSize=8,
                textColor=colors.black
            )
            
            # Logo
            logo_path = self.buscar_archivo_logo()
            if logo_path:
                try:
                    logo_img = Image(logo_path, width=2.5*inch, height=0.6*inch)
                    datos_empresa_texto = f"{COMPANY_NAME}<br/>{COMPANY_ADDRESS}<br/>TEL: {COMPANY_PHONE}<br/>{COMPANY_WEBSITE}"
                    
                    tabla_encabezado = Table(
                        [[logo_img, Paragraph(datos_empresa_texto, estilo_datos_empresa)]],
                        colWidths=[2.8*inch, 4.2*inch]
                    )
                    tabla_encabezado.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                        ('ALIGN', (0,0), (0,0), 'LEFT'),
                        ('ALIGN', (1,0), (1,0), 'CENTER'),
                    ]))
                    elementos.append(tabla_encabezado)
                except Exception:
                    elementos.append(Paragraph(COMPANY_NAME, estilo_empresa))
                    elementos.append(Paragraph(f"{COMPANY_ADDRESS}<br/>TEL: {COMPANY_PHONE}", estilo_datos_empresa))
            else:
                elementos.append(Paragraph(COMPANY_NAME, estilo_empresa))
                elementos.append(Paragraph(f"{COMPANY_ADDRESS}<br/>TEL: {COMPANY_PHONE}", estilo_datos_empresa))
            
            elementos.append(Spacer(1, 0.2*inch))
            
            # Fecha y oferta
            fecha_actual = datetime.now().strftime("%d/%m/%Y")
            datos_oferta = [
                ["FECHA DE OFERTA", "NUM. DE OFERTA"],
                [fecha_actual, "PENDIENTE"]
            ]
            tabla_oferta = Table(datos_oferta, colWidths=[3*inch, 3*inch])
            tabla_oferta.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('BACKGROUND', (0,0), (-1,0), colors.white),
            ]))
            elementos.append(tabla_oferta)
            elementos.append(Spacer(1, 0.15*inch))
            
            # Datos del cliente
            nombre_cliente = self.txt_nom_cli.text() or "NA"
            rfc_cliente = self.txt_rfc.text() or "NA"
            domicilio = self.txt_dir.text() or "NA"
            condiciones_pago = self.txt_cond.text() or "Contado"
            
            datos_cliente = [
                [Paragraph("CLIENTE:", estilo_titulo_seccion), Paragraph(nombre_cliente, estilo_datos),
                 Paragraph("PROYECTO:", estilo_titulo_seccion), Paragraph("Cotización", estilo_datos)],
                ["", "", "", ""],
                [Paragraph("RFC:", estilo_titulo_seccion), Paragraph(rfc_cliente, estilo_datos), "", ""],
                ["", "", "", ""],
                [Paragraph("Calle:", estilo_titulo_seccion), Paragraph(domicilio, estilo_datos),
                 Paragraph("TIEMPO DE EJECUCIÓN:", estilo_titulo_seccion), Paragraph("Inmediato", estilo_datos)]
            ]
            
            tabla_cliente = Table(datos_cliente, colWidths=[0.8*inch, 2.7*inch, 1.3*inch, 1.7*inch])
            tabla_cliente.setStyle(TableStyle([
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('ALIGN', (0,0), (0,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            elementos.append(tabla_cliente)
            elementos.append(Spacer(1, 0.1*inch))
            
            elementos.append(Paragraph(
                "Esperando poder dar solución a sus necesidades, les presentamos su cotización:",
                estilo_datos
            ))
            elementos.append(Spacer(1, 0.15*inch))
            
            # Tabla de artículos (continúa en siguiente mensaje debido a límite de caracteres)
            
            # Generar tabla de artículos
            total_general = 0
            total_iva = 0
            total_con_iva = 0
            moneda_texto = "MXN"
            
            datos_tabla = [[
                "CANT.",
                "UNIDAD",
                "CÓDIGO",
                "DESCRIPCIÓN",
                "PRECIO UNITARIO",
                "IMPORTE"
            ]]
            
            for art in self.articulos_cotizacion:
                moneda_texto = art["moneda"]
                datos_tabla.append([
                    f"{art['cantidad']:.2f}",
                    art["unidad"],
                    art["codigo"],
                    art["nombre"][:50],
                    f"${art['precio_con_descuento']:,.2f}",
                    f"${art['subtotal']:,.2f}"
                ])
                total_general += art["subtotal"]
                total_iva += art["iva"]
                total_con_iva += art["total"]
            
            tabla_articulos = Table(datos_tabla, colWidths=[0.6*inch, 0.7*inch, 1.2*inch, 2.5*inch, 1.0*inch, 1.0*inch])
            tabla_articulos.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 7),
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            elementos.append(tabla_articulos)
            elementos.append(Spacer(1, 0.1*inch))
            
            # Totales
            datos_totales = [
                ["SUBTOTAL:", f"${total_general:,.2f}"],
                ["IVA 16%:", f"${total_iva:,.2f}"],
                ["TOTAL:", f"${total_con_iva:,.2f} {moneda_texto}"]
            ]
            
            tabla_totales = Table(datos_totales, colWidths=[5.5*inch, 1.5*inch])
            tabla_totales.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('ALIGN', (0,0), (0,-1), 'RIGHT'),
                ('ALIGN', (1,0), (1,-1), 'RIGHT'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('BACKGROUND', (0,2), (-1,2), colors.lightgrey),
            ]))
            elementos.append(tabla_totales)
            elementos.append(Spacer(1, 0.1*inch))
            
            # Monto en letra
            monto_letra = self.numero_a_letras(total_con_iva, moneda_texto)
            elementos.append(Paragraph(f"<b>SON:</b> {monto_letra}", estilo_datos))
            elementos.append(Spacer(1, 0.1*inch))
            
            # Nota sobre Excel adjunto
            if rutaexcel and os.path.exists(rutaexcel):
                elementos.append(Spacer(1, 0.1*inch))
                nota_excel = Paragraph(
                    "<b>NOTA:</b> Este PDF contiene un archivo Excel adjunto con el detalle completo de la cotización.<br/>"
                    "<b>En Adobe Reader:</b> Haga clic en el ícono de clip en la barra lateral o vaya a "
                    "Ver > Mostrar/Ocultar > Paneles de navegación > Archivos adjuntos.<br/>"
                    "<b>En la aplicación:</b> Use el botón <i>Descargar Excel</i> para extraer el archivo.",
                    estilo_datos
                )
                elementos.append(nota_excel)
                elementos.append(Spacer(1, 0.3*inch))
            
            # QR Code
            datos_para_qr = {
                "cliente": nombre_cliente,
                "rfc": rfc_cliente,
                "fecha": fecha_actual,
                "items": self.articulos_cotizacion,
                "items_count": len(self.articulos_cotizacion),
                "subtotal": f"{total_general:,.2f}",
                "iva": f"{total_iva:,.2f}",
                "total": f"{total_con_iva:,.2f}",
                "moneda": moneda_texto
            }
            
            qr_path = None
            try:
                qr_path, _ = self.generar_qr_cotizacion(datos_para_qr)
                if qr_path:
                    qr_img = Image(qr_path, width=1.3*inch, height=1.3*inch)
                    tabla_qr = Table([[qr_img]], colWidths=[1.5*inch], hAlign='RIGHT')
                    tabla_qr.setStyle(TableStyle([
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ]))
                    elementos.append(tabla_qr)
            except Exception:
                pass
            
            # Construir PDF
            doc.build(elementos)
            
            # Limpiar QR temporal
            if qr_path and os.path.exists(qr_path):
                try:
                    os.remove(qr_path)
                except Exception:
                    pass
        except Exception as e:
            raise
    
    def descargar_excel(self):
        """Extrae y descarga el Excel adjunto del PDF"""
        if not hasattr(self, 'ultimo_pdf_generado') or not self.ultimo_pdf_generado:
            QMessageBox.warning(self, "Sin PDF", "Primero debes generar un PDF con Excel adjunto.")
            return
        
        if not os.path.exists(self.ultimo_pdf_generado):
            QMessageBox.warning(
                self, "Archivo no encontrado",
                f"El PDF generado ya no existe:\n{self.ultimo_pdf_generado}"
            )
            return
        
        try:
            pdf_document = fitz.open(self.ultimo_pdf_generado)
            
            if pdf_document.embfile_count() == 0:
                QMessageBox.warning(self, "Sin adjuntos", "Este PDF no contiene archivos adjuntos.")
                pdf_document.close()
                return
            
            embfile_info = pdf_document.embfile_info(0)
            embfile_name = embfile_info["filename"]
            embfile_data = pdf_document.embfile_get(0)
            pdf_document.close()
            
            download_folder = str(Path.home() / "Downloads")
            default_name = f"Cotizacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            full_path = os.path.join(download_folder, default_name)
            
            path_save, _ = QFileDialog.getSaveFileName(
                self, "Guardar Excel", full_path, "Excel Files (*.xlsx)"
            )
            
            if not path_save:
                return
            
            with open(path_save, "wb") as f:
                f.write(embfile_data)
            
            QMessageBox.information(
                self, "Excel descargado",
                f"Archivo Excel guardado en:\n{path_save}"
            )
            
            resp = QMessageBox.question(
                self, "Abrir Excel",
                "¿Deseas abrir el archivo Excel ahora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if resp == QMessageBox.StandardButton.Yes:
                if sys.platform == "win32":
                    os.startfile(path_save)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", path_save])
                else:
                    subprocess.Popen(["xdg-open", path_save])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al extraer Excel del PDF:\n{e}")
    
    def preparar_email_outlook(self):
        """Crea un correo en Outlook con PDF y Excel adjuntos"""
        if not hasattr(self, 'ultimo_pdf_generado') or not self.ultimo_pdf_generado:
            QMessageBox.warning(
                self, "Sin PDF",
                "Primero debes generar un PDF con la cotización."
            )
            return
        
        if not os.path.exists(self.ultimo_pdf_generado):
            QMessageBox.warning(
                self, "Archivo no encontrado",
                f"El PDF generado ya no existe:\n{self.ultimo_pdf_generado}"
            )
            return
        
        try:
            import win32com.client as win32
            
            outlook = win32.Dispatch("Outlook.Application")
            mail = outlook.CreateItem(0)
            
            # Destinatario
            email_cliente = self.txt_email.text().strip()
            if email_cliente:
                mail.To = email_cliente
            
            # Asunto
            nombre_cliente = self.txt_nom_cli.text() or "Cliente"
            mail.Subject = f"Cotización - {nombre_cliente} - {datetime.now().strftime('%d/%m/%Y')}"
            
            # Cuerpo del mensaje
            contenido_html = f"""
<p>Estimado/a {nombre_cliente},</p>

<p>Por medio de la presente, le enviamos la cotización solicitada.</p>

<p>Adjunto encontrará:</p>
<ul>
    <li><b>PDF</b> con el detalle de la cotización</li>
    <li><b>Excel</b> con información detallada</li>
</ul>

<p>Quedamos a sus órdenes para cualquier aclaración.</p>

<p>Saludos cordiales,</p>
"""
            
            # Cargar firma de Outlook primero
            mail.GetInspector()
            firma_outlook = mail.HTMLBody
            
            # Agregar contenido + firma
            mail.HTMLBody = contenido_html + firma_outlook
            
            # Adjuntar PDF
            mail.Attachments.Add(os.path.abspath(self.ultimo_pdf_generado))
            
            # Adjuntar Excel si existe
            excel_path = self.generar_excel_temporal()
            if excel_path and os.path.exists(excel_path):
                mail.Attachments.Add(os.path.abspath(excel_path))
            
            # Mostrar correo (no enviar automáticamente)
            mail.Display(False)
            
            QMessageBox.information(
                self, "Email Preparado",
                "El correo ha sido creado en Outlook con:\n\n"
                "• PDF de la cotización adjunto\n"
                "• Excel con detalle adjunto\n"
                "• Destinatario configurado\n"
                "• Asunto y cuerpo del mensaje\n"
                "• Firma de Outlook incluida\n\n"
                "Revisa el correo y envíalo cuando estés listo."
            )
            
            # Limpiar Excel temporal después de 10 segundos
            if excel_path and os.path.exists(excel_path):
                QTimer.singleShot(10000, lambda: self.limpiar_excel_temporal(excel_path))
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Error al preparar el correo:\n{e}\n\n"
                f"Asegúrate de tener Outlook instalado y configurado."
            )
    
    def limpiar_excel_temporal(self, ruta):
        """Limpia archivo Excel temporal después de adjuntarlo"""
        try:
            if os.path.exists(ruta):
                os.remove(ruta)
        except Exception:
            pass
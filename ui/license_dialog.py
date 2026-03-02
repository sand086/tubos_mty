"""
Dialogo de validacion de licencia
-----------------------------------
Cambios (v2):
  • Usa los metodos en espanol del nuevo LicenseManager.
  • Aliases de compatibilidad para nombres originales en ingles.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
    QTextEdit, QHBoxLayout, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from api.license_manager import LicenseManager
from utils.hardware_id import get_hardware_id, get_computer_name


class TrabajadorValidacionLicencia(QThread):
    """
    Hilo de trabajo para validar la licencia sin bloquear la interfaz.
    Emite la senal 'terminado' con (es_valido: bool, mensaje: str).
    """
    terminado = pyqtSignal(bool, str)

    def __init__(self, hardware_id: str, nombre_pc: str, usuario: str):
        super().__init__()
        self.hardware_id = hardware_id
        self.nombre_pc   = nombre_pc
        self.usuario     = usuario

    def run(self):
        try:
            gestor = LicenseManager()
            es_valido, mensaje = gestor.validar_licencia(
                self.hardware_id,
                self.nombre_pc,
                self.usuario,
            )
            self.terminado.emit(es_valido, mensaje)
        except Exception as e:
            self.terminado.emit(False, f"Error critico: {str(e)}")


class LicenseDialog(QDialog):
    """Dialogo de validacion de licencia."""

    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.username      = username
        self.hardware_id   = get_hardware_id()
        self.computer_name = get_computer_name()
        self.nombre_pc     = self.computer_name
        self.is_valid      = False

        self._construir_ui()
        self._iniciar_validacion()

    # ------------------------------------------------------------------
    #  Construccion de la interfaz
    # ------------------------------------------------------------------

    def _construir_ui(self):
        self.setWindowTitle("Validacion de Licencia")
        self.setFixedSize(500, 400)
        self.setModal(True)

        layout = QVBoxLayout()
        layout.setSpacing(15)

        titulo = QLabel("Validacion de Licencia")
        fuente_titulo = QFont()
        fuente_titulo.setPointSize(14)
        fuente_titulo.setBold(True)
        titulo.setFont(fuente_titulo)
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titulo)

        etiqueta_info = QLabel("Informacion del Dispositivo:")
        etiqueta_info.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(etiqueta_info)

        self.texto_info = QTextEdit()
        self.texto_info.setReadOnly(True)
        self.texto_info.setMaximumHeight(100)
        self.texto_info.setPlainText(
            f"ID del Equipo     : {self.hardware_id}\n"
            f"Nombre del Equipo : {self.nombre_pc}\n"
            f"Usuario           : {self.username}"
        )
        layout.addWidget(self.texto_info)

        self.barra_progreso = QProgressBar()
        self.barra_progreso.setRange(0, 0)
        layout.addWidget(self.barra_progreso)

        etiqueta_estado = QLabel("Estado de Validacion:")
        etiqueta_estado.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(etiqueta_estado)

        self.texto_estado = QTextEdit()
        self.texto_estado.setReadOnly(True)
        self.texto_estado.setMaximumHeight(150)
        self.texto_estado.setPlainText("Validando licencia, por favor espere...")
        layout.addWidget(self.texto_estado)

        contenedor_botones = QHBoxLayout()

        self.btn_copiar = QPushButton("Copiar ID del Equipo")
        self.btn_copiar.clicked.connect(self._copiar_hardware_id)
        self.btn_copiar.setEnabled(False)
        contenedor_botones.addWidget(self.btn_copiar)

        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_cerrar.clicked.connect(self._cerrar_dialogo)
        self.btn_cerrar.setEnabled(False)
        contenedor_botones.addWidget(self.btn_cerrar)

        layout.addLayout(contenedor_botones)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    #  Logica de validacion
    # ------------------------------------------------------------------

    def _iniciar_validacion(self):
        """Lanza el hilo de validacion."""
        self.trabajador = TrabajadorValidacionLicencia(
            self.hardware_id,
            self.nombre_pc,
            self.username,
        )
        self.trabajador.terminado.connect(self._al_terminar_validacion)
        self.trabajador.start()

    def _al_terminar_validacion(self, es_valido: bool, mensaje: str):
        """Actualiza la interfaz cuando termina la validacion."""
        self.barra_progreso.setRange(0, 1)
        self.barra_progreso.setValue(1)

        self.is_valid = es_valido
        self.texto_estado.setPlainText(mensaje)

        if es_valido:
            self.texto_estado.setStyleSheet(
                "background-color: #d4edda; color: #155724; padding: 10px;"
            )
            self.btn_cerrar.setText("Continuar")
            self.btn_cerrar.setStyleSheet(
                "background-color: #28a745; color: white; font-weight: bold;"
            )
        else:
            self.texto_estado.setStyleSheet(
                "background-color: #f8d7da; color: #721c24; padding: 10px;"
            )
            self.btn_copiar.setEnabled(True)
            self.btn_cerrar.setText("Cerrar")
            self.btn_cerrar.setStyleSheet(
                "background-color: #dc3545; color: white;"
            )

        self.btn_cerrar.setEnabled(True)

    # ------------------------------------------------------------------
    #  Acciones de los botones
    # ------------------------------------------------------------------

    def _cerrar_dialogo(self):
        """Acepta o rechaza el dialogo segun el resultado."""
        if self.is_valid:
            self.accept()
        else:
            self.reject()

    def _copiar_hardware_id(self):
        """Copia el Hardware ID al portapapeles."""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.hardware_id)
        self.btn_copiar.setText("ID Copiado")
        self.btn_copiar.setEnabled(False)

    # ------------------------------------------------------------------
    #  Aliases de compatibilidad con nombres originales en ingles
    # ------------------------------------------------------------------

    def validate_license(self):
        self._iniciar_validacion()

    def on_validation_finished(self, is_valid: bool, message: str):
        self._al_terminar_validacion(is_valid, message)

    def close_dialog(self):
        self._cerrar_dialogo()

    def copy_hardware_id(self):
        self._copiar_hardware_id()
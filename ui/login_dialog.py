from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFormLayout
)
from PyQt6.QtCore import Qt
from config.settings import MAX_LOGIN_ATTEMPTS, LOGIN_ATTEMPT_DELAY
from ui.license_dialog import LicenseDialog
import time

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔒 Acceso Seguro - SAP Business One")
        self.setFixedSize(350, 220)
        self.credenciales = None
        self.intentos_fallidos = 0
        self.tiempo_bloqueo = 0
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Usuario
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("Ej: manager")
        
        # Contraseña
        self.txt_pass = QLineEdit()
        self.txt_pass.setPlaceholderText("Contraseña")
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        
        # Base de datos (desde variable de entorno, con default)
        import os
        default_db = os.getenv("SAP_COMPANYDB", "")
        self.txt_db = QLineEdit(default_db)
        self.txt_db.setPlaceholderText("")
        
        form.addRow("👤 Usuario:", self.txt_user)
        form.addRow("🔐 Contraseña:", self.txt_pass)
        form.addRow("📊 Base Datos:", self.txt_db)
        layout.addLayout(form)
        
        # Botones
        btn_box = QHBoxLayout()
        self.btn_ok = QPushButton("Entrar")
        self.btn_ok.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.btn_ok.clicked.connect(self.validar)
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_box.addWidget(self.btn_ok)
        btn_box.addWidget(self.btn_cancel)
        layout.addLayout(btn_box)
        
        # Info label
        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("color: red; font-size: 9px;")
        layout.addWidget(self.lbl_info)
    
    def validar(self):
        # Chequear bloqueo por intentos fallidos
        if self.intentos_fallidos >= MAX_LOGIN_ATTEMPTS:
            delay = LOGIN_ATTEMPT_DELAY * (2 ** (self.intentos_fallidos - MAX_LOGIN_ATTEMPTS))
            if time.time() < self.tiempo_bloqueo + delay:
                self.lbl_info.setText(f"❌ Bloqueado. Intenta en {delay}s")
                return
        
        if not self.txt_user.text() or not self.txt_pass.text():
            QMessageBox.warning(self, "❌ Error", "Ingresa usuario y contraseña")
            return
        
        if not self.txt_db.text():
            QMessageBox.warning(self, "❌ Error", "Especifica la base de datos")
            return
        
        # ✅ VALIDACIÓN DE LICENCIA
        license_dialog = LicenseDialog(self.txt_user.text(), self)
        result = license_dialog.exec()
        
        # Si el usuario cerró el diálogo o la licencia es inválida, no continuar
        if result != QDialog.DialogCode.Accepted:  # Esto ahora funciona correctamente
            if not license_dialog.is_valid:
                QMessageBox.critical(
                    self,
                    "Licencia Inválida",
                    "No se puede continuar sin una licencia válida.\n"
                    "Contacta al administrador del sistema."
                )
            return
        
        # Licencia válida, continuar con login
        self.credenciales = {
            "CompanyDB": self.txt_db.text(),
            "UserName": self.txt_user.text(),
            "Password": self.txt_pass.text()
        }
        
        # Limpiar campos sensibles
        self.txt_pass.clear()
        
        self.accept()
    
    def set_login_error(self, message: str):
        """Llamado cuando login falla en la ventana principal"""
        self.intentos_fallidos += 1
        self.tiempo_bloqueo = time.time()
        self.lbl_info.setText(f"❌ {message}\nIntento {self.intentos_fallidos}/{MAX_LOGIN_ATTEMPTS}")
        
        if self.intentos_fallidos >= MAX_LOGIN_ATTEMPTS:
            self.btn_ok.setEnabled(False)
            self.lbl_info.setText(f"❌ Demasiados intentos. Bloqueado por {LOGIN_ATTEMPT_DELAY}s")

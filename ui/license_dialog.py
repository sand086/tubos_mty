"""
Diálogo de validación de licencia
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, 
    QTextEdit, QHBoxLayout, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from api.license_manager import LicenseManager
from utils.hardware_id import get_hardware_id, get_computer_name


class LicenseValidationWorker(QThread):
    """Worker thread para validación de licencia"""
    finished = pyqtSignal(bool, str)  # (is_valid, message)
    
    def __init__(self, hardware_id: str, computer_name: str, username: str):
        super().__init__()
        self.hardware_id = hardware_id
        self.computer_name = computer_name
        self.username = username
    
    def run(self):
        try:
            license_mgr = LicenseManager()
            is_valid, message = license_mgr.validate_license(
                self.hardware_id,
                self.computer_name,
                self.username
            )
            self.finished.emit(is_valid, message)
        except Exception as e:
            self.finished.emit(False, f"Error crítico: {str(e)}")


class LicenseDialog(QDialog):
    """Diálogo de validación de licencia"""
    
    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.username = username
        self.hardware_id = get_hardware_id()
        self.computer_name = get_computer_name()
        self.is_valid = False
        
        self.init_ui()
        self.validate_license()
    
    def init_ui(self):
        self.setWindowTitle("Validación de Licencia")
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Título
        title = QLabel("🔐 Validación de Licencia")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Información del dispositivo
        info_label = QLabel("Información del Dispositivo:")
        info_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(info_label)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(100)
        self.info_text.setPlainText(
            f"ID del Equipo: {self.hardware_id}\n"
            f"Nombre del Equipo: {self.computer_name}\n"
            f"Usuario: {self.username}"
        )
        layout.addWidget(self.info_text)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Modo indeterminado
        layout.addWidget(self.progress_bar)
        
        # Estado de validación
        status_label = QLabel("Estado de Validación:")
        status_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(status_label)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        self.status_text.setPlainText("Validando licencia, por favor espere...")
        layout.addWidget(self.status_text)
        
        # Botones
        button_layout = QHBoxLayout()
        
        self.btn_copy = QPushButton("📋 Copiar ID del Equipo")
        self.btn_copy.clicked.connect(self.copy_hardware_id)
        self.btn_copy.setEnabled(False)
        button_layout.addWidget(self.btn_copy)
        
        self.btn_close = QPushButton("Cerrar")
        self.btn_close.clicked.connect(self.close_dialog)
        self.btn_close.setEnabled(False)
        button_layout.addWidget(self.btn_close)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def validate_license(self):
        """Inicia validación de licencia en thread"""
        self.worker = LicenseValidationWorker(
            self.hardware_id,
            self.computer_name,
            self.username
        )
        self.worker.finished.connect(self.on_validation_finished)
        self.worker.start()
    
    def on_validation_finished(self, is_valid: bool, message: str):
        """Callback cuando termina la validación"""
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        
        self.is_valid = is_valid
        self.status_text.setPlainText(message)
        
        if is_valid:
            self.status_text.setStyleSheet("background-color: #d4edda; color: #155724; padding: 10px;")
            self.btn_close.setText("✅ Continuar")
            self.btn_close.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        else:
            self.status_text.setStyleSheet("background-color: #f8d7da; color: #721c24; padding: 10px;")
            self.btn_copy.setEnabled(True)
            self.btn_close.setText("❌ Cerrar")
            self.btn_close.setStyleSheet("background-color: #dc3545; color: white;")
        
        self.btn_close.setEnabled(True)

    def close_dialog(self):
        """Cierra el diálogo según validación"""
        if self.is_valid:
            self.accept()  # ← Retorna DialogCode.Accepted
        else:
            self.reject()  # ← Retorna DialogCode.Rejected
    
    def copy_hardware_id(self):
        """Copia el Hardware ID al portapapeles"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.hardware_id)
        self.btn_copy.setText("✅ ID Copiado")
        self.btn_copy.setEnabled(False)

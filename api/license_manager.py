"""
Gestor de licencias con validación en Google Sheets
Versión sin logs
"""

import os
import sys
import gspread
from google.oauth2.service_account import Credentials
from typing import Optional, Tuple, List
from pathlib import Path


class LicenseManager:
    """Maneja validación de licencias contra Google Sheets"""

    SPREADSHEET_ID = "1zJdAn5gAlxOy5bQA4_sgUaUexx7iQk4InfLn7vNDnS0"
    WORKSHEET_NAME = "Dispositivos"

    COL_HARDWARE_ID = 1
    COL_COMPUTER_NAME = 2
    COL_STATUS = 3
    COL_USER1 = 4
    COL_USER2 = 5
    COL_USER3 = 6
    COL_USER4 = 7

    def __init__(self):
        self.client = None
        self.worksheet = None
        self._connect()

    def _get_credentials_path(self) -> str:
        """Obtiene la ruta del archivo de credenciales"""
        if getattr(sys, "frozen", False):
            # Ejecutando como .exe - buscar en múltiples ubicaciones
            base_paths = [
                Path(sys._MEIPASS),
                Path(sys.executable).parent,
            ]

            for base_path in base_paths:
                # Intentar diferentes ubicaciones
                possible_paths = [
                    base_path / "credentials" / "service_account.json",
                    base_path / "config" / "service_account.json",
                    base_path / "service_account.json",
                ]

                for cred_path in possible_paths:
                    if cred_path.exists():
                        return str(cred_path)

            # Si no se encuentra, usar ruta esperada
            return str(Path(sys.executable).parent / "credentials" / "service_account.json")
        else:
            # Ejecutando como script
            base_path = Path(__file__).parent.parent
            return str(base_path / "credentials" / "service_account.json")

    def _connect(self) -> bool:
        """Conecta con Google Sheets API"""
        try:
            creds_path = self._get_credentials_path()

            if not os.path.exists(creds_path):
                return False

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]

            creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
            self.client = gspread.authorize(creds)

            spreadsheet = self.client.open_by_key(self.SPREADSHEET_ID)
            self.worksheet = spreadsheet.worksheet(self.WORKSHEET_NAME)

            return True

        except FileNotFoundError:
            return False
        except Exception:
            return False

    def find_device_row(self, hardware_id: str) -> Optional[int]:
        """Busca la fila del dispositivo por Hardware ID"""
        try:
            if not self.worksheet:
                return None

            hardware_ids = self.worksheet.col_values(self.COL_HARDWARE_ID)

            for idx, cell_value in enumerate(hardware_ids[1:], start=2):
                if cell_value.strip().upper() == hardware_id.upper():
                    return idx

            return None

        except Exception:
            return None

    def register_device(self, hardware_id: str, computer_name: str) -> bool:
        """Registra un nuevo dispositivo en la hoja"""
        try:
            if not self.worksheet:
                return False

            if self.find_device_row(hardware_id):
                return True

            new_row = [
                hardware_id,
                computer_name,
                "No autorizado",
                "", "", "", "",
            ]

            self.worksheet.append_row(new_row)
            return True

        except Exception:
            return False

    def get_device_status(self, hardware_id: str) -> Optional[str]:
        """Obtiene el estado de autorización del dispositivo"""
        try:
            if not self.worksheet:
                return None

            row_num = self.find_device_row(hardware_id)
            if not row_num:
                return None

            status = self.worksheet.cell(row_num, self.COL_STATUS).value
            return status.strip() if status else "No autorizado"

        except Exception:
            return None

    def get_authorized_users(self, hardware_id: str) -> List[str]:
        """Obtiene la lista de usuarios autorizados para este dispositivo"""
        try:
            if not self.worksheet:
                return []

            row_num = self.find_device_row(hardware_id)
            if not row_num:
                return []

            row_data = self.worksheet.row_values(row_num)

            users = []
            for col_idx in [3, 4, 5, 6]:
                if col_idx < len(row_data):
                    user = row_data[col_idx].strip()
                    if user:
                        users.append(user)

            return users

        except Exception:
            return []

    def validate_license(self, hardware_id: str, computer_name: str, username: str) -> Tuple[bool, str]:
        """Valida la licencia completa: dispositivo + usuario"""
        try:
            if not self.worksheet:
                return (
                    False,
                    "❌ Error de conexión con el sistema de licencias.\n\n"
                    "No se pudo conectar con Google Sheets.\n"
                    "Verifica tu conexión a internet.",
                )

            row_num = self.find_device_row(hardware_id)

            if not row_num:
                if self.register_device(hardware_id, computer_name):
                    return (
                        False,
                        "✅ Dispositivo registrado correctamente.\n\n"
                        "Por favor contacta al administrador para que autorice este equipo.\n\n"
                        f"ID del equipo: {hardware_id}\n"
                        f"Nombre: {computer_name}",
                    )
                else:
                    return (
                        False,
                        "❌ Error al registrar dispositivo.\n"
                        "Contacta al administrador del sistema.",
                    )

            status = self.get_device_status(hardware_id)
            if not status or status.lower() != "autorizado":
                return (
                    False,
                    f"⛔ Dispositivo NO AUTORIZADO\n\n"
                    f"Estado actual: {status}\n"
                    f"ID del equipo: {hardware_id}\n\n"
                    "Contacta al administrador para solicitar autorización.",
                )

            authorized_users = self.get_authorized_users(hardware_id)
            if not authorized_users:
                return (
                    False,
                    "⚠️ No hay usuarios autorizados para este dispositivo.\n\n"
                    "Contacta al administrador para agregar usuarios.",
                )

            username_lower = username.lower().strip()
            if username_lower not in [u.lower() for u in authorized_users]:
                return (
                    False,
                    f"⛔ Usuario NO AUTORIZADO en este dispositivo\n\n"
                    f"Usuario: {username}\n"
                    "Contacta al administrador.",
                )

            return (True, f"✅ Licencia válida\nBienvenido {username}")

        except Exception as e:
            return (
                False,
                f"❌ Error al validar licencia:\n{str(e)}\n\n"
                "Contacta al soporte técnico.",
            )

    def update_computer_name(self, hardware_id: str, computer_name: str) -> bool:
        """Actualiza el nombre del equipo en la hoja"""
        try:
            if not self.worksheet:
                return False

            row_num = self.find_device_row(hardware_id)
            if not row_num:
                return False

            self.worksheet.update_cell(row_num, self.COL_COMPUTER_NAME, computer_name)
            return True
        except Exception:
            return False

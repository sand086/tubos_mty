"""
Gestor de licencias con validacion a traves del middleware GAS
---------------------------------------------------------------
Cambios de seguridad (v2 — ISO/IEC 27001 A.5.17):
  • Eliminada la dependencia de gspread y google-auth.
  • Eliminado service_account.json del cliente.
  • Las operaciones sobre Google Sheets se realizan via HTTP contra
    el middleware de Google Apps Script (GAS), que es el unico
    componente que posee las credenciales de GCP.
  • Cada peticion incluye el token secreto (GAS_TOKEN) cifrado
    en config.encrypted y protegido por DPAPI.
"""

import os
import requests
from typing import Optional, Tuple, List


class LicenseManager:
    """
    Valida licencias consultando el middleware de Google Apps Script.
    No tiene acceso directo a Google Sheets ni a credenciales de GCP.
    """

    _TIMEOUT_SEGUNDOS = 15

    def __init__(self):
        self._gas_url   = os.getenv("GAS_URL", "").strip()
        self._gas_token = os.getenv("GAS_TOKEN", "").strip()
        self._disponible = bool(self._gas_url and self._gas_token)

        if not self._disponible:
            print("[LICENCIAS] GAS_URL o GAS_TOKEN no configurados.")

    # ------------------------------------------------------------------
    #  Comunicación con el middleware GAS
    # ------------------------------------------------------------------

    def _llamar_gas(self, accion: str, parametros: dict) -> Optional[dict]:
        """
        Realiza una peticion POST al middleware GAS.

        Args:
            accion: Nombre de la accion a ejecutar en el GAS.
            parametros: Parametros adicionales para la accion.

        Returns:
            Diccionario con la respuesta del GAS, o None si hubo error.
        """
        if not self._disponible:
            return None

        cuerpo = {
            "token" : self._gas_token,
            "accion": accion,
            **parametros,
        }

        try:
            respuesta = requests.post(
                self._gas_url,
                json=cuerpo,
                timeout=self._TIMEOUT_SEGUNDOS,
                headers={"Content-Type": "application/json"},
            )
            respuesta.raise_for_status()
            return respuesta.json()

        except requests.exceptions.Timeout:
            print("[LICENCIAS] Timeout al conectar con el servidor de licencias.")
            return None
        except requests.exceptions.ConnectionError:
            print("[LICENCIAS] Sin conexion al servidor de licencias.")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"[LICENCIAS] Error HTTP del servidor de licencias: {e}")
            return None
        except ValueError:
            print("[LICENCIAS] Respuesta invalida del servidor de licencias.")
            return None
        except Exception as e:
            print(f"[LICENCIAS] Error inesperado: {e}")
            return None

    # ------------------------------------------------------------------
    #  API pública — nombres en español (usados por license_dialog.py v2)
    # ------------------------------------------------------------------

    def validar_licencia(
        self,
        hardware_id: str,
        nombre_pc: str,
        usuario: str,
    ) -> Tuple[bool, str]:
        """
        Valida la licencia completa delegando al middleware GAS.

        Args:
            hardware_id: Identificador unico del hardware.
            nombre_pc: Nombre del equipo.
            usuario: Nombre de usuario que intenta acceder.

        Returns:
            Tupla (es_valido: bool, mensaje: str).
        """
        if not self._disponible:
            return (
                False,
                "Error de conexion con el sistema de licencias.\n\n"
                "El servidor de licencias no esta configurado correctamente.\n"
                "Verifica que GAS_URL y GAS_TOKEN esten en config.encrypted.",
            )

        respuesta = self._llamar_gas(
            "validar_licencia",
            {
                "hardware_id": hardware_id,
                "nombre_pc"  : nombre_pc,
                "usuario"    : usuario,
            },
        )

        if respuesta is None:
            return (
                False,
                "Error de conexion con el sistema de licencias.\n\n"
                "No se pudo contactar el servidor de licencias.\n"
                "Verifica tu conexion a internet e intenta de nuevo.",
            )

        if not respuesta.get("ok"):
            mensaje_error = respuesta.get("error", "Error desconocido del servidor.")
            return (
                False,
                f"Error del servidor de licencias:\n{mensaje_error}",
            )

        datos   = respuesta.get("datos", {})
        valido  = bool(datos.get("valido", False))
        mensaje = datos.get("mensaje", "Sin mensaje del servidor.")
        return (valido, mensaje)

    def registrar_dispositivo(self, hardware_id: str, nombre_pc: str) -> bool:
        """Registra un nuevo dispositivo con estado 'No autorizado'."""
        respuesta = self._llamar_gas(
            "registrar_dispositivo",
            {"hardware_id": hardware_id, "nombre_pc": nombre_pc}
        )
        return bool(respuesta and respuesta.get("ok"))

    def obtener_estado_dispositivo(self, hardware_id: str) -> Optional[str]:
        """Devuelve el estado de autorizacion del dispositivo."""
        respuesta = self._llamar_gas(
            "obtener_estado",
            {"hardware_id": hardware_id}
        )
        if respuesta and respuesta.get("ok"):
            return respuesta["datos"].get("estado")
        return None

    def obtener_usuarios_autorizados(self, hardware_id: str) -> List[str]:
        """Devuelve la lista de usuarios autorizados para el dispositivo."""
        respuesta = self._llamar_gas(
            "obtener_usuarios",
            {"hardware_id": hardware_id}
        )
        if respuesta and respuesta.get("ok"):
            return respuesta["datos"].get("usuarios", [])
        return []

    def actualizar_nombre_pc(self, hardware_id: str, nombre_pc: str) -> bool:
        """Actualiza el nombre del equipo en la hoja de Google Sheets."""
        respuesta = self._llamar_gas(
            "actualizar_nombre_pc",
            {"hardware_id": hardware_id, "nombre_pc": nombre_pc}
        )
        return bool(
            respuesta
            and respuesta.get("ok")
            and respuesta["datos"].get("actualizado")
        )

    # ------------------------------------------------------------------
    #  Aliases en inglés para compatibilidad con código existente
    # ------------------------------------------------------------------

    def validate_license(
        self, hardware_id: str, computer_name: str, username: str
    ) -> Tuple[bool, str]:
        """Alias de compatibilidad → validar_licencia."""
        return self.validar_licencia(hardware_id, computer_name, username)

    def register_device(self, hardware_id: str, computer_name: str) -> bool:
        """Alias de compatibilidad → registrar_dispositivo."""
        return self.registrar_dispositivo(hardware_id, computer_name)

    def get_device_status(self, hardware_id: str) -> Optional[str]:
        """Alias de compatibilidad → obtener_estado_dispositivo."""
        return self.obtener_estado_dispositivo(hardware_id)

    def get_authorized_users(self, hardware_id: str) -> List[str]:
        """Alias de compatibilidad → obtener_usuarios_autorizados."""
        return self.obtener_usuarios_autorizados(hardware_id)

    def update_computer_name(self, hardware_id: str, computer_name: str) -> bool:
        """Alias de compatibilidad → actualizar_nombre_pc."""
        return self.actualizar_nombre_pc(hardware_id, computer_name)

    def find_device_row(self, hardware_id: str) -> Optional[int]:
        """Alias de compatibilidad — verifica si el dispositivo existe."""
        respuesta = self._llamar_gas(
            "obtener_estado",
            {"hardware_id": hardware_id}
        )
        if respuesta and respuesta.get("ok") and respuesta["datos"].get("encontrado"):
            return 1
        return None
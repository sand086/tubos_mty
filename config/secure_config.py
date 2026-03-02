"""
Gestor de configuracion segura con encriptacion DPAPI (Windows)
---------------------------------------------------------------
La llave Fernet se almacena en Windows Credential Manager (DPAPI).
config.encrypted siempre vive en la RAIZ del proyecto, un nivel
arriba de la carpeta config/ donde reside este modulo.
"""

import os
import sys
import json
from pathlib import Path
from cryptography.fernet import Fernet

_SERVICIO_KEYRING = "CotizadorSAPB1"
_CUENTA_KEYRING   = "llave_configuracion"


def _obtener_keyring():
    try:
        import keyring
        try:
            import keyring.backends.Windows
            keyring.set_keyring(keyring.backends.Windows.WinVaultKeyring())
        except Exception:
            pass
        return keyring
    except ImportError:
        raise RuntimeError(
            "La libreria 'keyring' no esta instalada.\n"
            "Ejecuta:  pip install keyring"
        )


def _calcular_base_dir() -> Path:
    """
    Devuelve el directorio donde debe vivir config.encrypted.

    Como .exe (PyInstaller): directorio del ejecutable.
    Como script: raiz del proyecto (parent.parent de este archivo).
      secure_config.py esta en:  raiz/config/secure_config.py
      parent                  =  raiz/config/
      parent.parent           =  raiz/           <- aqui va config.encrypted
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent.parent


class SecureConfig:

    def __init__(self):
        self.base_dir       = _calcular_base_dir()
        self.archivo_config = self.base_dir / "config.encrypted"

    # ------------------------------------------------------------------
    #  Gestion de la llave en DPAPI
    # ------------------------------------------------------------------

    def _obtener_cifrador(self) -> Fernet:
        try:
            kr        = _obtener_keyring()
            llave_str = kr.get_password(_SERVICIO_KEYRING, _CUENTA_KEYRING)
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"Error al acceder a Windows Credential Manager: {e}\n\n"
                "Ejecuta crear_config.py en esta maquina."
            )

        if not llave_str:
            raise FileNotFoundError(
                "No se encontro la llave de cifrado en Windows Credential Manager.\n\n"
                "Ejecuta crear_config.py en esta maquina."
            )

        try:
            return Fernet(llave_str.encode())
        except Exception as e:
            raise RuntimeError(
                f"La llave en Windows Credential Manager es invalida: {e}\n\n"
                "Ejecuta crear_config.py para regenerarla."
            )

    @staticmethod
    def guardar_llave_en_dpapi(llave: bytes) -> None:
        kr = _obtener_keyring()
        try:
            kr.set_password(_SERVICIO_KEYRING, _CUENTA_KEYRING, llave.decode())
            print("[OK] Llave guardada en Windows Credential Manager.")
        except Exception as e:
            raise RuntimeError(
                f"No se pudo guardar la llave en Windows Credential Manager: {e}"
            )

    @staticmethod
    def llave_existe_en_dpapi() -> bool:
        try:
            kr    = _obtener_keyring()
            valor = kr.get_password(_SERVICIO_KEYRING, _CUENTA_KEYRING)
            return valor is not None and len(valor) > 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    #  Operaciones sobre el archivo cifrado
    # ------------------------------------------------------------------

    def guardar_config(self, config: dict) -> bool:
        try:
            cifrador    = self._obtener_cifrador()
            config_json = json.dumps(config, indent=2, ensure_ascii=False)
            cifrado     = cifrador.encrypt(config_json.encode("utf-8"))

            with open(self.archivo_config, "wb") as f:
                f.write(cifrado)

            if os.name != "nt":
                os.chmod(self.archivo_config, 0o600)

            print(f"[OK] Configuracion guardada en: {self.archivo_config}")
            return True
        except Exception as e:
            print(f"[ERROR] No se pudo guardar la configuracion: {e}")
            return False

    def cargar_config(self) -> dict:
        if not self.archivo_config.exists():
            raise FileNotFoundError(
                f"No se encontro config.encrypted en: {self.archivo_config}\n\n"
                "Ejecuta: python crear_config.py"
            )
        cifrador   = self._obtener_cifrador()
        cifrado    = self.archivo_config.read_bytes()
        descifrado = cifrador.decrypt(cifrado)
        return json.loads(descifrado.decode("utf-8"))

    # Aliases en ingles para compatibilidad
    def load_config(self) -> dict:
        return self.cargar_config()

    def save_config(self, config: dict) -> bool:
        return self.guardar_config(config)
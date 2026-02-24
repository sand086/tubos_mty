from cryptography.fernet import Fernet
import os
import json
from pathlib import Path

class CredentialManager:
    """Gestiona credenciales cifradas"""
    
    def __init__(self, key: str = None):
        """
        key: variable de entorno que contiene la clave Fernet
        Si no se proporciona, intenta leerla de SAP_CRYPT_KEY
        """
        if key is None:
            key = os.getenv("SAP_CRYPT_KEY")
            if not key:
                raise ValueError(
                    "❌ Variable de entorno SAP_CRYPT_KEY no configurada.\n"
                    "Genera una con: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )
        
        try:
            self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            raise ValueError(f"❌ Clave de encriptación inválida: {e}")

    def encrypt_credentials(self, credentials: dict) -> str:
        """Cifra un diccionario de credenciales"""
        data = json.dumps(credentials)
        encrypted = self.cipher.encrypt(data.encode())
        return encrypted.decode()

    def decrypt_credentials(self, encrypted_data: str) -> dict:
        """Descifra credenciales"""
        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            return json.loads(decrypted.decode())
        except Exception as e:
            raise ValueError(f"❌ Error descifrando credenciales: {e}")

    def save_credentials(self, credentials: dict, filepath: Path):
        """Guarda credenciales cifradas en archivo"""
        encrypted = self.encrypt_credentials(credentials)
        with open(filepath, 'w') as f:
            f.write(encrypted)
        # Permisos restrictivos (Linux/Mac)
        try:
            os.chmod(filepath, 0o600)
        except:
            pass

    def load_credentials(self, filepath: Path) -> dict:
        """Carga credenciales cifradas desde archivo"""
        if not filepath.exists():
            return None
        with open(filepath, 'r') as f:
            encrypted = f.read()
        return self.decrypt_credentials(encrypted)

# Uso:
# manager = CredentialManager()
# manager.save_credentials({"user": "admin", "password": "***"}, Path("creds.enc"))
# creds = manager.load_credentials(Path("creds.enc"))

"""
Gestor de configuración segura con encriptación
SOLO usa config.encrypted y config.key
"""
import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet
import json


class SecureConfig:
    """Maneja configuración encriptada"""
    
    def __init__(self):
        # Determinar directorio base
        if getattr(sys, 'frozen', False):
            self.base_dir = Path(sys.executable).parent
        else:
            self.base_dir = Path(__file__).parent.parent
        
        self.config_file = self.base_dir / "config.encrypted"
        self.key_file = self.base_dir / "config.key"
        
        print(f"[CONFIG] Directorio base: {self.base_dir}")
        print(f"[CONFIG] Buscando config.key: {self.key_file}")
        print(f"[CONFIG] Buscando config.encrypted: {self.config_file}")
        
        # Cargar clave (NO generar automáticamente)
        self.cipher = self._get_cipher()
    
    def _get_cipher(self) -> Fernet:
        """Obtiene la clave de encriptación (NO la genera)"""
        
        # Verificar que existe config.key
        if not self.key_file.exists():
            raise FileNotFoundError(
                f"❌ No se encontró config.key en: {self.key_file}\n\n"
                f"SOLUCIÓN:\n"
                f"1. Ejecuta: python crear_config.py\n"
                f"2. Copia config.key junto al ejecutable\n"
                f"3. Copia config.encrypted junto al ejecutable"
            )
        
        # Cargar clave
        try:
            with open(self.key_file, 'rb') as f:
                key = f.read().strip()
                
            if not key:
                raise ValueError("Archivo config.key está vacío")
            
            print(f"[OK] Clave cargada desde: {self.key_file}")
            return Fernet(key)
            
        except Exception as e:
            raise RuntimeError(
                f"❌ No se pudo cargar config.key: {e}\n\n"
                f"Verifica que el archivo config.key sea válido\n"
                f"o re-ejecuta: python crear_config.py"
            )
    
    def save_config(self, config: dict) -> bool:
        """Guarda configuración encriptada"""
        try:
            # Convertir a JSON
            config_json = json.dumps(config, indent=2, ensure_ascii=False)
            
            # Encriptar
            encrypted = self.cipher.encrypt(config_json.encode('utf-8'))
            
            # Guardar
            with open(self.config_file, 'wb') as f:
                f.write(encrypted)
            
            # Permisos restrictivos en Unix
            if os.name != 'nt':
                os.chmod(self.config_file, 0o600)
            
            print(f"[OK] Configuración guardada en: {self.config_file}")
            return True
            
        except Exception as e:
            print(f"[ERROR] No se pudo guardar configuración: {e}")
            return False
    
    def load_config(self) -> dict:
        """Carga configuración encriptada"""
        try:
            if not self.config_file.exists():
                raise FileNotFoundError(
                    f"❌ No se encontró config.encrypted en: {self.config_file}\n\n"
                    f"Ejecuta: python crear_config.py"
                )
            
            # Leer archivo encriptado
            with open(self.config_file, 'rb') as f:
                encrypted = f.read()
            
            # Desencriptar
            decrypted = self.cipher.decrypt(encrypted)
            
            # Parsear JSON
            config = json.loads(decrypted.decode('utf-8'))
            
            print("[OK] Configuración encriptada cargada correctamente")
            return config
            
        except Exception as e:
            print(f"[ERROR] No se pudo cargar configuración: {e}")
            raise
    
    def get(self, key: str, default=None):
        """Obtiene un valor de configuración"""
        config = self.load_config()
        return config.get(key, default)
    
    def set(self, key: str, value):
        """Establece un valor de configuración"""
        config = self.load_config()
        config[key] = value
        return self.save_config(config)


# Script de utilidad para crear configuración inicial
def create_initial_config():
    """Crea configuración inicial encriptada"""
    
    print("\n" + "="*70)
    print("CREADOR DE CONFIGURACIÓN ENCRIPTADA")
    print("="*70 + "\n")
    
    print("Este script creará config.key y config.encrypted")
    print("NO necesitas .env.secure\n")
    
    # Solicitar datos
    config = {}
    
    print("CONFIGURACIÓN DE SAP BUSINESS ONE")
    print("-"*70)
    config["SAP_BASE_URL"] = input("SAP_BASE_URL (ej: https://192.168.1.100:50000/b1s/v1): ").strip()
    config["SAP_COMPANYDB"] = input("SAP_COMPANYDB (ej: SBO_EMPRESA): ").strip()
    config["SAP_TIMEOUT"] = input("SAP_TIMEOUT en segundos [30]: ").strip() or "30"
    
    print("\nCONFIGURACIÓN SSL")
    print("-"*70)
    ssl_verify = input("¿Verificar certificados SSL? (s/n) [s]: ").strip().lower()
    config["SSL_VERIFY"] = "false" if ssl_verify == 'n' else "true"
    config["SAP_SSL_CERT"] = input("Ruta al certificado SSL (Enter para omitir): ").strip()
    
    print("\nCONFIGURACIÓN DE SESIÓN")
    print("-"*70)
    config["SESSION_TIMEOUT_MINUTES"] = input("Timeout de sesión en minutos [15]: ").strip() or "15"
    
    print("\n" + "-"*70)
    print("CONFIGURACIÓN A GUARDAR:")
    print("-"*70)
    for key, value in config.items():
        print(f"  {key}: {value}")
    print("-"*70 + "\n")
    
    confirm = input("¿Guardar esta configuración? (s/n): ")
    if confirm.lower() != 's':
        print("\n[INFO] Operación cancelada")
        return
    
    try:
        # Generar clave
        key = Fernet.generate_key()
        key_file = Path("config.key")
        
        with open(key_file, 'wb') as f:
            f.write(key)
        
        if os.name != 'nt':
            os.chmod(key_file, 0o600)
        
        print(f"\n[OK] Clave generada: {key_file.absolute()}")
        
        # Crear instancia y guardar config
        secure_config = SecureConfig()
        
        if secure_config.save_config(config):
            print(f"[OK] Configuración guardada: {secure_config.config_file.absolute()}")
            print("\n" + "="*70)
            print("IMPORTANTE - COPIA ESTOS ARCHIVOS JUNTO AL EJECUTABLE:")
            print("="*70)
            print(f"1. {key_file.absolute()}")
            print(f"2. {secure_config.config_file.absolute()}")
            print("\nNO INCLUYAS .env.secure (ya no se usa)")
            print("="*70)
        else:
            print("\n[ERROR] No se pudo guardar la configuración")
            
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        create_initial_config()
    except KeyboardInterrupt:
        print("\n\n[INFO] Operación cancelada por el usuario")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
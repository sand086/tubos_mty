import requests
import ssl
import certifi
from typing import Optional

class SSLValidator:
    """Valida certificados SSL/TLS de SAP B1"""
    
    @staticmethod
    def get_session(verify_ssl: bool = True, ca_cert: Optional[str] = None) -> requests.Session:
        """
        Crea una sesión de requests segura
        
        Args:
            verify_ssl: Si validar certificados (siempre True en prod)
            ca_cert: Ruta al certificado CA personalizado (si SAP B1 usa cert autofirmado)
        """
        session = requests.Session()
        
        if verify_ssl:
            if ca_cert:
                # Si SAP B1 tiene un certificado autofirmado, proporcionar su CA
                session.verify = ca_cert
            else:
                # Usar certificados del sistema (de certifi)
                session.verify = certifi.where()
        
        return session
    
    @staticmethod
    def install_ca_cert(ca_pem_path: str):
        """
        Instala un certificado CA en el almacén del sistema
        Requiere permisos administrativos
        """
        import subprocess
        import sys
        
        try:
            if sys.platform == 'win32':
                subprocess.run([
                    'certutil', '-addstore', '-f', 'ROOT', ca_pem_path
                ], check=True, capture_output=True)
                print(f"✅ Certificado instalado en Windows")
            elif sys.platform == 'darwin':
                subprocess.run([
                    'sudo', 'security', 'add-trusted-cert', '-d', '-r', 'trustRoot',
                    '-k', '/Library/Keychains/System.keychain', ca_pem_path
                ], check=True)
                print(f"✅ Certificado instalado en macOS")
            else:
                subprocess.run([
                    'sudo', 'cp', ca_pem_path, '/usr/local/share/ca-certificates/'
                ], check=True)
                subprocess.run(['sudo', 'update-ca-certificates'], check=True)
                print(f"✅ Certificado instalado en Linux")
        except Exception as e:
            print(f"❌ Error instalando certificado: {e}")

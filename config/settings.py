"""
Configuración centralizada de la aplicación
Versión CORREGIDA - SOLO usa config.encrypted
"""

import os
import sys
from pathlib import Path


# ==================== CARGAR CONFIGURACIÓN ENCRIPTADA ====================
print("[INIT] Cargando configuración encriptada...")

try:
    from config.secure_config import SecureConfig
    
    secure_config = SecureConfig()
    encrypted_config = secure_config.load_config()
    
    # Aplicar configuración encriptada como variables de entorno
    for key, value in encrypted_config.items():
        if not os.getenv(key):  # Solo si no está ya definida
            os.environ[key] = str(value)
    
    print("[OK] Configuración encriptada cargada")
    
except FileNotFoundError as e:
    print(f"[ERROR] {e}")
    print("\nSolución:")
    print("1. Ejecuta: python crear_config.py")
    print("2. Copia config.key y config.encrypted junto al ejecutable")
    sys.exit(1)
    
except Exception as e:
    print(f"[ERROR] No se pudo cargar configuración encriptada: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# ==================== RUTAS ====================
if getattr(sys, 'frozen', False):
    # Ejecutando como .exe
    BASE_DIR = Path(sys.executable).parent
    INTERNAL_DIR = Path(sys._MEIPASS)
else:
    # Ejecutando como script
    BASE_DIR = Path(__file__).resolve().parent.parent
    INTERNAL_DIR = BASE_DIR


CREDS_FILE = BASE_DIR / "config" / "credentials.enc"
LOGS_DIR = BASE_DIR / "logs"
TEMP_DIR = BASE_DIR / ".temp"

# Crear directorios si no existen
LOGS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)


# ==================== CONFIGURACIÓN SAP ====================
SAP_BASE_URL = os.getenv("SAP_BASE_URL")
SAP_TIMEOUT = int(os.getenv("SAP_TIMEOUT", "30"))
SAP_MAX_RESULTS = int(os.getenv("SAP_MAX_RESULTS", "10000"))
SAP_PAGE_SIZE = int(os.getenv("SAP_PAGE_SIZE", "20"))
SAP_SEARCH_TIMEOUT = int(os.getenv("SAP_SEARCH_TIMEOUT", "60"))

# Validar SAP_BASE_URL
if not SAP_BASE_URL:
    print("[ERROR] SAP_BASE_URL no configurada en config.encrypted")
    sys.exit(1)


# ==================== GESTIÓN DE SESIONES ====================
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "15"))
SESSION_CHECK_INTERVAL = int(os.getenv("SESSION_CHECK_INTERVAL", "60000"))
ENCRYPTION_KEY_ENV = "SAP_CRYPT_KEY"


# ==================== FUNCIONES SSL ====================
def get_ssl_cert_path() -> str:
    """
    Obtiene ruta al certificado SSL
    Funciona tanto en desarrollo como en ejecutable empaquetado
    
    Returns:
        str: Ruta al certificado o None
    """
    # Si viene en la config encriptada, usarla
    cert_from_config = os.getenv("SAP_SSL_CERT", "").strip()
    if cert_from_config and Path(cert_from_config).exists():
        print(f"[OK] Certificado SSL desde config: {cert_from_config}")
        return cert_from_config
    
    if getattr(sys, 'frozen', False):
        # Ejecutando como .exe (PyInstaller)
        base_path = Path(sys._MEIPASS)
        
        # Buscar certificado en múltiples ubicaciones
        cert_locations = [
            base_path / 'config' / '187.217.73.242.crt',
            base_path / 'config' / 'sap_cert.crt',
            base_path / 'credentials' / '187.217.73.242.crt',
            base_path / 'credentials' / 'sap_cert.crt',
        ]
        
        for cert_path in cert_locations:
            if cert_path.exists():
                print(f"[OK] Certificado SSL encontrado: {cert_path}")
                return str(cert_path)
    
    print("[WARN] No se encontró certificado SSL personalizado")
    return None


def get_secure_session(
    base_url: str = None, 
    timeout: int = None, 
    ssl_verify: bool = None, 
    ssl_cert_path: str = None
):
    """
    Fábrica para crear sesiones seguras con SAP
    
    Args:
        base_url: URL base de SAP (usa SAP_BASE_URL si None)
        timeout: Timeout en segundos (usa SAP_TIMEOUT si None)
        ssl_verify: Si verificar SSL (usa SSL_VERIFY si None)
        ssl_cert_path: Ruta al certificado CA (usa SSLCERTPATH si None)
    
    Returns:
        SecureSessionManager: Gestor de sesiones configurado
    """
    from security.session_manager import SecureSessionManager
    
    # Usar valores por defecto del módulo si no se proporcionan
    if base_url is None:
        base_url = SAP_BASE_URL
    if timeout is None:
        timeout = SAP_TIMEOUT
    if ssl_verify is None:
        ssl_verify = globals().get('SSL_VERIFY', True)
    if ssl_cert_path is None:
        ssl_cert_path = globals().get('SSLCERTPATH', None)
    
    # Validación: base_url no puede ser None
    if not base_url:
        raise ValueError(
            "SAP_BASE_URL no configurada correctamente.\n"
            "Ejecuta: python crear_config.py"
        )
    
    return SecureSessionManager(
        base_url=base_url,
        timeout=timeout,
        ssl_verify=ssl_verify,
        ssl_cert_path=ssl_cert_path
    )


# ==================== CONFIGURACIÓN SSL ====================
SSL_VERIFY_STR = os.getenv("SSL_VERIFY", "true").lower()
SSL_VERIFY = SSL_VERIFY_STR in ("true", "1", "yes", "on")
SSLCERTPATH = get_ssl_cert_path()

print(f"[CONFIG] SSL Verify: {SSL_VERIFY}")
if SSLCERTPATH:
    print(f"[CONFIG] SSL Cert: {SSLCERTPATH}")


# ==================== CREDENCIALES ====================
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "3"))
LOGIN_ATTEMPT_DELAY = int(os.getenv("LOGIN_ATTEMPT_DELAY", "2"))


# ==================== INTERFAZ PYQT ====================
UI_STYLE = os.getenv("UI_STYLE", "Fusion")
DEFAULT_FONT_SIZE = int(os.getenv("DEFAULT_FONT_SIZE", "10"))


# ==================== PDF ====================
PDF_TEMP_CLEANUP = os.getenv("PDF_TEMP_CLEANUP", "true").lower() in ("true", "1", "yes")
PDF_COMPRESSION = os.getenv("PDF_COMPRESSION", "true").lower() in ("true", "1", "yes")


# ==================== INFORMACIÓN DE LA EMPRESA ====================
COMPANY_NAME = "TUBOS MONTERREY S.A. DE C.V."
COMPANY_RFC = "TMO831114V9"
COMPANY_ADDRESS = "Poniente 122 # 603, Col: Industrial Vallejo, Alcaldía: Azcapotzalco, C.P. 02300, CDMX"
COMPANY_PHONE = "(55) 50787700"
COMPANY_WEBSITE = "https://www.tubosmonterrey.com.mx"
COMPANY_EMAIL = "ventas@tubosmonterrey.com.mx"


# ==================== CLIENTES AUTORIZADOS ====================
CLIENTES_AUTORIZADOS = [
    {
        'CardCode': 'C002650',
        'CardName': 'VILLATUBOS S.A. DE C.V.',
        'FederalTaxID': 'VIL080813MC4',
        'EmailAddress': 'encargadoalmacen@villatubos.com.mx; mherrera@villatubos.com.mx',
        'Phone1': '2292004642',
        'PaymentTermsCode': '30 días',
        'Address': 'CARRETERA FEDERAL SAN JULIAN PASO DEL TORO 401, NUEVA DR DELFINO A VICTORIA',
        'City': 'VERACRUZ',
        'State': 'VERACRUZ',
        'ZipCode': '91690'
    },
    {
        'CardCode': 'C000417',
        'CardName': 'ACEROS Y TUBOS DE YUCATAN S.A. DE C.V.',
        'FederalTaxID': 'ATY831231284',
        'EmailAddress': 'compras@acerosyuc.com.mx; gaarcila@acerosyuc.com.mx; mmatus@acerosyuc.com.mx',
        'Phone1': '9999206565',
        'PaymentTermsCode': '30 días',
        'Address': '21 226 A, ROMA',
        'City': 'MERIDA',
        'State': 'YUCATAN',
        'ZipCode': '97218'
    }
]


# ==================== DESCUENTOS MÁXIMOS POR GRUPO ====================
DESCUENTOS_MAXIMOS_POR_GRUPO = {
    "101": 32.8, "102": 53, "103": 50, "104": 57, "105": 48,
    "106": 53, "108": 53, "109": 50, "110": 50, "112": 45,
    "113": 42, "114": 42, "115": 50, "116": 50, "117": 50,
    "118": 40, "119": 40, "120": 40, "121": 40, "122": 40,
    "123": 40, "125": 40, "127": 50, "128": 40, "129": 55,
    "130": 55, "131": 55, "132": 50, "133": 40, "134": 57,
    "135": 57, "136": 57, "137": 57, "138": 56, "139": 56,
    "140": 45, "141": 42, "142": 40, "143": 40, "144": 50,
    "145": 40, "146": 40, "147": 40, "153": 55, "176": 8
}


# ==================== CONFIGURACIÓN DE ALERTAS UI ====================
ALERTA_DESCUENTO_COLOR = "#FFC107"
DESCUENTO_BLOQUEADO_COLOR = "#F44336"


# ==================== VALIDACIONES DE CONFIGURACIÓN ====================
def validate_configuration():
    """
    Valida que la configuración esté completa y correcta
    Retorna lista de advertencias/errores
    """
    issues = []
    
    if not SAP_BASE_URL:
        issues.append("❌ CRÍTICO: SAP_BASE_URL no configurada")
    elif not SAP_BASE_URL.startswith("https://"):
        issues.append("⚠️ SAP_BASE_URL no usa HTTPS")
    
    if SSL_VERIFY and not SSLCERTPATH:
        issues.append("⚠️ SSL activado pero sin certificado personalizado (usará certifi)")
    
    return issues


# Ejecutar validación al importar
validation_issues = validate_configuration()
if validation_issues:
    print("\n[VALIDACIÓN] Advertencias de configuración:")
    for issue in validation_issues:
        print(f"  {issue}")
    print()
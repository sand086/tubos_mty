"""
Configuración centralizada de la aplicación
--------------------------------------------
Cambios de seguridad (v2):
  • Usa SecureConfig con DPAPI en lugar de config.key en disco.
  • Se agregaron GAS_URL y GAS_TOKEN para el middleware de licencias.
  • Eliminadas referencias a gspread y google-auth.
  • Aliases de compatibilidad para todos los nombres usados en otros módulos.
"""

import os
import sys
from pathlib import Path


# ══════════════════════════════════════════════════════════════
#  CARGAR CONFIGURACIÓN CIFRADA DESDE DPAPI
# ══════════════════════════════════════════════════════════════
print("[INIT] Cargando configuracion cifrada...")

try:
    from .secure_config import SecureConfig

    _config_segura = SecureConfig()
    _config_cifrada = _config_segura.cargar_config()

    # Exponer cada clave como variable de entorno (solo si no está ya definida)
    for _clave, _valor in _config_cifrada.items():
        if not os.getenv(_clave):
            os.environ[_clave] = str(_valor)

    print("[OK] Configuracion cifrada cargada.")

except FileNotFoundError as e:
    print(f"[ERROR] {e}")
    print(
        "\nSOLUCION:\n"
        "  1. Ejecuta: python crear_config.py\n"
        "  2. Copia config.encrypted junto al ejecutable."
    )
    sys.exit(1)

except Exception as e:
    print(f"[ERROR] No se pudo cargar la configuracion cifrada: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# ══════════════════════════════════════════════════════════════
#  RUTAS
# ══════════════════════════════════════════════════════════════
if getattr(sys, "frozen", False):
    DIRECTORIO_BASE    = Path(sys.executable).parent
    DIRECTORIO_INTERNO = Path(sys._MEIPASS)
else:
    DIRECTORIO_BASE    = Path(__file__).resolve().parent.parent
    DIRECTORIO_INTERNO = DIRECTORIO_BASE

RUTA_CREDENCIALES = DIRECTORIO_BASE / "config" / "credentials.enc"
DIRECTORIO_LOGS   = DIRECTORIO_BASE / "logs"
DIRECTORIO_TEMP   = DIRECTORIO_BASE / ".temp"

DIRECTORIO_LOGS.mkdir(exist_ok=True)
DIRECTORIO_TEMP.mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════
#  CONFIGURACIÓN SAP BUSINESS ONE
# ══════════════════════════════════════════════════════════════
SAP_BASE_URL       = os.getenv("SAP_BASE_URL")
SAP_TIMEOUT        = int(os.getenv("SAP_TIMEOUT", "30"))
SAP_MAX_RESULTS    = int(os.getenv("SAP_MAX_RESULTS", "10000"))
SAP_PAGE_SIZE      = int(os.getenv("SAP_PAGE_SIZE", "20"))
SAP_SEARCH_TIMEOUT = int(os.getenv("SAP_SEARCH_TIMEOUT", "60"))

if not SAP_BASE_URL:
    print("[ERROR] SAP_BASE_URL no esta configurada en config.encrypted.")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════
#  MIDDLEWARE DE LICENCIAS (Google Apps Script)
# ══════════════════════════════════════════════════════════════
GAS_URL   = os.getenv("GAS_URL", "").strip()
GAS_TOKEN = os.getenv("GAS_TOKEN", "").strip()


# ══════════════════════════════════════════════════════════════
#  GESTIÓN DE SESIONES
# ══════════════════════════════════════════════════════════════
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "15"))
SESSION_CHECK_INTERVAL  = int(os.getenv("SESSION_CHECK_INTERVAL", "60000"))
ENCRYPTION_KEY_ENV      = "SAP_CRYPT_KEY"


# ══════════════════════════════════════════════════════════════
#  SSL
# ══════════════════════════════════════════════════════════════
def obtener_ruta_certificado_ssl() -> str:
    """
    Devuelve la ruta al certificado SSL personalizado.
    Funciona tanto en desarrollo como en ejecutable empaquetado.
    """
    cert_desde_config = os.getenv("SAP_SSL_CERT", "").strip()
    if cert_desde_config and Path(cert_desde_config).exists():
        print(f"[OK] Certificado SSL desde config: {cert_desde_config}")
        return cert_desde_config

    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
        ubicaciones = [
            base_path / "config" / "187.217.73.242.crt",
            base_path / "config" / "sap_cert.crt",
        ]
        for ruta in ubicaciones:
            if ruta.exists():
                print(f"[OK] Certificado SSL encontrado: {ruta}")
                return str(ruta)
    else:
        # Modo desarrollo: buscar en el directorio del proyecto
        base_dev = Path(__file__).resolve().parent.parent
        ubicaciones_dev = [
            base_dev / "config" / "187.217.73.242.crt",
            base_dev / "config" / "sap_cert.crt",
        ]
        for ruta in ubicaciones_dev:
            if ruta.exists():
                print(f"[OK] Certificado SSL encontrado: {ruta}")
                return str(ruta)

    print("[AVISO] No se encontro certificado SSL personalizado.")
    return None


def obtener_sesion_segura(
    base_url: str = None,
    timeout: int = None,
    ssl_verify: bool = None,
    ssl_cert_path: str = None,
):
    """
    Fábrica para crear gestores de sesión seguros con SAP.

    Args:
        base_url: URL base de SAP (usa SAP_BASE_URL si None).
        timeout: Timeout en segundos (usa SAP_TIMEOUT si None).
        ssl_verify: Si verificar SSL (usa SSL_VERIFY si None).
        ssl_cert_path: Ruta al certificado CA.

    Returns:
        SecureSessionManager configurado.
    """
    from security.session_manager import SecureSessionManager

    if base_url      is None: base_url      = SAP_BASE_URL
    if timeout       is None: timeout       = SAP_TIMEOUT
    if ssl_verify    is None: ssl_verify    = SSL_VERIFY
    if ssl_cert_path is None: ssl_cert_path = SSLCERTPATH

    if not base_url:
        raise ValueError(
            "SAP_BASE_URL no esta configurada.\n"
            "Ejecuta:  python crear_config.py"
        )

    return SecureSessionManager(
        base_url      = base_url,
        timeout       = timeout,
        ssl_verify    = ssl_verify,
        ssl_cert_path = ssl_cert_path,
    )


# Alias de compatibilidad usado por sap_client.py
get_secure_session = obtener_sesion_segura

SSL_VERIFY_STR = os.getenv("SSL_VERIFY", "true").lower()
SSL_VERIFY     = SSL_VERIFY_STR in ("true", "1", "yes", "on")
SSLCERTPATH    = obtener_ruta_certificado_ssl()

print(f"[CONFIG] SSL Verify : {SSL_VERIFY}")
if SSLCERTPATH:
    print(f"[CONFIG] SSL Cert   : {SSLCERTPATH}")


# ══════════════════════════════════════════════════════════════
#  CREDENCIALES / ACCESOS
# ══════════════════════════════════════════════════════════════
MAX_LOGIN_ATTEMPTS  = int(os.getenv("MAX_LOGIN_ATTEMPTS", "3"))
LOGIN_ATTEMPT_DELAY = int(os.getenv("LOGIN_ATTEMPT_DELAY", "2"))


# ══════════════════════════════════════════════════════════════
#  INTERFAZ PyQt
# ══════════════════════════════════════════════════════════════
UI_STYLE          = os.getenv("UI_STYLE", "Fusion")
DEFAULT_FONT_SIZE = int(os.getenv("DEFAULT_FONT_SIZE", "10"))


# ══════════════════════════════════════════════════════════════
#  PDF
# ══════════════════════════════════════════════════════════════
PDF_TEMP_CLEANUP = os.getenv("PDF_TEMP_CLEANUP", "true").lower() in ("true", "1", "yes")
PDF_COMPRESSION  = os.getenv("PDF_COMPRESSION",  "true").lower() in ("true", "1", "yes")


# ══════════════════════════════════════════════════════════════
#  INFORMACIÓN DE LA EMPRESA
# ══════════════════════════════════════════════════════════════
COMPANY_NAME    = "TUBOS MONTERREY S.A. DE C.V."
COMPANY_RFC     = "TMO831114V9"
COMPANY_ADDRESS = (
    "Poniente 122 # 603, Col: Industrial Vallejo, "
    "Alcaldia: Azcapotzalco, C.P. 02300, CDMX"
)
COMPANY_PHONE   = "(55) 50787700"
COMPANY_WEBSITE = "https://www.tubosmonterrey.com.mx"
COMPANY_EMAIL   = "ventas@tubosmonterrey.com.mx"


# ══════════════════════════════════════════════════════════════
#  CLIENTES AUTORIZADOS
# ══════════════════════════════════════════════════════════════
CLIENTES_AUTORIZADOS = [
    {
        "CardCode"        : "C002650",
        "CardName"        : "VILLATUBOS S.A. DE C.V.",
        "FederalTaxID"    : "VIL080813MC4",
        "EmailAddress"    : "encargadoalmacen@villatubos.com.mx; mherrera@villatubos.com.mx",
        "Phone1"          : "2292004642",
        "PaymentTermsCode": "30 dias",
        "Address"         : "CARRETERA FEDERAL SAN JULIAN PASO DEL TORO 401, "
                            "NUEVA DR DELFINO A VICTORIA",
        "City"            : "VERACRUZ",
        "State"           : "VERACRUZ",
        "ZipCode"         : "91690",
    },
    {
        "CardCode"        : "C000417",
        "CardName"        : "ACEROS Y TUBOS DE YUCATAN S.A. DE C.V.",
        "FederalTaxID"    : "ATY831231284",
        "EmailAddress"    : (
            "compras@acerosyuc.com.mx; gaarcila@acerosyuc.com.mx; "
            "mmatus@acerosyuc.com.mx"
        ),
        "Phone1"          : "9999206565",
        "PaymentTermsCode": "30 dias",
        "Address"         : "21 226 A, ROMA",
        "City"            : "MERIDA",
        "State"           : "YUCATAN",
        "ZipCode"         : "97218",
    },
]


# ══════════════════════════════════════════════════════════════
#  DESCUENTOS MÁXIMOS POR GRUPO
# ══════════════════════════════════════════════════════════════
DESCUENTOS_MAXIMOS_POR_GRUPO = {
    "101": 32.8, "102": 53,   "103": 50,   "104": 57,   "105": 48,
    "106": 53,   "108": 53,   "109": 50,   "110": 50,   "112": 45,
    "113": 42,   "114": 42,   "115": 50,   "116": 50,   "117": 50,
    "118": 40,   "119": 40,   "120": 40,   "121": 40,   "122": 40,
    "123": 40,   "125": 40,   "127": 50,   "128": 40,   "129": 55,
    "130": 55,   "131": 55,   "132": 50,   "133": 40,   "134": 57,
    "135": 57,   "136": 57,   "137": 57,   "138": 56,   "139": 56,
    "140": 45,   "141": 42,   "142": 40,   "143": 40,   "144": 50,
    "145": 40,   "146": 40,   "147": 40,   "153": 55,   "176": 8,
}


# ══════════════════════════════════════════════════════════════
#  CONFIGURACIÓN DE ALERTAS UI
# ══════════════════════════════════════════════════════════════
ALERTA_DESCUENTO_COLOR    = "#FFC107"
DESCUENTO_BLOQUEADO_COLOR = "#F44336"


# ══════════════════════════════════════════════════════════════
#  VALIDACIÓN DE CONFIGURACIÓN AL ARRANCAR
# ══════════════════════════════════════════════════════════════
def validar_configuracion() -> list:
    """Verifica que la configuración esté completa."""
    problemas = []

    if not SAP_BASE_URL:
        problemas.append("CRITICO: SAP_BASE_URL no configurada.")
    elif not SAP_BASE_URL.startswith("https://"):
        problemas.append("AVISO: SAP_BASE_URL no usa HTTPS.")

    if not GAS_URL:
        problemas.append("CRITICO: GAS_URL no configurada (middleware de licencias).")
    if not GAS_TOKEN:
        problemas.append("CRITICO: GAS_TOKEN no configurado (middleware de licencias).")

    if SSL_VERIFY and not SSLCERTPATH:
        problemas.append(
            "AVISO: SSL activado pero sin certificado personalizado (se usara certifi)."
        )

    return problemas


_problemas = validar_configuracion()
if _problemas:
    print("\n[VALIDACION] Advertencias de configuracion:")
    for _p in _problemas:
        print(f"  {_p}")
    print()
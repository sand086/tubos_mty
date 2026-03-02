"""
Script para crear la configuracion inicial cifrada.
-------------------------------------------------------
Ejecutar desde la RAIZ del proyecto:
    python crear_config.py
"""

import sys
import os
import secrets
from pathlib import Path

# Raiz del proyecto = directorio donde esta este script
RAIZ_PROYECTO = Path(__file__).resolve().parent

# sys.path debe incluir la raiz para que "from config.secure_config" funcione
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

# Limpiar __pycache__ para evitar conflictos con .pyc de versiones anteriores
for _cache_dir in [RAIZ_PROYECTO / "config" / "__pycache__",
                   RAIZ_PROYECTO / "__pycache__"]:
    if _cache_dir.exists():
        for _pyc in _cache_dir.glob("*.pyc"):
            try:
                _pyc.unlink()
            except Exception:
                pass

from cryptography.fernet import Fernet
from config.secure_config import SecureConfig


def _limpiar_archivos_obsoletos(directorio: Path) -> None:
    candidatos = [
        directorio / "config.key",
        directorio / "credentials" / "service_account.json",
        directorio / "service_account.json",
    ]
    encontrados = [p for p in candidatos if p.exists()]
    if not encontrados:
        return

    print("\n" + "!" * 70)
    print("ARCHIVOS OBSOLETOS DETECTADOS (representan riesgo de seguridad):")
    for ruta in encontrados:
        print(f"  {ruta}")
    respuesta = input("\n¿Eliminarlos ahora? (s/n) [s]: ").strip().lower()
    if respuesta in ("", "s"):
        for ruta in encontrados:
            try:
                ruta.unlink()
                print(f"[OK] Eliminado: {ruta}")
            except Exception as e:
                print(f"[ERROR] No se pudo eliminar {ruta}: {e}")
    else:
        print("[AVISO] Recuerda eliminarlos manualmente antes de distribuir el .exe")


def crear_configuracion_inicial() -> None:
    print("\n" + "=" * 70)
    print("CREADOR DE CONFIGURACION SEGURA — Cotizador SAP B1 v2")
    print("=" * 70)
    print(f"\nDirectorio del proyecto: {RAIZ_PROYECTO}\n")

    if SecureConfig.llave_existe_en_dpapi():
        print(
            "[AVISO] Ya existe una llave en Windows Credential Manager.\n"
            "        Si continuas se sobreescribira y el config.encrypted\n"
            "        actual quedara inutilizable."
        )
        if input("¿Continuar? (s/n) [n]: ").strip().lower() != "s":
            print("[INFO] Cancelado.")
            return

    # SAP
    print("\nCONFIGURACION SAP BUSINESS ONE")
    print("-" * 70)
    sap_base_url  = input("SAP_BASE_URL  (ej: https://192.168.1.100:50000/b1s/v1): ").strip()
    sap_companydb = input("SAP_COMPANYDB (ej: SBO_EMPRESA, o Enter para pedir en login): ").strip()
    sap_timeout   = input("SAP_TIMEOUT en segundos [30]: ").strip() or "30"

    # SSL
    print("\nCONFIGURACION SSL")
    print("-" * 70)
    ssl_verify   = "false" if input("¿Verificar SSL? (s/n) [s]: ").strip().lower() == "n" else "true"
    sap_ssl_cert = input("Ruta certificado SSL (Enter para omitir): ").strip()

    # Sesion
    print("\nCONFIGURACION DE SESION")
    print("-" * 70)
    session_timeout = input("Timeout sesion en minutos [15]: ").strip() or "15"

    # GAS
    print("\nCONFIGURACION MIDDLEWARE LICENCIAS (Google Apps Script)")
    print("-" * 70)
    gas_url   = input("GAS_URL (URL de implementacion de tu Apps Script): ").strip()
    gas_token = input("GAS_TOKEN (Enter para generar automaticamente): ").strip()
    if not gas_token:
        gas_token = secrets.token_hex(32)
        print(f"\n[OK] Token generado: {gas_token}")
        print("     *** Copia este token a TOKEN_SECRETO en gas_middleware.js ***")
        input("     Presiona Enter cuando lo hayas copiado...")

    log_level = input("\nNivel log (DEBUG/INFO/WARNING/ERROR) [INFO]: ").strip() or "INFO"

    config = {
        "SAP_BASE_URL"            : sap_base_url,
        "SAP_COMPANYDB"           : sap_companydb,
        "SAP_TIMEOUT"             : sap_timeout,
        "SAP_SSL_CERT"            : sap_ssl_cert,
        "SSL_VERIFY"              : ssl_verify,
        "SESSION_TIMEOUT_MINUTES" : session_timeout,
        "GAS_URL"                 : gas_url,
        "GAS_TOKEN"               : gas_token,
        "LOG_LEVEL"               : log_level,
    }

    print("\nCONFIGURACION A GUARDAR:")
    print("-" * 70)
    for k, v in config.items():
        print(f"  {k}: {'*'*8+'...' if k=='GAS_TOKEN' else v}")

    if input("\n¿Guardar? (s/n): ").strip().lower() != "s":
        print("[INFO] Cancelado.")
        return

    # Guardar llave en DPAPI
    print("\n[1/2] Guardando llave en Windows Credential Manager...")
    try:
        llave = Fernet.generate_key()
        SecureConfig.guardar_llave_en_dpapi(llave)
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    # Cifrar y guardar config.encrypted
    print("[2/2] Cifrando configuracion...")
    try:
        cfg = SecureConfig()
        # Forzar que config.encrypted quede en la raiz del proyecto
        cfg.base_dir       = RAIZ_PROYECTO
        cfg.archivo_config = RAIZ_PROYECTO / "config.encrypted"

        if cfg.guardar_config(config):
            print(f"\n[OK] config.encrypted guardado en:\n     {cfg.archivo_config}")
        else:
            print("[ERROR] No se pudo guardar la configuracion.")
            return
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback; traceback.print_exc()
        return

    _limpiar_archivos_obsoletos(RAIZ_PROYECTO)

    print("\n" + "=" * 70)
    print("LISTO. Configuracion completada correctamente.")
    print("=" * 70)
    print(
        "\n[OK] Llave protegida por DPAPI en esta maquina."
        "\n[OK] config.encrypted cifrado en la raiz del proyecto."
        "\n\nPara nuevas maquinas:"
        "\n  1. Copia config.encrypted al directorio del .exe"
        "\n  2. Ejecuta crear_config.py en esa maquina"
    )


if __name__ == "__main__":
    try:
        crear_configuracion_inicial()
    except KeyboardInterrupt:
        print("\n[INFO] Cancelado por el usuario.")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback; traceback.print_exc()
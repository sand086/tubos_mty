# -*- mode: python ; coding: utf-8 -*-
#
# Archivo de construcción — Cotizador SAP B1 (v2 Seguro)
# -------------------------------------------------------
# Cambios de seguridad respecto a la versión anterior:
#   • ELIMINADO: credentials/service_account.json del array datas.
#   • ELIMINADO: config.key del array datas.
#   • AGREGADO:  keyring y todos sus backends/módulos internos para
#                Windows Credential Manager (DPAPI).
#   • ELIMINADOS hiddenimports de gspread y google-auth.

import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Certificado SSL para SAP (no contiene credenciales)
        ('config/*.crt', 'config'),
        # NOTA: service_account.json YA NO se incluye aquí.
        # NOTA: config.key YA NO se incluye aquí.
    ],
    hiddenimports=[
        # ── Interfaz gráfica ──────────────────────────────────────────
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        # ── Red ───────────────────────────────────────────────────────
        'requests',
        'certifi',
        # ── Criptografía ──────────────────────────────────────────────
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.backends',
        # ── Keyring / DPAPI Windows ───────────────────────────────────
        # Es fundamental incluir TODOS los módulos internos de keyring
        # para que PyInstaller los empaquete correctamente.
        # Sin estos el ejecutable crashea silenciosamente al arrancar.
        'keyring',
        'keyring.core',
        'keyring.credentials',
        'keyring.errors',
        'keyring.util',
        'keyring.util.platform_',
        'keyring.util.properties',
        'keyring.backends',
        'keyring.backends.Windows',       # Backend DPAPI de Windows
        'keyring.backends._win_crypto',   # Módulo interno de cifrado Windows
        'keyring.backends.fail',           # Fallback si no hay backend
        'keyring.backends.null',           # Backend nulo (desarrollo)
        # ── Utilidades ────────────────────────────────────────────────
        'dotenv',
        'json',
        'pathlib',
        'threading',
        'tempfile',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Excluir explícitamente las librerías de Google que ya no se usan
        'gspread',
        'google.auth',
        'google.oauth2',
        'google.oauth2.service_account',
        'google.auth.transport',
        'google_auth_httplib2',
        'googleapiclient',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Cotizador_SAP_B1_Seguro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # Cambiar a True para depuración
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='sap_logo_icon_170763.ico' if os.path.exists('sap_logo_icon_170763.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Cotizador_SAP_B1_Seguro',
)
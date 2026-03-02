"""
Main — Punto de entrada de la aplicacion
-----------------------------------------
Cambios de seguridad (v2):
  • Eliminada la verificacion de config.key (ya no existe).
  • La llave se verifica en Windows Credential Manager (DPAPI).
  • Eliminado input() en arranque (incompatible con console=False).
  • Todos los errores fatales se muestran con QMessageBox.
  • sys.path configurado antes de cualquier importacion del proyecto.
"""

import sys
import os
from pathlib import Path

# ── Rutas base ────────────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    # Ejecutando como .exe compilado
    BASE_PATH = Path(sys._MEIPASS)
    APP_PATH  = Path(sys.executable).parent
else:
    # Ejecutando como script Python
    BASE_PATH = Path(__file__).resolve().parent
    APP_PATH  = BASE_PATH

# Asegurar que la raiz del proyecto esté en sys.path
# Esto evita el error "partially initialized module" por importacion circular
if str(APP_PATH) not in sys.path:
    sys.path.insert(0, str(APP_PATH))
if getattr(sys, "frozen", False) and str(BASE_PATH) not in sys.path:
    sys.path.insert(0, str(BASE_PATH))

print("=" * 60)
print("COTIZADOR SAP B1 - VERSION SEGURA v2")
print("=" * 60)
print(f"[INFO] Directorio aplicacion : {APP_PATH}")
print(f"[INFO] Directorio interno    : {BASE_PATH}")


# ── Inicializar Qt lo antes posible para poder mostrar errores graficos ───────
try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
    _qt_app = QApplication.instance() or QApplication(sys.argv)
except Exception as e:
    print(f"[ERROR FATAL] No se pudo inicializar Qt: {e}")
    sys.exit(1)


def _mostrar_error_fatal(titulo: str, mensaje: str) -> None:
    """Muestra un error fatal con QMessageBox y en consola."""
    print(f"[ERROR FATAL] {titulo}: {mensaje}")
    try:
        QMessageBox.critical(None, titulo, mensaje)
    except Exception:
        pass


# ── Verificar config.encrypted ────────────────────────────────────────────────
print("\n[INICIO] Verificando archivos criticos...")

archivo_config = APP_PATH / "config.encrypted"

if not archivo_config.exists():
    _mostrar_error_fatal(
        "Error de Configuracion",
        f"No se encontro config.encrypted en:\n{archivo_config}\n\n"
        "SOLUCION:\n"
        "  1. Ejecuta crear_config.py en esta maquina.\n"
        "  2. Asegurate de que config.encrypted este en el mismo\n"
        "     directorio que el ejecutable."
    )
    sys.exit(1)

print(f"[OK] config.encrypted encontrado.")


# ── Verificar llave en Windows Credential Manager (DPAPI) ────────────────────
print("[INICIO] Verificando llave en Windows Credential Manager...")

try:
    from config.secure_config import SecureConfig

    if not SecureConfig.llave_existe_en_dpapi():
        _mostrar_error_fatal(
            "Error de Configuracion",
            "No se encontro la llave de cifrado en\n"
            "Windows Credential Manager.\n\n"
            "SOLUCION:\n"
            "  Ejecuta crear_config.py en esta maquina.\n"
            "  Esto registra la llave de forma segura usando\n"
            "  las credenciales de tu sesion de Windows.\n\n"
            "  Este proceso debe hacerse una sola vez por maquina."
        )
        sys.exit(1)

    print("[OK] Llave en Credential Manager verificada.")

except ImportError as e:
    _mostrar_error_fatal(
        "Error de Importacion",
        f"No se pudo importar el modulo de configuracion:\n\n{e}\n\n"
        "Verifica que la instalacion este completa."
    )
    sys.exit(1)

except Exception as e:
    _mostrar_error_fatal(
        "Error de Configuracion",
        f"No se pudo verificar la llave de cifrado:\n\n{e}\n\n"
        "Ejecuta crear_config.py en esta maquina."
    )
    sys.exit(1)

print("[OK] Todos los requisitos verificados.\n")


# ── Funcion principal ─────────────────────────────────────────────────────────
def main() -> int:
    """Funcion principal con manejo robusto de errores."""
    try:
        # Importar modulos de la aplicacion
        # settings.py carga config.encrypted aqui via SecureConfig
        from ui.login_dialog  import LoginDialog
        from ui.main_window   import VentanaPrincipal
        from config.settings  import UI_STYLE

        _qt_app.setStyle(UI_STYLE)

        print("[LOGIN] Iniciando sistema de login...\n")

        login = LoginDialog()

        if login.exec():
            try:
                print("[LOGIN] Login exitoso, iniciando ventana principal...\n")
                ventana = VentanaPrincipal(login.credenciales)
                ventana.show()
                return _qt_app.exec()
            except Exception as e:
                import traceback
                traceback.print_exc()
                mensaje = f"No se pudo iniciar la ventana principal:\n\n{e}"
                print(f"[ERROR] {mensaje}")
                QMessageBox.critical(
                    None,
                    "Error Fatal",
                    mensaje + "\n\nRevisa la consola para mas detalles."
                )
                return 1
        else:
            print("[INFO] Login cancelado por el usuario.")
            return 0

    except ImportError as e:
        import traceback
        traceback.print_exc()
        mensaje = f"Error al importar modulos:\n\n{e}"
        print(f"[ERROR] {mensaje}")
        QMessageBox.critical(None, "Error de Importacion", mensaje)
        return 1

    except Exception as e:
        import traceback
        traceback.print_exc()
        mensaje = f"Error critico:\n\n{e}"
        print(f"[ERROR] {mensaje}")
        QMessageBox.critical(None, "Error Fatal", mensaje)
        return 1


if __name__ == "__main__":
    try:
        codigo_salida = main()
        sys.exit(codigo_salida)
    except KeyboardInterrupt:
        print("\n[INFO] Aplicacion interrumpida.")
        sys.exit(0)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n[ERROR FATAL] {e}")
        sys.exit(1)
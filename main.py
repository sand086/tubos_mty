"""
Main - Punto de entrada de la aplicación
SOLO usa config.encrypted y config.key
"""
import sys
import os
from pathlib import Path

# Configurar ruta base según si es ejecutable o script
if getattr(sys, 'frozen', False):
    # Ejecutando como .exe
    BASE_PATH = Path(sys._MEIPASS)
    APP_PATH = Path(sys.executable).parent
else:
    # Ejecutando como script
    BASE_PATH = Path(__file__).parent
    APP_PATH = BASE_PATH

print("="*60)
print("COTIZADOR SAP B1 - VERSIÓN SEGURA")
print("="*60)
print(f"📁 Directorio aplicación: {APP_PATH}")
print(f"📁 Directorio base: {BASE_PATH}")

# ==========================================
# VERIFICACIÓN DE ARCHIVOS CRÍTICOS
# ==========================================
print("\n🔍 Verificando archivos críticos...")

archivos_criticos = {
    'config.key': APP_PATH / "config.key",
    'config.encrypted': APP_PATH / "config.encrypted",
}

archivos_faltantes = []
for nombre, ruta in archivos_criticos.items():
    if ruta.exists():
        print(f"   ✅ {nombre}: OK")
    else:
        print(f"   ❌ {nombre}: NO ENCONTRADO")
        archivos_faltantes.append((nombre, ruta))

if archivos_faltantes:
    print(f"\n❌ ERROR FATAL: Faltan archivos críticos:")
    for nombre, ruta in archivos_faltantes:
        print(f"   - {nombre} en: {ruta}")
    print("\nLa aplicación NO puede continuar.")
    print("\nSOLUCIÓN:")
    print("1. Ejecuta: python crear_config.py")
    print("2. Copia config.key y config.encrypted junto al ejecutable")
    
    input("\nPresiona Enter para salir...")
    sys.exit(1)

print("✅ Todos los archivos están presentes\n")

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt


def main():
    """Función principal con manejo robusto de errores"""
    app = None
    try:
        # Crear aplicación Qt
        app = QApplication(sys.argv)
        
        # Importar después de crear QApplication
        from ui.login_dialog import LoginDialog
        from ui.main_window import VentanaPrincipal
        from config.settings import UI_STYLE
        
        app.setStyle(UI_STYLE)
        
        print("🔐 Iniciando sistema de login...\n")
        
        # Mostrar diálogo de login
        login = LoginDialog()
        
        if login.exec():
            # Login exitoso
            try:
                print("✅ Login exitoso, iniciando ventana principal...\n")
                ventana = VentanaPrincipal(login.credenciales)
                ventana.show()
                return app.exec()
            except Exception as e:
                error_msg = f"No se pudo iniciar la ventana principal:\n\n{str(e)}"
                print(f"❌ ERROR: {error_msg}")
                
                import traceback
                traceback.print_exc()
                
                QMessageBox.critical(
                    None, 
                    "Error Fatal", 
                    error_msg + "\n\nRevisa la consola para más detalles."
                )
                return 1
        else:
            # Usuario canceló el login
            print("ℹ️ Login cancelado por el usuario")
            return 0
            
    except ImportError as e:
        error_msg = f"Error importando módulos:\n\n{str(e)}"
        print(f"❌ IMPORT ERROR: {error_msg}")
        
        import traceback
        traceback.print_exc()
        
        if app:
            QMessageBox.critical(None, "Error de Importación", error_msg)
        return 1
        
    except Exception as e:
        error_msg = f"Error crítico:\n\n{str(e)}"
        print(f"❌ CRITICAL ERROR: {error_msg}")
        
        import traceback
        traceback.print_exc()
        
        if app:
            QMessageBox.critical(None, "Error Fatal", error_msg)
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ Aplicación interrumpida")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERROR FATAL: {e}")
        import traceback
        traceback.print_exc()
        input("\nPresiona Enter para salir...")
        sys.exit(1)
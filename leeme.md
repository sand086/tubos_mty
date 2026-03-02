# Cotizador SAP B1 — Documentación Técnica
**Tubos Monterrey S.A. de C.V.**
Versión 2.0 — Segura | Python 3.12 + PyQt6 + PyInstaller

---

## Descripción general

Aplicación de escritorio (Fat Client) para Windows que permite a los agentes de ventas consultar stock en SAP Business One, generar cotizaciones en PDF con Excel adjunto, y enviarlas por Outlook. Incorpora validación de licencias por hardware y protección de credenciales mediante DPAPI de Windows.

---

## Estructura del proyecto

```
stock SAP AUDIT\
│
├── main.py                     # Punto de entrada de la aplicación
├── crear_config.py             # Asistente de configuración inicial (NO compilar)
├── build.spec                  # Configuración de PyInstaller
├── requirements.txt            # Dependencias Python
├── config.encrypted            # Configuración cifrada (generada por crear_config.py)
├── leeme.md                    # Este archivo
│
├── config\
│   ├── secure_config.py        # Gestor de cifrado con DPAPI
│   ├── settings.py             # Variables de configuración centralizadas
│   └── 187.217.73.242.crt      # Certificado SSL del servidor SAP
│
├── api\
│   ├── sap_client.py           # Cliente REST para SAP B1 Service Layer
│   └── license_manager.py      # Validación de licencias vía GAS middleware
│
├── ui\
│   ├── main_window.py          # Ventana principal — búsqueda, cotización, PDF
│   ├── login_dialog.py         # Diálogo de login SAP
│   └── license_dialog.py       # Diálogo de validación de licencia
│
├── security\
│   ├── session_manager.py      # Gestión segura de sesiones HTTP con SAP
│   └── crypto.py               # Utilidades de cifrado
│
├── utils\
│   ├── hardware_id.py          # Generación de ID único de hardware
│   └── logger.py               # Sistema de logs
│
└── resources\
    └── logo_tubos.jpg          # Logo de la empresa para el PDF
```

---

## Lenguaje y versión

| Componente | Versión |
|---|---|
| Python | 3.12 |
| Sistema operativo objetivo | Windows 10 / 11 (64 bits) |
| Arquitectura | Fat Client (ejecutable local, sin servidor propio) |

---

## Librerías y dependencias

### Interfaz gráfica
| Librería | Versión | Uso |
|---|---|---|
| PyQt6 | 6.7.0 | Framework de interfaz gráfica (ventanas, diálogos, tablas) |
| PyQt6-sip | 13.6.0 | Bindings C++ requeridos por PyQt6 |

### Comunicación con SAP
| Librería | Versión | Uso |
|---|---|---|
| requests | 2.31.0 | Llamadas HTTP REST a SAP B1 Service Layer |
| certifi | 2024.2.2 | Certificados CA para verificación SSL |

### Generación de documentos
| Librería | Versión | Uso |
|---|---|---|
| reportlab | 4.0.9 | Generación de PDFs con tablas, estilos y QR |
| PyPDF2 | 3.0.1 | Manipulación de PDFs (adjuntar Excel) |
| PyMuPDF (fitz) | — | Incrustación de archivos en PDF (embfile) |
| pandas | 2.2.0 | Construcción de datos tabulares para Excel |
| openpyxl | 3.1.5 | Escritura de archivos .xlsx |
| qrcode[pil] | 7.4.2 | Generación de código QR en el PDF |

### Seguridad y cifrado
| Librería | Versión | Uso |
|---|---|---|
| cryptography | 41.0.7 | Cifrado Fernet (AES-128 CBC) para config.encrypted |
| keyring | 25.2.1 | Acceso a Windows Credential Manager (DPAPI) para proteger la llave |

### Utilidades
| Librería | Versión | Uso |
|---|---|---|
| python-dotenv | 1.0.0 | Carga de variables de entorno |

### Empaquetado
| Herramienta | Versión | Uso |
|---|---|---|
| pyinstaller | 6.3.0 | Compilación a ejecutable .exe de Windows |
| pyinstaller-hooks-contrib | 2024.0 | Hooks adicionales para módulos complejos |

### Librerías eliminadas en v2 (auditoría de seguridad)
Las siguientes librerías existían en la versión 1 y fueron eliminadas al migrar a la arquitectura GAS middleware:

```
gspread==6.0.0                      # El cliente ya no accede directamente a Google Sheets
google-auth==2.27.0                 # Las credenciales GCP solo viven en el servidor GAS
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
google-api-python-client==2.70.0
```

### Herramientas externas requeridas en el equipo
| Servicio / Herramienta | Uso |
|---|---|
| Microsoft Outlook (instalado localmente) | Preparación de correos con PDF y Excel adjuntos via COM (win32com) |
| Google Apps Script (nube) | Middleware de validación de licencias — accede a Google Sheets |

---

## Arquitectura de seguridad (v2)

### Cambios implementados por auditoría ISO/IEC 27001:2022

**Credenciales GCP — Hallazgo ALTO (A.5.17)**

```
Antes:  Cliente .exe  →  service_account.json embebido  →  Google Sheets API
Ahora:  Cliente .exe  →  HTTPS + token secreto  →  GAS Middleware  →  Google Sheets API
```

El cliente nunca toca credenciales de GCP. Solo conoce la URL del GAS y un token secreto cifrado en `config.encrypted`.

**Llave de cifrado — Hallazgo ALTO (A.8.24)**

```
Antes:  config.key (texto plano en disco) + config.encrypted  →  cualquiera puede descifrar
Ahora:  Llave en Windows Credential Manager (DPAPI) + config.encrypted
```

La llave Fernet se almacena en DPAPI mediante `keyring`. DPAPI vincula el cifrado a las credenciales de sesión del empleado: si alguien copia `config.encrypted` a otra máquina no puede descifrarlo.

### Archivos de seguridad relevantes

| Archivo | Ubicación | Descripción |
|---|---|---|
| `config.encrypted` | Raíz del proyecto / junto al .exe | Configuración cifrada con Fernet. Seguro para copiar entre máquinas. |
| Llave Fernet | Windows Credential Manager | Nunca en disco. Vinculada al usuario y máquina por DPAPI. |
| `gas_middleware.js` | Google Apps Script (nube) | Proxy de licencias. Nunca en el cliente. |

---

## Configuración inicial

Antes de ejecutar la aplicación por primera vez en cualquier máquina, ejecutar:

```powershell
python crear_config.py
```

El script solicita los siguientes datos:

| Parámetro | Descripción | Ejemplo |
|---|---|---|
| `SAP_BASE_URL` | URL del servidor SAP B1 Service Layer | `https://187.217.73.242:50000/b1s/v1` |
| `SAP_COMPANYDB` | Base de datos SAP (opcional) | `SBO_TUBOS` |
| `SAP_TIMEOUT` | Timeout de conexión en segundos | `30` |
| `SSL_VERIFY` | Verificar certificado SSL del servidor | `true` / `false` |
| `SAP_SSL_CERT` | Ruta al certificado CA personalizado | `config/187.217.73.242.crt` |
| `SESSION_TIMEOUT_MINUTES` | Minutos de inactividad antes de cerrar sesión | `15` |
| `GAS_URL` | URL de implementación del middleware Google Apps Script | `https://script.google.com/macros/s/.../exec` |
| `GAS_TOKEN` | Token secreto compartido con el GAS | Generado automáticamente (32 bytes hex) |
| `LOG_LEVEL` | Nivel de detalle de los logs | `INFO` |

Al finalizar, el script genera `config.encrypted` en la raíz del proyecto y guarda la llave en Windows Credential Manager. **Este proceso debe repetirse en cada máquina donde se instale el sistema.**

---

## Compilación del ejecutable

### Prerrequisitos

```powershell
# Instalar todas las dependencias
pip install -r requirements.txt

# Verificar que keyring esté instalado (crítico para DPAPI)
pip install keyring==25.2.1

# Limpiar caché de Python para evitar conflictos con versiones anteriores
Remove-Item -Recurse -Force "config\__pycache__"
Remove-Item -Recurse -Force "__pycache__"
```

### Comando de compilación

```powershell
# Desde la raíz del proyecto
pyinstaller build.spec
```

El ejecutable se genera en:
```
dist\Cotizador_SAP_B1_Seguro\Cotizador_SAP_B1_Seguro.exe
```

### Notas importantes sobre build.spec

- `console=False` — modo producción (sin ventana de consola)
- `console=True` — usar temporalmente para depurar errores de arranque
- `config.encrypted` **NO** se embebe en el ejecutable — debe copiarse manualmente junto al .exe
- `service_account.json` y `config.key` fueron eliminados del array `datas`
- Los módulos internos de `keyring` para Windows están declarados explícitamente en `hiddenimports` — sin ellos el .exe no abre

Los hiddenimports críticos de keyring son:

```python
'keyring',
'keyring.core',
'keyring.credentials',
'keyring.errors',
'keyring.util',
'keyring.util.platform_',
'keyring.util.properties',
'keyring.backends',
'keyring.backends.Windows',
'keyring.backends._win_crypto',
'keyring.backends.fail',
'keyring.backends.null',
```

### Depuración del ejecutable

Si el .exe no abre sin mostrar ningún mensaje de error:

1. Cambiar `console=False` a `console=True` en `build.spec`
2. Recompilar: `pyinstaller build.spec`
3. Ejecutar desde PowerShell para ver la traza de error en consola
4. Restaurar `console=False` una vez resuelto el problema

---

## Despliegue en máquinas cliente

Para instalar el sistema en un nuevo equipo de ventas:

1. Copiar la carpeta `dist\Cotizador_SAP_B1_Seguro\` completa al equipo destino
2. Copiar `config.encrypted` al mismo directorio que el ejecutable
3. Ejecutar `crear_config.py` **en esa máquina** (registra la llave en su DPAPI local)
4. Ejecutar `Cotizador_SAP_B1_Seguro.exe`

> La llave DPAPI es específica de cada máquina y sesión de Windows. No se puede copiar entre equipos.

---

## Despliegue del middleware GAS

El archivo `gas_middleware.js` se despliega en https://script.google.com como aplicación web.

### Pasos

1. Abrir https://script.google.com y crear un nuevo proyecto
2. Pegar el contenido de `gas_middleware.js`
3. Generar un token secreto en PowerShell:
   ```powershell
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
4. Editar la variable `TOKEN_SECRETO` en el script con el token generado
5. Verificar que `SPREADSHEET_ID` apunte a la hoja de Google Sheets correcta
6. Menú: **Implementar → Nueva implementación**
   - Tipo: Aplicación web
   - Ejecutar como: Mi cuenta
   - Quién puede acceder: Cualquier persona
7. Copiar la URL de implementación y usarla como `GAS_URL` al correr `crear_config.py`

### Endpoints implementados

| Acción | Descripción |
|---|---|
| `validar_licencia` | Verifica hardware_id + usuario en la hoja de Sheets |
| `registrar_dispositivo` | Da de alta un nuevo equipo con estado "No autorizado" |
| `obtener_estado` | Consulta el estado de autorización de un hardware_id |
| `obtener_usuarios` | Lista los usuarios autorizados para un equipo |
| `actualizar_nombre_pc` | Actualiza el nombre del equipo en la hoja |

### Estructura de la hoja de Google Sheets

| Columna | Contenido |
|---|---|
| A | Hardware ID (identificador único del equipo) |
| B | Nombre del equipo |
| C | Estado: `Autorizado` / `No autorizado` |
| D – G | Usuarios autorizados (uno por columna) |

---

## Flujo de arranque de la aplicación

```
main.py arranca
    |
    |-- Verifica config.encrypted en el directorio del ejecutable
    |       No existe → QMessageBox de error → cierra
    |
    |-- Importa SecureConfig → consulta Windows Credential Manager (DPAPI)
    |       No hay llave → QMessageBox de error → cierra
    |
    |-- Importa settings.py → descifra config.encrypted con la llave DPAPI
    |       Expone variables: SAP_BASE_URL, GAS_URL, GAS_TOKEN, etc.
    |
    |-- Muestra LoginDialog
    |       Dentro del login: muestra LicenseDialog
    |       LicenseDialog → POST HTTPS → GAS Middleware
    |       GAS valida hardware_id + usuario en Google Sheets
    |
    └-- Login exitoso → VentanaPrincipal
            SAPClient.login() → sesión HTTP con SAP B1 Service Layer
            Búsqueda de artículos, cotizaciones, PDF con Excel adjunto
```

---

## Notas técnicas importantes

**`crear_config.py` nunca debe compilarse.** Es una herramienta administrativa que requiere entrada interactiva por consola. Se ejecuta siempre como script Python.

**`config.encrypted` nunca debe incluirse dentro del .exe.** Cada máquina tiene su propio archivo vinculado a su llave DPAPI local. Incluirlo en el ejecutable rompería el modelo de seguridad.

**Limpiar `__pycache__` antes de compilar** si se actualizaron archivos en `config\`:
```powershell
Remove-Item -Recurse -Force "config\__pycache__"
```

**Importaciones dentro del paquete `config\`** deben usar rutas relativas:
```python
# Correcto (dentro de config\settings.py)
from .secure_config import SecureConfig

# Incorrecto (causa importación circular)
from config.secure_config import SecureConfig
```

**Codificación de archivos.** Guardar todos los archivos `.py` en UTF-8 sin BOM para evitar errores de codificación en Windows.

---

## Riesgos residuales pendientes de implementar

| Riesgo | Control | Hallazgo ISO 27001 | Severidad |
|---|---|---|---|
| Ingeniería inversa del ejecutable | Migrar de PyInstaller a Nuitka (compilación AOT a código máquina) | A.8.28 | Medio |
| Parámetros comerciales hardcodeados | Mover `DESCUENTOS_MAXIMOS_POR_GRUPO` y `CLIENTES_AUTORIZADOS` a config.encrypted o a SAP | A.8.32 | Bajo |

---

*Documentación interna — Tubos Monterrey S.A. de C.V.*
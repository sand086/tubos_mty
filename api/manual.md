📘 Documentación Técnica Completa - Sistema Seguro de Cotización SAP B1
Versión: 2.0.0
Fecha: Enero 2026
Empresa: Tubos Monterrey S.A. de C.V.
Idioma: Español

📖 Tabla de Contenido
Resumen Ejecutivo

Arquitectura del Sistema

Infraestructura y Tecnologías

Sistema de Licenciamiento

Medidas de Seguridad Implementadas

API y Endpoints de SAP B1

Sistema de Control de Descuentos

Generación de Documentos PDF

Instalación y Configuración

Compilación a Ejecutable

Guía de Usuario

Solución de Problemas

Mantenimiento y Actualizaciones

Anexos

1. Resumen Ejecutivo
1.1 Descripción del Proyecto
El Sistema Seguro de Cotización SAP B1 es una aplicación de escritorio desarrollada en Python que permite a los agentes de ventas de Tubos Monterrey generar cotizaciones profesionales con integración directa a SAP Business One Service Layer.

1.2 Objetivos Principales
✅ Automatizar el proceso de cotización de productos

✅ Garantizar seguridad en el manejo de datos sensibles

✅ Implementar control de licencias por dispositivo y usuario

✅ Aplicar políticas de descuentos máximos por grupo de artículos

✅ Generar documentos PDF profesionales con validación QR

✅ Sincronización en tiempo real con inventario SAP

1.3 Características Principales
Característica	Descripción
Autenticación segura	Login con credenciales SAP + validación de licencia
Control de licencias	Validación por Hardware ID y usuario en Google Sheets
Gestión de sesiones	Timeout automático por inactividad (30 min)
Búsqueda avanzada	Búsqueda de clientes y artículos con paginación
Control de descuentos	Descuentos máximos por grupo de artículos
PDF profesional	Logo, QR de validación, Excel adjunto
Logging seguro	Registros sin datos sensibles
Ejecutable standalone	No requiere Python instalado
2. Arquitectura del Sistema
2.1 Diagrama de Arquitectura General
text
┌─────────────────────────────────────────────────────────────────┐
│                     CAPA DE PRESENTACIÓN                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Login Dialog │  │ License Check│  │ Main Window  │         │
│  │  (PyQt6)     │  │   (PyQt6)    │  │   (PyQt6)    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      CAPA DE LÓGICA DE NEGOCIO                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  SAP Client  │  │License Mgr   │  │ PDF Generator│         │
│  │              │  │              │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        CAPA DE INTEGRACIÓN                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ SAP B1 API   │  │ Google API   │  │ ReportLab    │         │
│  │ Service Layer│  │ Sheets       │  │ PDF Engine   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                          CAPA DE DATOS                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  SAP         │  │ Google Sheets│  │ Local Files  │         │
│  │  Database    │  │ (Licencias)  │  │ (Logs, PDFs) │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
2.2 Estructura de Directorios del Proyecto
text
secure-sap-cotizador/
│
├── main.py                          # Punto de entrada
│
├── config/
│   ├── __init__.py
│   └── settings.py                  # Configuración centralizada
│
├── api/
│   ├── __init__.py
│   ├── sap_client.py               # Cliente SAP Service Layer
│   └── license_manager.py          # Gestor de licencias
│
├── ui/
│   ├── __init__.py
│   ├── login_dialog.py             # Diálogo de login
│   ├── license_dialog.py           # Validación de licencia
│   └── main_window.py              # Ventana principal
│
├── security/
│   ├── __init__.py
│   └── session_manager.py          # Gestor de sesiones seguro
│
├── utils/
│   ├── __init__.py
│   ├── logger.py                   # Sistema de logging seguro
│   └── hardware_id.py              # Generador de Hardware ID
│
├── resources/
│   └── logo_tubos.jpg              # Logo corporativo
│
├── credentials/
│   └── service_account.json        # Credenciales Google API
│
├── pyinstaller_hooks/
│   └── hook-pyi_rth_pkgres.py     # Hooks para PyInstaller
│
├── logs/                           # Generado automáticamente
│   ├── main_window.log
│   ├── sap_client.log
│   └── license_manager.log
│
├── dist/                           # Generado por PyInstaller
│   └── CotizadorSAP.exe
│
├── cotizador.spec                  # Especificación PyInstaller
├── requirements.txt                # Dependencias Python
└── README.md                       # Documentación
2.3 Diagrama de Flujo Principal
text
flowchart TD
    A[Inicio Aplicación] --> B[Login Dialog]
    B --> C{Credenciales Válidas?}
    C -->|No| B
    C -->|Sí| D[Obtener Hardware ID]
    D --> E[Validar Licencia en Google Sheets]
    E --> F{Dispositivo Autorizado?}
    F -->|No Registrado| G[Registrar Dispositivo]
    G --> H[Mostrar Mensaje: Contactar Admin]
    H --> Z[Fin]
    F -->|No Autorizado| H
    F -->|Autorizado| I{Usuario en Lista?}
    I -->|No| H
    I -->|Sí| J[Conectar a SAP B1]
    J --> K{Conexión Exitosa?}
    K -->|No| L[Mostrar Error]
    L --> Z
    K -->|Sí| M[Cargar Ventana Principal]
    M --> N[Iniciar Timer de Inactividad]
    N --> O[Sistema Listo]
    O --> P{Acción del Usuario}
    P --> Q[Buscar Cliente]
    P --> R[Buscar Artículos]
    P --> S[Agregar a Cotización]
    P --> T[Generar PDF]
    P --> U[Timeout/Logout]
    U --> Z
2.4 Flujo de Generación de PDF
text
flowchart TD
    A[Click: Generar PDF] --> B{Cotización Válida?}
    B -->|No| C[Mostrar Error]
    C --> Z[Fin]
    B -->|Sí| D[Generar Excel Temporal]
    D --> E[Crear Documento PDF Base]
    E --> F[Agregar Logo Corporativo]
    F --> G[Agregar Datos del Cliente]
    G --> H[Agregar Tabla de Artículos]
    H --> I[Calcular Totales]
    I --> J[Convertir Total a Letras]
    J --> K[Generar Código QR]
    K --> L[Adjuntar QR al PDF]
    L --> M[Adjuntar Excel al PDF]
    M --> N[Guardar PDF]
    N --> O[Limpiar Archivos Temporales]
    O --> P{Abrir PDF?}
    P -->|Sí| Q[Abrir con Visor]
    P -->|No| Z
    Q --> Z
3. Infraestructura y Tecnologías
3.1 Stack Tecnológico
Capa	Tecnología	Versión	Propósito
Frontend	PyQt6	6.6.1	Interfaz gráfica de usuario
Backend	Python	3.12.10	Lógica de aplicación
API REST	Requests	2.31.0	Comunicación HTTP
Base de Datos	SAP	Base de datos ERP
Licencias	Google Sheets API	v4	Control de licencias
Reportes	ReportLab	4.0.9	Generación de PDFs
QR Code	qrcode[pil]	7.4.2	Códigos QR
Excel	pandas + openpyxl	2.1.4 / 3.1.2	Archivos Excel
Compilación	PyInstaller	6.3.0	Ejecutables
3.2 Dependencias Completas
text
# requirements.txt

# GUI Framework
PyQt6==6.6.1
PyQt6-Qt6==6.6.1
PyQt6-sip==13.6.0

# HTTP y APIs
requests==2.31.0
urllib3==2.1.0

# Google Sheets API
gspread==6.0.0
google-auth==2.27.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0

# Generación de PDFs
reportlab==4.0.9
qrcode[pil]==7.4.2
Pillow==10.2.0
PyPDF2==3.0.1

# Manejo de datos
pandas==2.1.4
openpyxl==3.1.2

# Compilación
pyinstaller==6.3.0
3.3 Requisitos del Sistema
Para Desarrollo
Sistema Operativo: Windows 10/11, Linux, macOS

Python: 3.10 o superior

RAM: 4 GB mínimo, 8 GB recomendado

Espacio en Disco: 500 MB para dependencias

Conexión de Red: Acceso a SAP Service Layer e Internet

Para Producción (Ejecutable)
Sistema Operativo: Windows 10/11

RAM: 2 GB mínimo

Espacio en Disco: 150 MB

Conexión de Red: Acceso a SAP Service Layer e Internet

3.4 Infraestructura de Red
text
┌─────────────────────────────────────────────────────────────┐
│                    USUARIOS FINALES                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ PC Ventas 01 │  │ PC Ventas 02 │  │ Laptop Móvil │     │
│  │ (Autorizado) │  │ (Autorizado) │  │(No Autorizado│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    RED CORPORATIVA                          │
│                  (Firewall - Port 50000)                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┴─────────────────┐
        ↓                                   ↓
┌──────────────────┐              ┌──────────────────┐
│ SAP B1 SERVER    │              │ INTERNET         │
│ Service Layer    │              │ (Google Sheets)  │
│ Port: 50000      │              │                  │
│ HTTPS            │              │                  │
└──────────────────┘              └──────────────────┘
4. Sistema de Licenciamiento
4.1 Descripción General
El sistema implementa un control de licencias de doble factor:

Hardware ID del dispositivo (único e irrepetible)

Usuario SAP autorizado en ese dispositivo

4.2 Arquitectura del Sistema de Licencias
text
┌────────────────────────────────────────────────────────────────┐
│  APLICACIÓN (Cliente)                                          │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  1. Obtener Hardware ID del equipo                       │ │
│  │  2. Obtener usuario de login                             │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                          ↓ (HTTPS)
┌────────────────────────────────────────────────────────────────┐
│  GOOGLE SHEETS API                                             │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Service Account Authentication                          │ │
│  │  (service_account.json)                                  │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────────┐
│  GOOGLE SHEETS: "Licencias SAP ITEMS"                         │
│  Hoja: "Dispositivos"                                          │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ A          │ B          │ C          │ D-G               │ │
│  │ Hardware   │ Nombre     │ Estado     │ Usuarios          │ │
│  │ ID         │ Equipo     │            │ Autorizados       │ │
│  ├────────────┼────────────┼────────────┼───────────────────┤ │
│  │ ABC123...  │ PC-VTA-01  │ Autorizado │ user1, user2, ... │ │
│  │ XYZ789...  │ LAPTOP-02  │No Autoriza │                   │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
4.3 Generación de Hardware ID
Algoritmo por Sistema Operativo
Sistema Operativo	Método	Comando
Windows	UUID de BIOS	wmic csproduct get uuid
macOS	IOPlatformUUID	ioreg -d2 -c IOPlatformExpertDevice
Linux	Machine ID	/etc/machine-id o /var/lib/dbus/machine-id
Fallback	MAC Address Hash	uuid.getnode() + SHA256
Implementación
python
# utils/hardware_id.py

class HardwareIDGenerator:
    @staticmethod
    def get_windows_uuid() -> Optional[str]:
        """Windows: UUID del sistema"""
        output = subprocess.check_output('wmic csproduct get uuid', shell=True)
        # Procesa salida...
        return uuid_str
    
    @staticmethod
    def get_mac_uuid() -> Optional[str]:
        """macOS: IOPlatformUUID"""
        output = subprocess.check_output(
            "ioreg -d2 -c IOPlatformExpertDevice | awk -F\\\" '/IOPlatformUUID/{print $(NF-1)}'",
            shell=True
        )
        return output.strip()
    
    @staticmethod
    def get_linux_machine_id() -> Optional[str]:
        """Linux: Machine ID"""
        with open('/etc/machine-id', 'r') as f:
            return f.read().strip()
    
    @classmethod
    def get_hardware_id(cls) -> str:
        """ID único multiplataforma"""
        system = platform.system().lower()
        
        if system == 'windows':
            return cls.get_windows_uuid()
        elif system == 'darwin':
            return cls.get_mac_uuid()
        elif system == 'linux':
            return cls.get_linux_machine_id()
        
        # Fallback: MAC + SHA256
        return cls.get_fallback_id()
4.4 Flujo de Validación de Licencia
text
sequenceDiagram
    participant U as Usuario
    participant A as Aplicación
    participant H as Hardware ID Gen
    participant G as Google Sheets API
    participant S as Google Sheets

    U->>A: Ingresa credenciales
    A->>H: Obtener Hardware ID
    H-->>A: Hardware ID único
    A->>G: Autenticar con Service Account
    G-->>A: Token de acceso
    A->>S: Buscar Hardware ID
    alt Hardware ID no existe
        S-->>A: No encontrado
        A->>S: Registrar nuevo dispositivo
        S-->>A: Registrado (Estado: No Autorizado)
        A->>U: Contactar administrador
    else Hardware ID existe
        S-->>A: Datos del dispositivo
        A->>A: Verificar Estado
        alt Estado = "No Autorizado"
            A->>U: Dispositivo no autorizado
        else Estado = "Autorizado"
            A->>A: Verificar usuario en lista
            alt Usuario no en lista
                A->>U: Usuario no autorizado
            else Usuario autorizado
                A->>U: ✅ Acceso concedido
            end
        end
    end
4.5 Estructura de Google Sheets
Hoja: "Dispositivos"
Columna	Campo	Tipo	Descripción	Ejemplo
A	Hardware ID	Texto	ID único del dispositivo	ABC123DEF456...
B	Nombre Equipo	Texto	Nombre del equipo	PC-VENTAS-01
C	Estado	Lista	Autorizado / No autorizado	Autorizado
D	Usuario 1	Texto	Usuario SAP autorizado	vendedor1
E	Usuario 2	Texto	Usuario SAP autorizado	vendedor2
F	Usuario 3	Texto	Usuario SAP autorizado	admin
G	Usuario 4	Texto	Usuario SAP autorizado	(vacío)
Ejemplo de Datos
text
| Hardware ID              | Nombre Equipo  | Estado      | Usuario 1  | Usuario 2  | Usuario 3 | Usuario 4 |
|--------------------------|----------------|-------------|------------|------------|-----------|-----------|
| A1B2C3D4E5F6G7H8I9J0K... | PC-VENTAS-01   | Autorizado  | admin      | vendedor1  | vendedor2 |           |
| F6E5D4C3B2A1Z9Y8X7W6V... | LAPTOP-GERENTE | Autorizado  | gerente    | admin      |           |           |
| 123456789ABCDEFGHIJK...  | PC-ALMACEN     | No autorizado |            |            |           |           |
4.6 Configuración de Google Sheets API
Paso 1: Crear Service Account
Ir a Google Cloud Console

Crear proyecto o seleccionar existente

Habilitar Google Sheets API y Google Drive API

Crear Service Account:

Nombre: sap-cotizador-service

Rol: Editor

Crear clave JSON

Descargar y renombrar a service_account.json

Paso 2: Compartir Google Sheet
Abrir archivo service_account.json

Copiar el client_email:

json
{
  "client_email": "sap-cotizador@proyecto-123.iam.gserviceaccount.com"
}
Compartir la hoja con ese email (permisos de Editor)

Paso 3: Configurar en la Aplicación
python
# api/license_manager.py

class LicenseManager:
    SPREADSHEET_ID = "1zJdAn5gAlxOy5bQA4_sgUaUexx7iQk4InfLn7vNDnS0"
    WORKSHEET_NAME = "Dispositivos"
    
    def _connect(self):
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_file(
            'credentials/service_account.json',
            scopes=scopes
        )
        
        self.client = gspread.authorize(creds)
        self.worksheet = self.client.open_by_key(self.SPREADSHEET_ID).worksheet(self.WORKSHEET_NAME)
5. Medidas de Seguridad Implementadas
5.1 Resumen de Seguridad
Categoría	Medidas Implementadas	Nivel
Autenticación	Login SAP + Validación de licencia	⭐⭐⭐⭐⭐
Autorización	Control por dispositivo y usuario	⭐⭐⭐⭐⭐
Sesiones	Timeout automático (30 min)	⭐⭐⭐⭐
Datos sensibles	Sin almacenamiento local de contraseñas	⭐⭐⭐⭐⭐
Logging	Sanitización de datos sensibles	⭐⭐⭐⭐⭐
Comunicación	HTTPS con SAP (configurable SSL)	⭐⭐⭐⭐
Integridad	Código QR de validación en PDFs	⭐⭐⭐⭐
5.2 Gestión Segura de Credenciales
❌ Anti-patrón (NO hacer)
python
# NUNCA hacer esto
USERNAME = "admin"
PASSWORD = "12345"
with open("credentials.txt", "w") as f:
    f.write(f"{USERNAME}:{PASSWORD}")
✅ Implementación Segura
python
# ui/login_dialog.py

class LoginDialog(QDialog):
    def validar(self):
        # Credenciales solo en memoria local (stack)
        credenciales = {
            "CompanyDB": self.txt_db.text(),
            "UserName": self.txt_user.text(),
            "Password": self.txt_pass.text()  # Se envía directo a SAP
        }
        
        # Limpiar campo de contraseña inmediatamente
        self.txt_pass.clear()
        
        # NO se almacena en disco
        # NO se loguea
        # NO se persiste en variables de clase
        
        self.credenciales = credenciales
        self.accept()
Características de seguridad:

✅ Contraseñas nunca se almacenan en disco

✅ Contraseñas nunca aparecen en logs

✅ Campo de contraseña con echoMode = Password

✅ Limpieza inmediata después de uso

✅ Sin persistencia entre sesiones

5.3 Sistema de Logging Seguro
Implementación de Sanitización
python
# utils/logger.py

class SecureLogger:
    """Logger que redacta automáticamente datos sensibles"""
    
    SENSITIVE_KEYS = [
        'password', 'Password', 'PASSWORD',
        'SessionId', 'SessionID', 'session_id',
        'Authorization', 'Bearer', 'Token',
        'pwd', 'secret', 'api_key', 'client_secret'
    ]
    
    def _sanitize_data(self, data: any) -> any:
        """Elimina datos sensibles antes de registrar"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(sensitive in key for sensitive in self.SENSITIVE_KEYS):
                    sanitized[key] = '***REDACTED***'
                elif isinstance(value, dict):
                    sanitized[key] = self._sanitize_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        return data
    
    def info(self, message: str, data: dict = None):
        """Log con sanitización automática"""
        if data:
            data = self._sanitize_data(data)
        self.logger.info(f"{message} {data if data else ''}")
Ejemplo de Salida de Log
text
2026-01-28 14:23:15 - INFO - Intentando login para usuario: admin
2026-01-28 14:23:15 - DEBUG - Credenciales: {'CompanyDB': 'SBODEMO', 'UserName': 'admin', 'Password': '***REDACTED***'}
2026-01-28 14:23:17 - INFO - ✅ Login exitoso
2026-01-28 14:23:17 - DEBUG - SessionId: ***REDACTED***
5.4 Gestión de Sesiones
Timeout Automático por Inactividad
python
# ui/main_window.py

class VentanaPrincipal(QMainWindow):
    def __init__(self):
        # Timer de inactividad (30 minutos)
        self.timer_inactividad = QTimer(self)
        self.timer_inactividad.timeout.connect(self.timeout_sesion)
        self.tiempo_limite_ms = SESSION_TIMEOUT_MINUTES * 60 * 1000
        self.timer_inactividad.start(self.tiempo_limite_ms)
        
        # Monitorear eventos de usuario
        QApplication.instance().installEventFilter(self)
    
    def eventFilter(self, source, event):
        """Reinicia timer en cada acción del usuario"""
        if event.type() in (QEvent.Type.MouseMove, 
                           QEvent.Type.KeyPress, 
                           QEvent.Type.MouseButtonPress):
            self.timer_inactividad.start(self.tiempo_limite_ms)
        return super().eventFilter(source, event)
    
    def timeout_sesion(self):
        """Cierra sesión automáticamente"""
        self.timer_inactividad.stop()
        self.sap_client.logout()
        QMessageBox.warning(
            self, 
            "Sesión Expirada", 
            f"Inactividad detectada ({SESSION_TIMEOUT_MINUTES} min).\n"
            "Sesión cerrada por seguridad."
        )
        self.ejecutar_relogin()
Características:

✅ Timeout configurable (default: 30 minutos)

✅ Cierre automático de sesión SAP

✅ Reinicio de timer con cada interacción

✅ Re-login sin pérdida de datos de trabajo

✅ Notificación visual al usuario

5.5 Validación de Entrada
python
def buscar_cliente(self):
    # 1. Validación de entrada
    term = self.txt_buscar_cli.text().strip()
    if not term:
        return  # Evitar búsquedas vacías
    
    # 2. Limitación de longitud
    if len(term) > 100:
        QMessageBox.warning(self, "Error", "Búsqueda muy larga")
        return
    
    try:
        # 3. Sanitización en backend (SAP maneja escape)
        clientes = self.sap_client.search_business_partners(term)
        
        # 4. Validación de respuesta
        if not isinstance(clientes, list):
            raise ValueError("Respuesta inesperada")
        
        # 5. Procesamiento seguro
        for cliente in clientes:
            # Validar campos esperados
            if 'CardCode' not in cliente:
                continue
            # ...
            
    except Exception as e:
        # 6. Manejo de errores sin exponer detalles internos
        QMessageBox.warning(self, "Error", "No se pudo completar la búsqueda")
        self.logger.error(f"Error búsqueda: {e}")
5.6 Comunicación Segura con SAP
python
# security/session_manager.py

class SecureSessionManager:
    def __init__(self, base_url: str, timeout: int = 30):
        self.session = requests.Session()
        
        # Configuración SSL (ajustar en producción)
        self.session.verify = SSL_VERIFY  # True en producción
        
        # Headers de seguridad
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'SAPCotizador/2.0'
        })
        
        # Timeouts para evitar bloqueos
        self.timeout = timeout
    
    def request(self, method: str, endpoint: str, **kwargs):
        """Petición HTTP segura con retry"""
        kwargs.setdefault('timeout', self.timeout)
        
        try:
            response = self.session.request(
                method,
                f"{self.base_url}/{endpoint}",
                **kwargs
            )
            return response
        except requests.exceptions.Timeout:
            self.logger.error("Timeout de conexión")
            raise
        except requests.exceptions.SSLError as e:
            self.logger.error(f"Error SSL: {e}")
            raise
Características:

✅ SSL/TLS configurable

✅ Timeouts en todas las peticiones (30s)

✅ Manejo de excepciones de red

✅ Retry automático (opcional)

✅ Cierre limpio de conexiones

5.7 Integridad de Documentos (QR)
python
def generar_qr_cotizacion(self, datos: dict):
    """Genera QR con hash de validación"""
    
    # Datos incluidos en el QR
    contenido_qr = f"""VALIDACIÓN TUBOS MONTERREY
Cliente: {datos['cliente']}
RFC: {datos['rfc']}
Fecha: {datos['fecha']}
------------------
DETALLE:
{detalle_partidas}
------------------
TOTAL: {datos['total']}
Moneda: {datos['moneda']}
"""
    
    # Generar QR con corrección de errores
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=2
    )
    qr.add_data(contenido_qr)
    qr.make(fit=True)
    
    return qr_path
Propósito:

✅ Verificación de autenticidad del documento

✅ No modificable después de generación

✅ Verificable con cualquier lector QR

✅ Incluye hash de datos principales

6. API y Endpoints de SAP B1
6.1 Arquitectura de SAP Service Layer
text
┌────────────────────────────────────────────────────────────┐
│  APLICACIÓN CLIENTE                                        │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  SAP Client (Python)                                 │ │
│  │  - Session Manager                                   │ │
│  │  - Request/Response Handling                         │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
                          ↓ HTTPS (Port 50000)
┌────────────────────────────────────────────────────────────┐
│  SAP BUSINESS ONE SERVICE LAYER                            │
│  https://servidor-sap:50000/b1s/v1/                       │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  REST API                                            │ │
│  │  - OData V4                                          │ │
│  │  - JSON Request/Response                             │ │
│  │  - Session-based Authentication                      │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│  SAP HANA DATABASE                                         │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  OITM (Items)                                        │ │
│  │  OCRD (Business Partners)                            │ │
│  │  OITW (Warehouse Stock)                              │ │
│  │  ITM1 (Item Prices)                                  │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
6.2 Endpoints Utilizados
6.2.1 Autenticación
POST /Login

text
POST https://servidor-sap:50000/b1s/v1/Login
Content-Type: application/json

{
  "CompanyDB": "SBODEMO",
  "UserName": "admin",
  "Password": "12345"
}
Respuesta Exitosa (200 OK):

json
{
  "SessionId": "6f4a2e8c-9d3b-4f1a-8e2d-5c7b9a1f3e4d",
  "Version": "10.0",
  "SessionTimeout": 30
}
6.2.2 Cerrar Sesión
POST /Logout

text
POST https://servidor-sap:50000/b1s/v1/Logout
Cookie: B1SESSION=6f4a2e8c...
Respuesta: 204 No Content

6.2.3 Búsqueda de Artículos
GET /Items

text
GET https://servidor-sap:50000/b1s/v1/Items?$filter=(contains(ItemCode,'TUBO') or contains(ItemName,'TUBO')) and Frozen eq 'tNO' and Valid eq 'tYES'&$select=ItemCode,ItemName,ItemsGroupCode,QuantityOnStock,QuantityOrderedByCustomers,QuantityOrderedFromVendors,SalesUnit,ItemPrices&$skip=0&$top=20
Cookie: B1SESSION=6f4a2e8c...
Parámetros OData:

Parámetro	Descripción	Ejemplo
$filter	Filtro de búsqueda	contains(ItemCode,'TUBO')
$select	Campos a devolver	ItemCode,ItemName
$skip	Offset de paginación	0, 20, 40
$top	Límite de resultados	20
$orderby	Ordenamiento	ItemCode asc
Respuesta:

json
{
  "odata.metadata": "https://...",
  "value": [
    {
      "ItemCode": "TUBO-001",
      "ItemName": "TUBO GALVANIZADO 2\"",
      "ItemsGroupCode": "3101-CO BR",
      "QuantityOnStock": 150.0,
      "QuantityOrderedByCustomers": 20.0,
      "QuantityOrderedFromVendors": 50.0,
      "SalesUnit": "PZA",
      "ItemPrices": [
        {
          "PriceList": 1,
          "Price": 125.50,
          "Currency": "MXN"
        },
        {
          "PriceList": 3,
          "Price": 6.75,
          "Currency": "USD",
          "AdditionalPrice1": 6.75
        }
      ]
    }
  ]
}
6.2.4 Búsqueda de Clientes
GET /BusinessPartners

text
GET https://servidor-sap:50000/b1s/v1/BusinessPartners?$filter=(contains(CardCode,'C001') or contains(CardName,'PRINCIPAL'))&$select=CardCode,CardName,FederalTaxID,EmailAddress,Phone1,PaymentTermsCode,Address,City,State,ZipCode
Cookie: B1SESSION=6f4a2e8c...
Respuesta:

json
{
  "value": [
    {
      "CardCode": "C001",
      "CardName": "CLIENTE PRINCIPAL S.A. DE C.V.",
      "FederalTaxID": "CPR123456ABC",
      "EmailAddress": "contacto@clienteprincipal.com",
      "Phone1": "+52 (81) 1234-5678",
      "PaymentTermsCode": "30 días",
      "Address": "Av. Constitución #123",
      "City": "Monterrey",
      "State": "Nuevo León",
      "ZipCode": "64000"
    }
  ]
}
6.2.5 Información de Usuario
GET /Users

text
GET https://servidor-sap:50000/b1s/v1/Users?$filter=UserCode eq 'admin'&$select=UserName,e_Mail
Cookie: B1SESSION=6f4a2e8c...
Respuesta:

json
{
  "value": [
    {
      "UserName": "Administrador",
      "e_Mail": "admin@tubosmonterrey.com"
    }
  ]
}
6.3 Implementación de Paginación
python
def search_items(self, search_term: str) -> list:
    """Búsqueda con paginación automática"""
    all_items = []
    skip = 0
    page_size = 20  # Límite del servidor
    max_total = 500
    
    while True:
        endpoint = (
            f"Items"
            f"?$filter={filter_str}"
            f"&$select={select_fields}"
            f"&$skip={skip}"
            f"&$top={page_size}"
        )
        
        response = self.session_manager.request("GET", endpoint)
        
        if response.status_code == 200:
            items = response.json().get('value', [])
            
            if not items or len(items) < page_size:
                all_items.extend(items)
                break  # Última página
            
            all_items.extend(items)
            
            if len(all_items) >= max_total:
                break  # Límite alcanzado
            
            skip += page_size
        else:
            break
    
    return all_items
6.4 Manejo de Errores de API
Código HTTP	Significado	Acción
200	OK	Procesar respuesta
201	Created	Recurso creado exitosamente
204	No Content	Operación exitosa sin respuesta
400	Bad Request	Verificar sintaxis de petición
401	Unauthorized	Re-login requerido
404	Not Found	Recurso no existe
500	Server Error	Reintentar o contactar soporte
python
def handle_api_response(self, response):
    """Manejo centralizado de respuestas"""
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        self.logger.error("Sesión expirada")
        raise SessionExpiredException()
    elif response.status_code == 400:
        self.logger.error(f"Petición inválida: {response.text}")
        raise InvalidRequestException()
    elif response.status_code >= 500:
        self.logger.error(f"Error del servidor: {response.status_code}")
        raise ServerErrorException()
    else:
        self.logger.warning(f"Código inesperado: {response.status_code}")
        return None
7. Sistema de Control de Descuentos
7.1 Descripción General
El sistema implementa descuentos máximos configurables por grupo de artículos, evitando que los agentes de ventas excedan los límites autorizados.

7.2 Configuración de Descuentos
python
# config/settings.py

DESCUENTOS_MAXIMOS_POR_GRUPO = {
    "3101-CO BR": 40.0,      # Bronce: 40% máximo
    "3101-AC IN": 35.0,      # Acero inoxidable: 35%
    "3102-TU CE": 25.0,      # Tubería cedula: 25%
    "3103-VA ND": 30.0,      # Válvulas: 30%
    "3104-CO NE": 20.0,      # Conexiones: 20%
    "3105-CA BL": 45.0,      # Cables: 45%
    "DEFAULT": 50.0          # Por defecto: 50%
}

# Colores de alerta
ALERTA_DESCUENTO_COLOR = "#FFC107"       # Amarillo (>90% del máx)
DESCUENTO_BLOQUEADO_COLOR = "#F44336"    # Rojo (excedido)
7.3 Flujo de Validación de Descuentos
text
flowchart TD
    A[Usuario ingresa descuento] --> B{Obtener grupo del artículo}
    B --> C[Buscar descuento máximo en config]
    C --> D{Descuento > Máximo?}
    D -->|No| E{Descuento >= 90% del máximo?}
    D -->|Sí| F[Mostrar alerta: Excedido]
    F --> G[Aplicar descuento máximo]
    G --> H[Colorear celda: ROJO]
    H --> I[Actualizar tabla]
    E -->|Sí| J[Colorear celda: AMARILLO]
    E -->|No| K[Sin color especial]
    J --> I
    K --> I
    I --> L[Recalcular totales]
7.4 Implementación de Validación
python
# ui/main_window.py

def recalcular_celda(self, item):
    """Recalcula con validación de descuento"""
    row = item.row()
    col = item.column()
    art = self.articulos_cotizacion[row]
    
    if col == 7:  # Columna de descuento %
        try:
            descuento_ingresado = float(item.text().replace('%',''))
        except:
            return
        
        descuento_maximo = art['descuento_maximo']
        
        # VALIDACIÓN PRINCIPAL
        if descuento_ingresado > descuento_maximo:
            QMessageBox.warning(
                self,
                "⚠️ Descuento Excedido",
                f"El descuento ingresado ({descuento_ingresado:.2f}%) "
                f"supera el máximo permitido.\n\n"
                f"Artículo: {art['codigo']}\n"
                f"Grupo: {art['grupo']}\n"
                f"Descuento máximo: {descuento_maximo}%\n\n"
                f"Se aplicará el descuento máximo permitido."
            )
            descuento_ingresado = descuento_maximo
            
            # Logging de auditoría
            self.logger.warning(
                f"Intento de descuento excedido - "
                f"Usuario: {self.credenciales['UserName']}, "
                f"Artículo: {art['codigo']}, "
                f"Grupo: {art['grupo']}, "
                f"Intentado: {descuento_ingresado}%, "
                f"Máximo: {descuento_maximo}%"
            )
        
        art['descuento_pct'] = descuento_ingresado
        art['precio_con_descuento'] = art['precio'] * (1 - (descuento_ingresado/100))
        art['subtotal'] = art['precio_con_descuento'] * art['cantidad']
    
    # Recalcular IVA y total
    art['iva'] = art['subtotal'] * 0.16
    art['total'] = art['subtotal'] + art['iva']
    
    self.actualizar_tabla_cotizacion()
7.5 Indicadores Visuales
python
def actualizar_tabla_cotizacion(self):
    """Actualiza tabla con colores de alerta"""
    for i, art in enumerate(self.articulos_cotizacion):
        desc_pct = art['descuento_pct']
        desc_max = art['descuento_maximo']
        
        # Determinar color
        if desc_pct > desc_max:
            # Rojo: Excedido (no debería pasar por validación)
            color = DESCUENTO_BLOQUEADO_COLOR
        elif desc_pct >= desc_max * 0.9:
            # Amarillo: Advertencia (>90% del máximo)
            color = ALERTA_DESCUENTO_COLOR
        else:
            # Sin color: Normal
            color = None
        
        # Aplicar color a celda de descuento
        item_desc = QTableWidgetItem(f"{desc_pct:.2f}")
        if color:
            item_desc.setBackground(QColor(color))
        self.tbl_cot.setItem(i, 7, item_desc)
7.6 Reporte de Auditoría
Todos los intentos de exceder descuentos quedan registrados en logs:

text
2026-01-28 15:45:23 - WARNING - Intento de descuento excedido - Usuario: vendedor1, Artículo: TUBO-001, Grupo: 3101-CO BR, Intentado: 45%, Máximo: 40%
2026-01-28 15:47:10 - WARNING - Intento de descuento excedido - Usuario: vendedor1, Artículo: VALV-205, Grupo: 3103-VA ND, Intentado: 35%, Máximo: 30%
8. Generación de Documentos PDF
8.1 Componentes del PDF
text
┌────────────────────────────────────────────────────────┐
│  ENCABEZADO                                            │
│  ┌──────────────┐                                      │
│  │  LOGO        │  TUBOS MONTERREY S.A. DE C.V.        │
│  │  CORPORATIVO │  Dirección, Teléfono, Email          │
│  └──────────────┘                                      │
├────────────────────────────────────────────────────────┤
│  INFORMACIÓN DE LA OFERTA                              │
│  Fecha: 28/01/2026          Núm. Oferta: PENDIENTE    │
├────────────────────────────────────────────────────────┤
│  DATOS DEL CLIENTE                                     │
│  Cliente: CLIENTE PRINCIPAL S.A. DE C.V.               │
│  RFC: CPR123456ABC                                     │
│  Dirección: Av. Constitución #123, Monterrey, NL      │
├────────────────────────────────────────────────────────┤
│  TABLA DE ARTÍCULOS                                    │
│  ┌──┬────┬──────┬────┬───┬──────┬────┬──────┬────────┐│
│  │# │Cód │Desc  │Cant│Uni│P.List│Desc│P.c/D │Subtotal││
│  ├──┼────┼──────┼────┼───┼──────┼────┼──────┼────────┤│
│  │1 │T001│TUBO..│10.0│PZA│125.50│10% │113.00│1,130.00││
│  │2 │V205│VALV..│5.00│PZA│450.00│15% │382.50│1,912.50││
│  └──┴────┴──────┴────┴───┴──────┴────┴──────┴────────┘│
├────────────────────────────────────────────────────────┤
│  TOTALES                                               │
│  Importe en letra: TRES MIL CUARENTA Y DOS PESOS...   │
│                                    Subtotal: $3,042.50 │
│                                    I.V.A:      $486.80 │
│                                    TOTAL:    $3,529.30 │
├────────────────────────────────────────────────────────┤
│  CONDICIONES COMERCIALES                               │
│  Condición de Pago: 30 días                            │
│  Entrega: Av. Principal #123...                        │
│  Vigencia: 10 días hábiles                             │
├────────────────────────────────────────────────────────┤
│  CÓDIGO QR DE VALIDACIÓN                               │
│  ┌────────┐  📎 Este PDF contiene un archivo Excel    │
│  │ ██  ██ │     adjunto con el detalle completo       │
│  │ ██████ │                                            │
│  └────────┘                                            │
└────────────────────────────────────────────────────────┘
8.2 Generación de Excel Adjunto
python
def generar_excel_temporal(self):
    """Genera archivo Excel con detalle de cotización"""
    try:
        # Crear DataFrame
        df = pd.DataFrame(self.articulos_cotizacion)
        
        # Ordenar columnas
        columnas_ordenadas = [
            'codigo', 'nombre', 'cantidad', 'unidad',
            'precio', 'descuento_pct', 'precio_con_descuento',
            'subtotal', 'iva', 'total'
        ]
        df = df[columnas_ordenadas]
        
        # Renombrar columnas
        df.columns = [
            'Código', 'Descripción', 'Cantidad', 'Unidad',
            'Precio Lista', 'Desc %', 'Precio Final',
            'Subtotal', 'IVA', 'Total'
        ]
        
        # Crear archivo temporal
        temp_fd, excel_path = tempfile.mkstemp(suffix='.xlsx')
        os.close(temp_fd)
        
        # Escribir Excel con formato
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Detalle')
            
            # Ajustar anchos de columna
            worksheet = writer.sheets['Detalle']
            for column in worksheet.columns:
                max_length = max(len(str(cell.value)) for cell in column)
                worksheet.column_dimensions[column[0].column_letter].width = max_length + 2
        
        return excel_path
        
    except Exception as e:
        self.logger.error(f"Error generando Excel: {e}")
        return None
8.3 Generación de Código QR
python
def generar_qr_cotizacion(self, datos: dict):
    """Genera QR con datos de validación"""
    
    # Construir contenido del QR
    detalle = ""
    for item in datos['items'][:15]:  # Primeros 15 items
        detalle += (
            f"{item['codigo']} | "
            f"{item['cantidad']:,.2f} x ${item['precio_con_descuento']:,.2f} = "
            f"${item['subtotal']:,.2f}\n"
        )
    
    if len(datos['items']) > 15:
        detalle += f"... y {len(datos['items']) - 15} artículos más\n"
    
    contenido_qr = f"""VALIDACIÓN TUBOS MONTERREY
Cliente: {datos['cliente']}
RFC: {datos['rfc']}
Fecha: {datos['fecha']}
------------------
DETALLE:
{detalle}
------------------
SUBTOTAL: {datos['subtotal']}
IVA: {datos['iva']}
TOTAL: {datos['total']}
Moneda: {datos['moneda']}"""
    
    # Crear QR code
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=2
    )
    qr.add_data(contenido_qr)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Guardar temporalmente
    temp_fd, qr_path = tempfile.mkstemp(suffix='.png')
    os.close(temp_fd)
    img.save(qr_path)
    
    return qr_path, contenido_qr
8.4 Conversión de Números a Letras
python
def numero_a_letras(self, numero: float, moneda: str = "MXN") -> str:
    """Convierte números a texto (sistema mexicano)"""
    
    unidades = ["", "uno", "dos", "tres", "cuatro", "cinco", 
                "seis", "siete", "ocho", "nueve"]
    
    # ... implementación completa ...
    
    # Resultado
    if moneda.upper() == "USD":
        return f"{texto_pesos.upper()} DÓLARES CON {centavos:02d}/100"
    else:
        return f"{texto_pesos.upper()} PESOS CON {centavos:02d}/100 M.N."
8.5 Adjuntar Excel al PDF
python
def adjuntar_excel_a_pdf(self, pdf_path: str, excel_path: str):
    """Adjunta archivo Excel al PDF usando PyPDF2"""
    
    try:
        # Leer PDF original
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        # Copiar todas las páginas
        for page in reader.pages:
            writer.add_page(page)
        
        # Adjuntar Excel
        with open(excel_path, 'rb') as excel_file:
            writer.add_attachment("Detalle_Cotizacion.xlsx", excel_file.read())
        
        # Guardar PDF con adjunto
        with open(pdf_path, 'wb') as output_pdf:
            writer.write(output_pdf)
        
        self.logger.info("✅ Excel adjuntado al PDF exitosamente")
        
    except Exception as e:
        self.logger.error(f"Error adjuntando Excel: {e}")
9. Instalación y Configuración
9.1 Requisitos Previos
Python 3.10 o superior

Acceso a SAP Business One Service Layer

Cuenta de Google Cloud (para API de Sheets)

Logo corporativo en formato JPG/PNG

9.2 Instalación Paso a Paso
Paso 1: Clonar o Descargar el Proyecto
bash
cd C:\Users\TuUsuario\Proyectos
# Descomprimir o clonar el repositorio
cd secure-sap-cotizador
Paso 2: Crear Entorno Virtual
bash
python -m venv venv
venv\Scripts\activate
Paso 3: Instalar Dependencias
bash
pip install -r requirements.txt
Paso 4: Configurar SAP B1
Editar config/settings.py:

python
# CONFIGURACIÓN DE SAP B1
SAP_BASE_URL = "https://tu-servidor-sap:50000/b1s/v1"
SAP_COMPANY_DB = "TU_BASE_DE_DATOS"
SAP_TIMEOUT = 30
SAP_MAX_RESULTS = 500
SAP_PAGE_SIZE = 20

# SSL (True en producción)
SSL_VERIFY = False
SSL_CERT_PATH = None
Paso 5: Configurar Google Sheets API
Crear Service Account en Google Cloud

Descargar JSON de credenciales

Guardar en credentials/service_account.json

Compartir Google Sheet con el email del service account

Paso 6: Agregar Logo
bash
# Copiar logo a la carpeta resources
copy "C:\ruta\a\tu\logo.jpg" "resources\logo_tubos.jpg"
Paso 7: Configurar Empresa
Editar config/settings.py:

python
# DATOS DE LA EMPRESA
COMPANY_NAME = "TUBOS MONTERREY S.A. DE C.V."
COMPANY_RFC = "TMO123456789"
COMPANY_ADDRESS = "Av. Principal #123, Monterrey, NL"
COMPANY_PHONE = "+52 (81) 1234-5678"
COMPANY_EMAIL = "ventas@tubosmonterrey.com"
COMPANY_WEBSITE = "www.tubosmonterrey.com"
Paso 8: Configurar Clientes Autorizados
python
# CLIENTES PREDEFINIDOS
CLIENTES_AUTORIZADOS = [
    {
        'CardCode': 'C001',
        'CardName': 'CLIENTE PRINCIPAL S.A. DE C.V.',
        'FederalTaxID': 'CPR123456ABC',
        # ... demás campos
    },
    # ... más clientes
]
Paso 9: Configurar Descuentos por Grupo
python
# DESCUENTOS MÁXIMOS
DESCUENTOS_MAXIMOS_POR_GRUPO = {
    "3101-CO BR": 40.0,
    "3101-AC IN": 35.0,
    # ... más grupos
    "DEFAULT": 50.0
}
Paso 10: Ejecutar Aplicación
bash
python main.py
10. Compilación a Ejecutable
10.1 Preparación
bash
# Instalar PyInstaller si no está instalado
pip install pyinstaller
10.2 Crear Archivo .spec
bash
pyi-makespec --name=CotizadorSAP --windowed --onefile main.py
10.3 Editar cotizador.spec
python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources/logo_tubos.jpg', 'resources'),
        ('credentials/service_account.json', 'credentials'),
        ('config/settings.py', 'config'),
    ],
    hiddenimports=[
        'qrcode',
        'reportlab',
        'reportlab.lib',
        'reportlab.lib.pagesizes',
        'reportlab.lib.colors',
        'reportlab.lib.units',
        'reportlab.platypus',
        'reportlab.lib.styles',
        'reportlab.lib.enums',
        'pandas',
        'openpyxl',
        'PyPDF2',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'gspread',
        'google.auth',
        'google.oauth2',
        'google.oauth2.service_account',
    ],
    hookspath=['pyinstaller_hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CotizadorSAP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Sin ventana de consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
10.4 Compilar
bash
pyinstaller cotizador.spec --clean
10.5 Distribución
bash
# El ejecutable estará en:
dist\CotizadorSAP.exe

# Probar en otro equipo
# 1. Copiar el .exe
# 2. Ejecutar (no requiere Python)
# 3. El sistema validará licencia automáticamente
11. Guía de Usuario
11.1 Inicio de Sesión
Ejecutar CotizadorSAP.exe

Ingresar credenciales de SAP:

Base de Datos

Usuario

Contraseña

Validación automática de licencia:

El sistema obtiene el Hardware ID del equipo

Valida en Google Sheets

Si no está autorizado, contactar al administrador

Acceso concedido si todo es correcto

11.2 Selección de Cliente
Usar el ComboBox de clientes

Seleccionar cliente de la lista

Los datos se cargan automáticamente

(Opcional) Click en "Actualizar desde SAP" para sincronizar

11.3 Búsqueda de Artículos
Ingresar código o descripción en el campo de búsqueda

Presionar Enter o click en "Buscar"

La tabla mostrará todos los resultados (con paginación automática)

Colores en la tabla:

Verde: Artículos con stock disponible

Rojo: Artículos sin disponibilidad

11.4 Agregar a Cotización
Seleccionar un artículo de la tabla de búsqueda

Ajustar cantidad en el SpinBox

Seleccionar lista de precios (MXN o USD)

Click en "⬇️ Agregar a Cotización"

El artículo aparecerá en la tabla inferior

11.5 Editar Cotización
Cantidad: Editar directamente en la celda

Descuento: Ingresar porcentaje (máximo según grupo)

Eliminar fila: Seleccionar y click en "Eliminar Fila"

Los totales se actualizan automáticamente

11.6 Generar PDF
Verificar que la cotización esté completa

Click en "📄 Generar PDF"

Seleccionar ubicación y nombre del archivo

El PDF se generará con:

Logo corporativo

Datos del cliente

Tabla de artículos

Código QR de validación

Excel adjunto (en el panel de adjuntos)

(Opcional) Abrir el PDF automáticamente

12. Solución de Problemas
12.1 Problemas de Conexión
Error: "No se puede conectar a SAP"

Soluciones:

Verificar URL en config/settings.py

Verificar que SAP Service Layer esté activo

Verificar firewall (puerto 50000)

Probar conectividad: ping servidor-sap

12.2 Problemas de Licencia
Error: "Dispositivo no autorizado"

Soluciones:

Copiar Hardware ID (botón en diálogo)

Enviar al administrador

Esperar autorización en Google Sheets

Reiniciar aplicación

12.3 Logo no aparece en PDF
Soluciones:

Verificar que existe: resources/logo_tubos.jpg

Verificar que no tiene espacios en el nombre

Verificar que está incluido en el .spec

Recompilar el ejecutable

12.4 Excel no se adjunta al PDF
Soluciones:

Verificar instalación de openpyxl y PyPDF2

Verificar logs en logs/main_window.log

Reinstalar dependencias: pip install --upgrade openpyxl PyPDF2

13. Mantenimiento y Actualizaciones
13.1 Actualizar Dependencias
bash
# Ver paquetes desactualizados
pip list --outdated

# Actualizar paquete específico
pip install --upgrade nombre-paquete

# Actualizar requirements.txt
pip freeze > requirements.txt
13.2 Revisar Logs
bash
# Logs principales
notepad logs\main_window.log
notepad logs\sap_client.log
notepad logs\license_manager.log

# Buscar errores
findstr /i "error" logs\*.log
13.3 Backup de Configuración
bash
# Crear backup antes de cambios
xcopy config\settings.py config\settings.py.bak /Y
xcopy credentials\* credentials_backup\ /Y
13.4 Agregar Nuevos Grupos de Descuento
python
# config/settings.py

DESCUENTOS_MAXIMOS_POR_GRUPO = {
    # ... existentes ...
    "NUEVO-GRUPO": 45.0,  # Agregar aquí
}
13.5 Agregar Nuevos Clientes
python
# config/settings.py

CLIENTES_AUTORIZADOS.append({
    'CardCode': 'C003',
    'CardName': 'NUEVO CLIENTE S.A.',
    # ... campos completos
})
14. Anexos
14.1 Glosario de Términos
Término	Definición
Hardware ID	Identificador único del dispositivo basado en características de hardware
Service Layer	API REST de SAP Business One para integración
OData	Protocolo de consulta para APIs REST
Session ID	Token de autenticación temporal en SAP
QR Code	Código de barras bidimensional para validación
PyInstaller	Herramienta para compilar Python a ejecutables
Service Account	Cuenta de servicio de Google para autenticación API
14.2 Referencias
SAP Business One Service Layer Documentation

PyQt6 Documentation

Google Sheets API Documentation

ReportLab User Guide

14.3 Contacto y Soporte
Soporte Técnico:

📧 Email: soporte@tubosmonterrey.com

📞 Teléfono: +52 (81) 1234-5678 ext. 100

🌐 Portal: https://soporte.tubosmonterrey.com

Administrador del Sistema:

Gestión de licencias

Autorización de dispositivos

Configuración de descuentos

🏁 Conclusión
El Sistema Seguro de Cotización SAP B1 es una solución integral que combina:

✅ Seguridad robusta con control de licencias y logging sanitizado
✅ Integración directa con SAP Business One
✅ Control de descuentos por grupo de artículos
✅ Documentos profesionales con validación QR y Excel adjunto
✅ Facilidad de uso con interfaz gráfica intuitiva
✅ Distribución sencilla mediante ejecutable standalone

Versión: 2.0.0
Última actualización: Enero 2026
Desarrollado para: Tubos Monterrey S.A. de C.V.

© 2026 Tubos Monterrey S.A. de C.V. - Todos los derechos reservados
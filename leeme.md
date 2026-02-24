# Cotizador SAP Business One - Versión Segura

## 🔒 Sistema de Seguridad

Esta aplicación usa **configuración encriptada** para proteger información sensible. Ya **NO** usa el archivo `.env.secure`.

### Archivos de Configuración

- **`config.key`**: Clave de encriptación (¡MANTENER SEGURO!)
- **`config.encrypted`**: Configuración encriptada (URL de SAP, credenciales de empresa, etc.)
- **`credentials/service_account.json`**: Credenciales de Google Sheets para validación de licencias

## 📋 Requisitos Previos

```bash
pip install -r requirements.txt
```

### Librerías Principales:
- PyQt6
- requests
- cryptography
- gspread
- google-auth
- reportlab
- PyPDF2
- pandas
- openpyxl
- qrcode
- certifi

## 🚀 Instalación y Configuración

### 1. Crear Configuración Encriptada

**IMPORTANTE**: Solo en caso de que no esten o no existan ya los archivos:
- **`config.key`**: Clave de encriptación (¡MANTENER SEGURO!)
- **`config.encrypted`**: Configuración encriptada
- **`Hacer esto ANTES de compilar el ejecutable.`**
```bash
python crear_config.py
```

Este script te pedirá:
- URL de SAP Business One Service Layer
- Base de datos SAP
- Configuración SSL
- Datos de la empresa
- Descuentos máximos por grupo de artículos
- Clientes autorizados

Al terminar, generará:
- ✅ `config.key` (clave de encriptación)
- ✅ `config.encrypted` (configuración encriptada)

### 2. Configurar Google Sheets (Licencias)

1. Crear un proyecto en Google Cloud Console
2. Habilitar Google Sheets API
3. Crear credenciales de cuenta de servicio
4. Descargar el JSON como `credentials/service_account.json`
5. Compartir la hoja de cálculo con el email de la cuenta de servicio

### 3. Estructura de Directorios

```
proyecto/
├── main.py
├── crear_config.py
├── build.spec
├── config.key                    ← Generado por crear_config.py
├── config.encrypted              ← Generado por crear_config.py
├── config/
│   ├── __init__.py
│   ├── secure_config.py
│   ├── settings.py
│   └── certificado.crt          ← Opcional: Certificado SSL de SAP
├── credentials/
│   └── service_account.json     ← Credenciales de Google
├── api/
│   ├── __init__.py
│   ├── sap_client.py
│   └── license_manager.py
├── security/
│   ├── __init__.py
│   └── session_manager.py
├── ui/
│   ├── __init__.py
│   ├── login_dialog.py
│   ├── license_dialog.py
│   └── main_window.py
└── utils/
    ├── __init__.py
    ├── hardware_id.py
    └── logger.py
```

## 🏗️ Compilar Ejecutable

```bash
python -m PyInstaller build.spec
```

### Post-Compilación (CRÍTICO):

Después de compilar, **DEBES copiar manualmente** estos archivos al directorio del ejecutable:

```bash
cp config.key dist/Cotizador_SAP_B1_Seguro/
cp config.encrypted dist/Cotizador_SAP_B1_Seguro/
```

**¿Por qué no se incluyen automáticamente?**

Por seguridad. Si se incluyen en el .exe, podrían extraerse fácilmente. Al mantenerlos como archivos separados:
- Son más difíciles de robar
- Puedes actualizar configuración sin recompilar
- Cada instalación puede tener su propia configuración

## 🔧 Solución de Problemas

### Error: "No se encontró config.encrypted"

**Causa**: Falta el archivo `config.encrypted` junto al ejecutable.

**Solución**:
```bash
cd dist/Cotizador_SAP_B1_Seguro/
# Copiar archivos faltantes
cp ../../config.key .
cp ../../config.encrypted .
cp ../../certificado.crt .
```

### Error: "La clave de encriptación NO coincide"

**Causa**: El `config.key` no corresponde al `config.encrypted`.

**Solución**:
```bash
# Re-crear configuración con la clave actual
python crear_config.py
```

### Error: "SAP rechazó el usuario"

**Posibles causas**:

1. **Usuario/contraseña incorrectos**
   - Verifica las credenciales en SAP Business One
   - Asegúrate que el usuario esté activo

2. **Base de datos incorrecta**
   - Verifica el nombre exacto de la base de datos en `config.encrypted`
   - Re-ejecuta `crear_config.py` si es necesario

3. **URL incorrecta**
   - Formato esperado: `https://servidor:puerto/b1s/v1`
   - Ejemplo: `https://192.168.1.100:50000/b1s/v1`

4. **Problemas de certificado SSL**
   - Si SAP usa certificado autofirmado, configura `SSLCERTPATH` en `crear_config.py`
   - O temporalmente desactiva verificación SSL (NO recomendado en producción)

5. **Firewall bloqueando conexión**
   - Verifica que el puerto SAP esté accesible
   - Prueba con `telnet servidor puerto`

### Verificar Configuración

Para ver qué configuración está cargando la aplicación (sin mostrar datos sensibles):

```bash
python -c "from config.settings import *; print('SAP_BASE_URL:', SAP_BASE_URL); print('SSL_VERIFY:', SSL_VERIFY)"
```

### Debugging

Ejecutar con consola para ver mensajes detallados:

```bash
# En build.spec, asegúrate que:
console=True,  # ← Debe ser True

# Luego recompilar
pyinstaller build.spec
```

## 🔐 Seguridad en Producción

### ✅ Buenas Prácticas:

1. **Nunca** compartas `config.key`
2. **Nunca** subas `config.key` o `config.encrypted` a Git
3. Mantén copias de respaldo de `config.key` en lugar seguro
4. Usa SSL/TLS en producción (`SSL_VERIFY=True`)
5. Limita acceso al directorio del ejecutable
6. Rota credenciales periódicamente

### ❌ NO hacer:

- NO desactives SSL en producción
- NO uses contraseñas débiles
- NO ejecutes con privilegios de administrador innecesariamente
- NO uses `.env.secure` (obsoleto, ya no soportado)

## 📝 Actualizar Configuración

Si necesitas cambiar la configuración (ej: cambiar URL de SAP):

### Opción 1: Re-crear desde cero
```bash
python crear_config.py
# Copiar nuevos archivos al ejecutable
```

### Opción 2: Modificar manualmente (avanzado)

```python
from cryptography.fernet import Fernet
import json

# Leer clave
with open('config.key', 'rb') as f:
    key = f.read()

cipher = Fernet(key)

# Desencriptar
with open('config.encrypted', 'rb') as f:
    encrypted = f.read()

data = json.loads(cipher.decrypt(encrypted).decode('utf-8'))

# Modificar
data['SAP_BASE_URL'] = 'https://nueva-url:50000/b1s/v1'

# Re-encriptar
encrypted = cipher.encrypt(json.dumps(data).encode('utf-8'))

# Guardar
with open('config.encrypted', 'wb') as f:
    f.write(encrypted)
```

## 📞 Soporte

Para problemas o dudas:
1. Revisa los logs en `logs/`
2. Ejecuta con `console=True` para ver errores
3. Verifica que todos los archivos estén en su lugar
4. Contacta al administrador del sistema

## 📄 Licencia

Uso interno de la empresa. Todos los derechos reservados.

---

**Última actualización**: Febrero 2026
**Versión**: 2.0 (con configuración encriptada)
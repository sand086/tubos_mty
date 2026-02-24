"""
Gestor de sesiones SAP con SSL seguro
Versión CORREGIDA - Fix para certificados SSL
"""
import os
import requests
import certifi
import ssl
import tempfile
from datetime import datetime, timedelta
from typing import Optional
import threading
from pathlib import Path


class SecureSessionManager:
    """Administra sesiones seguras con SAP Business One Service Layer"""
    
    def __init__(
        self, 
        base_url: str, 
        timeout: int = 30, 
        ssl_verify: bool = True, 
        ssl_cert_path: Optional[str] = None
    ):
        """
        Inicializa el gestor de sesiones
        
        Args:
            base_url: URL base de SAP Service Layer
            timeout: Timeout en segundos para requests
            ssl_verify: Si verificar certificados SSL
            ssl_cert_path: Ruta al certificado CA personalizado
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.ssl_verify = ssl_verify
        self.ssl_cert_path = ssl_cert_path
        
        # Estado de sesión
        self.session: Optional[requests.Session] = None
        self.session_id: Optional[str] = None
        self.route_id: Optional[str] = None
        self.login_time: Optional[datetime] = None
        self.session_timeout_minutes: int = 25
        
        # Thread safety
        self.lock = threading.Lock()
        
        #print(f"[SESSION] Inicializado:")
        #print(f"   URL: {base_url}")
        #print(f"   SSL Verify: {ssl_verify}")
        #print(f"   Timeout: {timeout}s")
    
    def _create_ssl_context_with_cert(self, cert_path: str):
        """
        Crea un contexto SSL personalizado con el certificado
        
        Args:
            cert_path: Ruta al certificado .crt
            
        Returns:
            str: Ruta a un bundle temporal que combina certifi + certificado personalizado
        """
        try:
            # Leer el certificado personalizado
            with open(cert_path, 'r') as f:
                custom_cert = f.read()
            
            # Leer el bundle de certifi
            certifi_bundle = certifi.where()
            with open(certifi_bundle, 'r') as f:
                certifi_certs = f.read()
            
            # Crear un bundle temporal combinado
            temp_bundle = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
            temp_bundle.write(certifi_certs)
            temp_bundle.write('\n')
            temp_bundle.write(custom_cert)
            temp_bundle.close()
            
            #print(f"[OK] Bundle SSL combinado creado: {temp_bundle.name}")
            return temp_bundle.name
            
        except Exception as e:
            #print(f"[ERROR] No se pudo crear bundle SSL: {e}")
            return None
    
    def _configure_ssl(self, session: requests.Session) -> None:
        """
        Configura validación SSL de forma segura
        
        Args:
            session: Sesión de requests a configurar
        """
        if self.ssl_verify:
            # MODO SEGURO: Verificar certificados
            if self.ssl_cert_path and os.path.exists(self.ssl_cert_path):
                cert_path = Path(self.ssl_cert_path)
                
                try:
                    # Verificar que sea un certificado válido
                    with open(cert_path, 'r') as f:
                        cert_content = f.read()
                        if '-----BEGIN CERTIFICATE-----' not in cert_content:
                            #print(f"[ERROR] Archivo no es un certificado válido: {cert_path}")
                            session.verify = certifi.where()
                            #print("[WARN] Usando certifi bundle")
                            return
                    
                    # CRÍTICO: Crear bundle combinado (certifi + certificado SAP)
                    combined_bundle = self._create_ssl_context_with_cert(str(cert_path))
                    
                    if combined_bundle:
                        session.verify = combined_bundle
                        #print(f"[OK] SSL configurado con certificado: {cert_path.name}")
                    else:
                        # Fallback a certifi
                        session.verify = certifi.where()
                        #print("[WARN] Usando certifi bundle como fallback")
                        
                except Exception as e:
                    #print(f"[ERROR] Error configurando SSL: {e}")
                    # Último recurso: usar solo certifi
                    session.verify = certifi.where()
                    #print("[WARN] Usando certifi bundle")
                
            else:
                # Sin certificado personalizado
                session.verify = certifi.where()
                #print("[OK] SSL con certifi bundle")
                
                if self.ssl_cert_path:
                    print(f"[WARN] Certificado no encontrado: {self.ssl_cert_path}")
        else:
            # MODO INSEGURO: Solo para desarrollo
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            session.verify = False
            #print("[WARN] ⚠️ SSL DESACTIVADO - NO usar en producción")
    
    def login(self, credentials: dict) -> bool:
        """
        Inicia sesión en SAP B1
        
        Args:
            credentials: Dict con CompanyDB, UserName, Password
        
        Returns:
            bool: True si login exitoso
        """
        with self.lock:
            try:
                # Validar credenciales
                required_fields = ['CompanyDB', 'UserName', 'Password']
                for field in required_fields:
                    if field not in credentials or not credentials[field]:
                        #print(f"[ERROR] Campo requerido faltante: {field}")
                        return False
                
                # CRÍTICO: Extraer datos ANTES de usarlos
                # Crear NUEVO dict para evitar modificar el original
                username = str(credentials.get('UserName', 'UNKNOWN'))
                company_db = str(credentials.get('CompanyDB', 'UNKNOWN'))
                password = str(credentials.get('Password', ''))
                
                #print(f"\n[LOGIN] Intentando login en SAP...")
                #print(f"   Usuario: {username}")
                #print(f"   Base de datos: {company_db}")
                #print(f"   URL: {self.base_url}")
                
                # Crear nueva sesión
                self.session = requests.Session()
                self._configure_ssl(self.session)
                
                # Endpoint de login
                login_url = f"{self.base_url}/Login"
                
                # CRÍTICO: Crear payload SEPARADO - NO usar credentials directamente
                login_payload = {
                    'CompanyDB': company_db,
                    'UserName': username,
                    'Password': password
                }
                
                #print(f"[DEBUG] Payload:")
                #print(f"   CompanyDB: {login_payload['CompanyDB']}")
                #print(f"   UserName: {login_payload['UserName']}")
                #print(f"   Password: {'*' * len(login_payload['Password'])}")
                
                # POST request
                #print(f"[REQUEST] POST {login_url}")
                
                try:
                    response = self.session.post(
                        login_url,
                        json=login_payload,
                        timeout=self.timeout,
                        headers={
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        }
                    )
                    
                    print(f"[RESPONSE] Status: {response.status_code}")
                    
                    # Manejo detallado de errores
                    if response.status_code == 401:
                        print(f"[ERROR] Credenciales rechazadas (401)")
                        try:
                            error_data = response.json()
                            error_msg = error_data.get('error', {}).get('message', {}).get('value', 'Credenciales incorrectas')
                            #print(f"[ERROR] SAP dice: {error_msg}")
                        except:
                            print(f"[ERROR] Respuesta: {response.text[:500]}")
                        return False
                    
                    if response.status_code == 500:
                        print(f"[ERROR] Error interno del servidor SAP (500)")
                        try:
                            error_data = response.json()
                            #print(f"[ERROR] Detalle: {error_data}")
                        except:
                            print(f"[ERROR] Response: {response.text[:500]}")
                        return False
                    
                    if response.status_code != 200:
                        print(f"[ERROR] Status inesperado: {response.status_code}")
                        print(f"[ERROR] Response: {response.text[:500]}")
                        return False
                    
                    # Parsear respuesta exitosa
                    try:
                        data = response.json()
                    except ValueError as e:
                        print(f"[ERROR] No se pudo parsear JSON: {e}")
                        print(f"[ERROR] Response: {response.text[:500]}")
                        return False
                    
                    self.session_id = data.get('SessionId')
                    self.route_id = data.get('RouteId', '')
                    self.login_time = datetime.utcnow()
                    
                    if not self.session_id:
                        print(f"[ERROR] Respuesta sin SessionId")
                        print(f"[ERROR] Data: {data}")
                        return False
                    
                    print(f"[OK] ✅ Login exitoso")
                    print(f"   SessionId: {self.session_id[:8]}...")
                    print(f"   RouteId: {self.route_id}")
                    
                    return True
                    
                except requests.exceptions.Timeout:
                    print(f"[ERROR] Timeout al conectar con SAP ({self.timeout}s)")
                    print(f"   Verifica que el servidor SAP esté accesible")
                    return False
                    
                except requests.exceptions.ConnectionError as e:
                    print(f"[ERROR] No se pudo conectar con SAP")
                    print(f"   Error: {e}")
                    print(f"   Verifica:")
                    print(f"   - URL correcta: {self.base_url}")
                    print(f"   - Servidor SAP encendido")
                    print(f"   - Firewall permite la conexión")
                    return False
                    
                except requests.exceptions.SSLError as e:
                    print(f"[ERROR] ❌ Error de certificado SSL")
                    print(f"   Error: {e}")
                    print(f"\n   SOLUCIONES:")
                    print(f"   1. Verifica que el certificado esté en: {self.ssl_cert_path}")
                    print(f"   2. El certificado debe ser el CA root del servidor SAP")
                    print(f"   3. Opción temporal: desactiva SSL en crear_config.py")
                    print(f"      (NO recomendado en producción)")
                    return False
                
            except KeyError as e:
                print(f"[ERROR] Campo faltante: {e}")
                return False
            except Exception as e:
                print(f"[ERROR] Error inesperado: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    def is_session_valid(self) -> bool:
        """
        Verifica si la sesión actual es válida
        
        Returns:
            bool: True si sesión válida
        """
        if not self.session_id or not self.login_time:
            return False
        
        elapsed = datetime.utcnow() - self.login_time
        is_valid = elapsed < timedelta(minutes=self.session_timeout_minutes)
        
        if not is_valid:
            print(f"[TIMEOUT] Sesión expirada: {elapsed.total_seconds():.0f}s")
        
        return is_valid
    
    def logout(self) -> None:
        """Cierra sesión en SAP B1"""
        with self.lock:
            if self.session and self.session_id:
                try:
                    logout_url = f"{self.base_url}/Logout"
                    self.session.post(logout_url, timeout=5)
                    print("[OK] Logout exitoso")
                except Exception as e:
                    print(f"[WARN] Error en logout (ignorado): {e}")
                finally:
                    self._clear_session()
            else:
                self._clear_session()
    
    def _clear_session(self) -> None:
        """Limpia estado de sesión"""
        self.session = None
        self.session_id = None
        self.route_id = None
        self.login_time = None
    
    def get_request_headers(self) -> dict:
        """
        Obtiene headers para requests a SAP
        
        Returns:
            dict: Headers con cookies de sesión
        """
        if not self.session_id:
            raise RuntimeError("No hay sesión activa")
        
        headers = {
            "Content-Type": "application/json",
            "Cookie": f"B1SESSION={self.session_id}"
        }
        
        if self.route_id:
            headers["Cookie"] += f";ROUTEID={self.route_id}"
        
        return headers
    
    def request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> requests.Response:
        """
        Ejecuta request a SAP B1 Service Layer
        
        Args:
            method: Método HTTP (GET, POST, PATCH, DELETE)
            endpoint: Endpoint sin / inicial
            **kwargs: Argumentos adicionales para requests
        
        Returns:
            Response: Respuesta de requests
        
        Raises:
            RuntimeError: Si sesión inválida
        """
        # Validar sesión
        if not self.is_session_valid():
            raise RuntimeError("Sesión expirada. Necesitas hacer login nuevamente.")
        
        # Construir URL
        endpoint = endpoint.lstrip('/')
        url = f"{self.base_url}/{endpoint}"
        
        # Preparar headers
        headers = self.get_request_headers()
        headers.update(kwargs.pop("headers", {}))
        
        # Configurar timeout
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout
        
        try:
            # Ejecutar request
            response = self.session.request(
                method.upper(),
                url,
                headers=headers,
                **kwargs
            )
            
            return response
            
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Timeout en request a {url}")
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(f"Error de conexión: {e}")
        except requests.exceptions.SSLError as e:
            raise RuntimeError(f"Error SSL: {e}")
            
    def get_session_info(self) -> dict:
        """
        Obtiene información de la sesión actual
        
        Returns:
            dict: Información de sesión
        """
        if not self.session_id:
            return {"status": "no_session"}
        
        elapsed = None
        remaining = None
        
        if self.login_time:
            elapsed = datetime.utcnow() - self.login_time
            timeout_delta = timedelta(minutes=self.session_timeout_minutes)
            remaining = timeout_delta - elapsed
        
        return {
            "status": "active" if self.is_session_valid() else "expired",
            "session_id": self.session_id[:8] + "..." if self.session_id else None,
            "login_time": self.login_time.isoformat() if self.login_time else None,
            "elapsed_seconds": int(elapsed.total_seconds()) if elapsed else None,
            "remaining_seconds": int(remaining.total_seconds()) if remaining else None,
        }
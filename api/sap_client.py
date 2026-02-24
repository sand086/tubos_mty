"""
Cliente SAP Business One - Versión sin logs
"""
import re
import requests
from typing import List, Optional, Dict, Any
from security.session_manager import SecureSessionManager
from config.settings import (
    SAP_BASE_URL, SAP_TIMEOUT, SAP_MAX_RESULTS, 
    SSL_VERIFY, DESCUENTOS_MAXIMOS_POR_GRUPO, 
    SSLCERTPATH, get_secure_session
)


class SAPClient:
    """Cliente seguro para SAP Business One Service Layer"""
    
    def __init__(self):
        """Inicializa el cliente SAP con gestión segura de sesiones"""
        self.session_manager = get_secure_session(
            SAP_BASE_URL, 
            SAP_TIMEOUT, 
            SSL_VERIFY, 
            SSLCERTPATH
        )
    
    def login(self, credentials: dict) -> bool:
        """
        Login seguro a SAP B1
        
        Args:
            credentials: Dict con CompanyDB, UserName, Password
        
        Returns:
            bool: True si login exitoso
        """
        try:
            # Validar que credentials tenga los campos necesarios
            if not credentials or not isinstance(credentials, dict):
                return False
            
            # Hacer login - NO modificar el dict original
            login_creds = {
                'CompanyDB': credentials.get('CompanyDB'),
                'UserName': credentials.get('UserName'),
                'Password': credentials.get('Password')
            }
            
            success = self.session_manager.login(login_creds)
            return success
            
        except KeyError:
            return False
        except Exception:
            return False
    
    def logout(self):
        """Cierra sesión de forma segura"""
        try:
            self.session_manager.logout()
        except Exception:
            pass
    
    def get_user_info(self, user_code: str) -> dict:
        """
        Obtiene información del usuario actual
        NOTA: Requiere permisos en SAP - puede fallar con 403
        
        Args:
            user_code: Código del usuario
        
        Returns:
            dict: Información del usuario o dict con datos básicos
        """
        try:
            # Sanitizar user_code
            safe_user_code = self._sanitize_odata_value(user_code)
            
            endpoint = f"Users?$filter=UserCode eq '{safe_user_code}'&$select=UserName,e_Mail"
            resp = self.session_manager.request("GET", endpoint)
            
            # Si es 403, no es crítico - usuario no tiene permisos
            if resp.status_code == 403:
                return {
                    'UserCode': user_code,
                    'UserName': user_code,
                    'e_Mail': ''
                }
            
            resp.raise_for_status()
            
            data = resp.json().get('value', [])
            if data:
                return data[0]
            else:
                # Usuario no encontrado, retornar datos básicos
                return {
                    'UserCode': user_code,
                    'UserName': user_code,
                    'e_Mail': ''
                }
            
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 403:
                return {
                    'UserCode': user_code,
                    'UserName': user_code,
                    'e_Mail': ''
                }
            else:
                return {}
        except Exception:
            return {}
    
    def _sanitize_odata_value(self, value: str) -> str:
        """
        Sanitiza valores para prevenir inyección OData
        
        Args:
            value: Valor a sanitizar
        
        Returns:
            str: Valor sanitizado
        """
        if not value:
            return ""
        
        # Limitar longitud
        value = str(value)[:100]
        
        # Escapar comillas simples (OData)
        value = value.replace("'", "''")
        
        # Remover caracteres peligrosos (control chars, etc)
        value = re.sub(r'[\x00-\x1F\x7F]', '', value)
        
        return value.strip()
    
    def _validate_search_term(self, search_term: str) -> Optional[str]:
        """
        Valida y sanitiza término de búsqueda
        
        Args:
            search_term: Término ingresado por usuario
        
        Returns:
            str: Término sanitizado o None si inválido
        """
        if not search_term or not isinstance(search_term, str):
            return None
        
        # Limitar longitud
        if len(search_term) > 100:
            search_term = search_term[:100]
        
        # Remover espacios extra
        search_term = ' '.join(search_term.split())
        
        if len(search_term) < 1:
            return None
        
        return search_term
    
    def search_items(
        self, 
        search_term: str, 
        filter_str: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca artículos en SAP B1 con paginación automática
        Solo retorna artículos de grupos autorizados
        
        Args:
            search_term: Término de búsqueda (código o nombre)
            filter_str: Filtro OData personalizado (opcional, usar con precaución)
        
        Returns:
            list: Lista de artículos encontrados
        """
        try:
            # 1. Validar término de búsqueda
            validated_term = self._validate_search_term(search_term)
            if not validated_term:
                return []
            
            # 2. Sanitizar término para OData
            safe_term = self._sanitize_odata_value(validated_term)
            
            # 3. Construir filtro seguro
            if not filter_str:
                # Filtro por defecto: buscar en código y nombre
                filter_str = (
                    f"(contains(ItemCode, '{safe_term}') or "
                    f"contains(ItemName, '{safe_term}')) and "
                    f"Frozen eq 'tNO' and "
                    f"Valid eq 'tYES'"
                )
            else:
                # Si viene filtro personalizado, validar caracteres seguros
                if not self._is_safe_odata_filter(filter_str):
                    return []
            
            # 4. Campos a seleccionar
            select_fields = (
                "ItemCode,"
                "ItemName,"
                "ItemsGroupCode,"
                "QuantityOnStock,"
                "QuantityOrderedByCustomers,"
                "QuantityOrderedFromVendors,"
                "SalesUnit,"
                "ItemPrices"
            )
            
            # 5. Búsqueda paginada
            all_items = self._paginated_search(filter_str, select_fields)
            
            # 6. Filtrar por grupos autorizados
            filtered_items = self._filter_by_authorized_groups(all_items)
            
            return filtered_items
            
        except (requests.exceptions.Timeout, 
                requests.exceptions.ConnectionError):
            return []
        except Exception:
            return []
    
    def _is_safe_odata_filter(self, filter_str: str) -> bool:
        """
        Valida que un filtro OData no contenga caracteres peligrosos
        
        Args:
            filter_str: Filtro a validar
        
        Returns:
            bool: True si es seguro
        """
        # Permitir solo caracteres seguros en filtros OData
        safe_pattern = r'^[a-zA-Z0-9\s\(\)\'\"eqandorcontainsgtlt\,\=\$]+$'
        
        if not re.match(safe_pattern, filter_str):
            return False
        
        # Verificar balance de comillas y paréntesis
        if filter_str.count("'") % 2 != 0:
            return False
        if filter_str.count("(") != filter_str.count(")"):
            return False
        
        return True
    
    def _paginated_search(
        self, 
        filter_str: str, 
        select_fields: str,
        page_size: int = 20,
        max_total: int = 3000,
        max_iterations: int = 150
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta búsqueda paginada en SAP
        
        Args:
            filter_str: Filtro OData
            select_fields: Campos a seleccionar
            page_size: Tamaño de página
            max_total: Máximo de items a retornar
            max_iterations: Máximo de iteraciones
        
        Returns:
            list: Items encontrados
        """
        all_items = []
        skip = 0
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Construir endpoint con paginación
            endpoint = (
                f"Items"
                f"?$filter={filter_str}"
                f"&$select={select_fields}"
                f"&$skip={skip}"
                f"&$top={page_size}"
            )
            
            try:
                response = self.session_manager.request("GET", endpoint)
                
                if response.status_code == 401:
                    break
                
                if response.status_code == 400:
                    break
                
                response.raise_for_status()
                
                data = response.json()
                items = data.get('value', [])
                
                # Sin más resultados
                if not items:
                    break
                
                all_items.extend(items)
                
                # Última página (menos items que page_size)
                if len(items) < page_size:
                    break
                
                # Límite máximo alcanzado
                if len(all_items) >= max_total:
                    break
                
                skip += page_size
                
            except (ValueError, requests.exceptions.RequestException):
                break
        
        return all_items
    
    def _filter_by_authorized_groups(
        self, 
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filtra items por grupos autorizados
        
        Args:
            items: Lista de items de SAP
        
        Returns:
            list: Items filtrados
        """
        grupos_autorizados = set(DESCUENTOS_MAXIMOS_POR_GRUPO.keys())
        
        items_filtrados = [
            item for item in items
            if str(item.get('ItemsGroupCode', '')).strip() in grupos_autorizados
        ]
        
        return items_filtrados
    
    def search_business_partners(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Búsqueda segura de Business Partners (Clientes)
        
        Args:
            search_term: Término de búsqueda
        
        Returns:
            list: Lista de clientes encontrados
        """
        try:
            # Validar y sanitizar
            validated_term = self._validate_search_term(search_term)
            if not validated_term:
                return []
            
            safe_term = self._sanitize_odata_value(validated_term)
            
            filter_str = (
                f"(contains(CardCode, '{safe_term}') or "
                f"contains(CardName, '{safe_term}'))"
            )
            
            endpoint = f"BusinessPartners?$filter={filter_str}"
            
            resp = self.session_manager.request("GET", endpoint)
            resp.raise_for_status()
            
            return resp.json().get('value', [])
            
        except Exception:
            return []
    
    def get_item_by_code(self, item_code: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un artículo específico por código
        
        Args:
            item_code: Código del artículo
        
        Returns:
            dict: Datos del artículo o None
        """
        try:
            safe_code = self._sanitize_odata_value(item_code)
            
            endpoint = f"Items('{safe_code}')"
            resp = self.session_manager.request("GET", endpoint)
            
            if resp.status_code == 404:
                return None
            
            resp.raise_for_status()
            return resp.json()
            
        except Exception:
            return None

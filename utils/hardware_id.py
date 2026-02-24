"""
Módulo para obtener ID único de hardware del equipo
"""
import subprocess
import platform
import hashlib
import uuid
import os
from typing import Optional

class HardwareIDGenerator:
    """Genera ID único basado en hardware del equipo"""
    
    @staticmethod
    def get_windows_uuid() -> Optional[str]:
        """Obtiene UUID del sistema Windows"""
        try:
            output = subprocess.check_output(
                'wmic csproduct get uuid',
                shell=True,
                stderr=subprocess.DEVNULL
            ).decode()
            
            lines = output.strip().split('\n')
            if len(lines) >= 2:
                uuid_str = lines[1].strip()
                if uuid_str and uuid_str.lower() != 'uuid':
                    return uuid_str
        except Exception:
            pass
        return None
    
    @staticmethod
    def get_mac_uuid() -> Optional[str]:
        """Obtiene UUID del sistema macOS"""
        try:
            output = subprocess.check_output(
                "ioreg -d2 -c IOPlatformExpertDevice | awk -F\\\" '/IOPlatformUUID/{print $(NF-1)}'",
                shell=True,
                stderr=subprocess.DEVNULL
            ).decode()
            uuid_str = output.strip()
            if uuid_str:
                return uuid_str
        except Exception:
            pass
        return None
    
    @staticmethod
    def get_linux_machine_id() -> Optional[str]:
        """Obtiene machine ID de Linux"""
        try:
            # Probar /etc/machine-id primero
            if os.path.exists('/etc/machine-id'):
                with open('/etc/machine-id', 'r') as f:
                    return f.read().strip()
            
            # Alternativa: /var/lib/dbus/machine-id
            if os.path.exists('/var/lib/dbus/machine-id'):
                with open('/var/lib/dbus/machine-id', 'r') as f:
                    return f.read().strip()
        except Exception:
            pass
        return None
    
    @staticmethod
    def get_fallback_id() -> str:
        """ID de respaldo basado en MAC address"""
        mac = uuid.getnode()
        mac_str = ':'.join(['{:02x}'.format((mac >> elements) & 0xff) 
                            for elements in range(0, 8*6, 8)][::-1])
        return hashlib.sha256(mac_str.encode()).hexdigest()[:32]
    
    @classmethod
    def get_hardware_id(cls) -> str:
        """
        Obtiene ID único del hardware según el sistema operativo
        
        Returns:
            str: ID único del hardware (32 caracteres)
        """
        system = platform.system().lower()
        hardware_id = None
        
        if system == 'windows':
            hardware_id = cls.get_windows_uuid()
        elif system == 'darwin':  # macOS
            hardware_id = cls.get_mac_uuid()
        elif system == 'linux':
            hardware_id = cls.get_linux_machine_id()
        
        # Si no se pudo obtener ID, usar fallback
        if not hardware_id:
            hardware_id = cls.get_fallback_id()
        
        # Normalizar: eliminar guiones y convertir a mayúsculas
        hardware_id = hardware_id.replace('-', '').replace('{', '').replace('}', '')
        hardware_id = hardware_id.upper()[:32]
        
        return hardware_id
    
    @classmethod
    def get_computer_name(cls) -> str:
        """Obtiene el nombre del equipo"""
        try:
            if platform.system().lower() == 'windows':
                return os.environ.get('COMPUTERNAME', platform.node())
            else:
                return platform.node()
        except:
            return 'UNKNOWN'


# Función de conveniencia
def get_hardware_id() -> str:
    """Obtiene el hardware ID del equipo actual"""
    return HardwareIDGenerator.get_hardware_id()


def get_computer_name() -> str:
    """Obtiene el nombre del equipo actual"""
    return HardwareIDGenerator.get_computer_name()

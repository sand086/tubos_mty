import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import os

class SecureLogger:
    """Logger que sanitiza credenciales y maneja encoding correcto"""    
    def __init__(self, name: str, log_dir: Path, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level))
        
        # Evitar duplicación de handlers
        if self.logger.handlers:
            return
        
        # Handler a archivo con encoding UTF-8
        log_file = log_dir / f"{name}.log"
        handler = RotatingFileHandler(
            log_file,
            maxBytes=10485760,  # 10MB
            backupCount=5,
            encoding='utf-8'  # ← CRÍTICO: UTF-8 para soportar cualquier caracter
        )
        
        # Formato (sin credenciales)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Handler a consola con encoding UTF-8 si está disponible
        try:
            console = logging.StreamHandler()
            console.setLevel(logging.INFO)
            console.setFormatter(formatter)
            # Configurar encoding UTF-8 para consola en Windows
            if hasattr(console.stream, 'reconfigure'):
                console.stream.reconfigure(encoding='utf-8')
            self.logger.addHandler(console)
        except Exception:
            pass  # Si falla, solo usar archivo
    
    def sanitize(self, message: str) -> str:
        """Remueve credenciales y emojis problemáticos de logs"""
        import re
        
        # Remover contraseñas
        message = re.sub(r'"[Pp]assword"\s*:\s*"[^"]*"', '"Password": "***"', message)
        # Remover tokens
        message = re.sub(r'"[Ss]ession[Ii]d"\s*:\s*"[^"]*"', '"SessionId": "***"', message)
        
        # Reemplazar emojis comunes con texto
        emoji_map = {
            '✅': '[OK]',
            '❌': '[ERROR]',
            '⚠️': '[WARN]',
            '🔧': '[CONFIG]',
            '🔐': '[AUTH]',
            '📋': '[INFO]',
            '🔍': '[SEARCH]',
            '📦': '[ITEMS]',
            '🚪': '[LOGOUT]',
            '💥': '[EXCEPTION]',
            '⏱️': '[TIMEOUT]',
            '🔌': '[CONN]',
            '📜': '[CERT]',
            '🛡️': '[SECURITY]',
            'ℹ️': '[INFO]',
            '📄': '[DOC]',
            '🔄': '[RELOAD]',
        }
        
        for emoji, replacement in emoji_map.items():
            message = message.replace(emoji, replacement)
        
        return message
    
    def info(self, message: str):
        self.logger.info(self.sanitize(message))
    
    def warning(self, message: str):
        self.logger.warning(self.sanitize(message))
    
    def error(self, message: str):
        self.logger.error(self.sanitize(message))
    
    def debug(self, message: str):
        self.logger.debug(self.sanitize(message))
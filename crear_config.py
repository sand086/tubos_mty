"""
Script para crear configuración encriptada
Ejecutar ANTES de compilar el ejecutable
"""
import sys
from pathlib import Path

# Agregar directorio al path
sys.path.insert(0, str(Path(__file__).parent))

from config.secure_config import create_initial_config

if __name__ == "__main__":
    create_initial_config()
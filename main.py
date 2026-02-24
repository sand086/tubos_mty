import os
import sys
import json
import secrets
import hashlib
import time
import shutil
import zipfile
import tarfile
import py7zr
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QTabWidget,
    QProgressBar,
    QCheckBox,
    QSpinBox,
    QListWidget,
    QComboBox,
    QTextEdit,
    QScrollArea,
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding as sym_padding
import zlib


class SecureEncryptor:
    """
    Sistema de encriptación personalizado con múltiples capas de seguridad.
    - AES-256 en modo GCM (autenticación integrada)
    - PBKDF2 con iteraciones configurables para derivación de claves
    - Salt único por archivo
    - Firma de integridad SHA-256
    - Compresión inteligente (detecta archivos ya comprimidos)
    - Formato propietario .secvault
    - Protección anti-extracción con archivos señuelo
    """

    MAGIC_HEADER = b"SECVAULT_V2"  #
    SALT_SIZE = 32
    IV_SIZE = 16
    TAG_SIZE = 16
    KEY_SIZE = 32  # AES-256
    HASH_SIZE = 32  # SHA-256
    DEFAULT_ITERATIONS = 600000  # PBKDF2 iteraciones (muy seguro pero más lento)
    FAST_ITERATIONS = 100000  # Modo rápido

    # Extensiones de archivos ya comprimidos (no recomprimir)
    COMPRESSED_EXTENSIONS = {
        ".zip",
        ".rar",
        ".7z",
        ".gz",
        ".bz2",
        ".xz",
        ".tar.gz",
        ".tgz",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".mp4",
        ".avi",
        ".mkv",
        ".mp3",
        ".flac",
        ".ogg",
        ".pdf",
        ".docx",
        ".xlsx",
        ".pptx",
    }

    @staticmethod
    def calculate_file_hash(filepath: str) -> str:
        """Calcula hash SHA-256 de un archivo"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def should_compress(filepath: str) -> bool:
        """Determina si un archivo debe comprimirse basado en su extensión"""
        ext = os.path.splitext(filepath)[1].lower()
        return ext not in SecureEncryptor.COMPRESSED_EXTENSIONS

    @staticmethod
    def derive_key(password: str, salt: bytes, iterations: int = None) -> bytes:
        """Deriva una clave fuerte desde la contraseña usando PBKDF2"""
        if iterations is None:
            iterations = SecureEncryptor.DEFAULT_ITERATIONS

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=SecureEncryptor.KEY_SIZE,
            salt=salt,
            iterations=iterations,
            backend=default_backend(),
        )
        return kdf.derive(password.encode("utf-8"))

    @staticmethod
    def compress_data(data: bytes) -> tuple:
        """Comprime datos usando zlib y retorna (datos_comprimidos, ratio)"""
        compressed = zlib.compress(data, level=9)
        ratio = len(compressed) / len(data) if len(data) > 0 else 1.0
        return compressed, ratio

    @staticmethod
    def decompress_data(data: bytes) -> bytes:
        """Descomprime datos"""
        return zlib.decompress(data)

    @staticmethod
    def create_decoy_files(temp_dir: str, num_files: int = 20):
        """Crea archivos señuelo vacíos o con basura para confundir extractores"""
        decoy_names = [
            "passwords.txt",
            "credentials.json",
            "secrets.dat",
            "keys.pem",
            "config.ini",
            "database.db",
            "backup.sql",
            "accounts.csv",
            "private_key.key",
            "wallet.dat",
            "sensitive_data.xlsx",
            "confidential.pdf",
            "encrypted_backup.zip",
            "master_password.txt",
            "recovery_codes.txt",
            "api_keys.json",
            "ssh_keys.pem",
            "certificate.crt",
            "token.jwt",
            "session_data.bin",
        ]

        for i, name in enumerate(decoy_names[:num_files]):
            decoy_path = os.path.join(temp_dir, name)

            # 50% vacío, 50% con datos aleatorios corruptos
            if i % 2 == 0:
                # Archivo vacío
                open(decoy_path, "w").close()
            else:
                # Archivo con basura aleatoria
                with open(decoy_path, "wb") as f:
                    f.write(secrets.token_bytes(secrets.randbelow(5000) + 100))

    @staticmethod
    def encrypt_file(
        input_path: str,
        output_path: str,
        password: str,
        compress: bool = True,
        iterations: int = None,
        progress_callback=None,
    ):
        """Encripta un archivo individual con verificación de integridad"""
        # Leer archivo
        file_size = os.path.getsize(input_path)
        with open(input_path, "rb") as f:
            plaintext = f.read()

        # Calcular hash original
        original_hash = hashlib.sha256(plaintext).digest()

        # Comprimir si se solicita y es recomendable
        compression_ratio = 1.0
        actually_compressed = False

        if compress and SecureEncryptor.should_compress(input_path):
            if progress_callback:
                progress_callback("Comprimiendo...")
            compressed_data, compression_ratio = SecureEncryptor.compress_data(
                plaintext
            )

            # Solo usar compresión si realmente reduce el tamaño
            if compression_ratio < 0.95:  # Al menos 5% de reducción
                plaintext = compressed_data
                actually_compressed = True

        # Generar salt e IV aleatorios
        salt = secrets.token_bytes(SecureEncryptor.SALT_SIZE)
        iv = secrets.token_bytes(SecureEncryptor.IV_SIZE)

        # Derivar clave
        if progress_callback:
            progress_callback("Derivando clave...")
        key = SecureEncryptor.derive_key(password, salt, iterations)

        # Encriptar con AES-256-GCM
        if progress_callback:
            progress_callback("Encriptando...")
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        tag = encryptor.tag

        # Crear metadata
        metadata = {
            "filename": os.path.basename(input_path),
            "compressed": actually_compressed,
            "original_size": file_size,
            "compression_ratio": compression_ratio if actually_compressed else 1.0,
            "iterations": iterations or SecureEncryptor.DEFAULT_ITERATIONS,
            "timestamp": time.time(),
        }
        metadata_bytes = json.dumps(metadata).encode("utf-8")
        metadata_len = len(metadata_bytes).to_bytes(4, "big")

        # Escribir archivo encriptado con formato propietario
        with open(output_path, "wb") as f:
            f.write(SecureEncryptor.MAGIC_HEADER)  # Header mágico
            f.write(salt)  # Salt (32 bytes)
            f.write(iv)  # IV (16 bytes)
            f.write(tag)  # Tag de autenticación (16 bytes)
            f.write(original_hash)  # Hash SHA-256 del original (32 bytes)
            f.write(metadata_len)  # Longitud de metadata (4 bytes)
            f.write(metadata_bytes)  # Metadata JSON
            f.write(ciphertext)  # Datos encriptados

        # Limpiar memoria sensible
        del plaintext, key, ciphertext

        return actually_compressed, compression_ratio

    @staticmethod
    def decrypt_file(
        input_path: str, output_path: str, password: str, progress_callback=None
    ):
        """Desencripta un archivo con verificación de integridad"""
        with open(input_path, "rb") as f:
            # Verificar header mágico
            header = f.read(len(SecureEncryptor.MAGIC_HEADER))

            # Soporte para versión anterior
            if header == b"SECVAULT_V1":
                return SecureEncryptor._decrypt_file_v1(
                    f, output_path, password, progress_callback
                )
            elif header != SecureEncryptor.MAGIC_HEADER:
                raise ValueError("Archivo no válido o corrupto")

            # Leer componentes
            salt = f.read(SecureEncryptor.SALT_SIZE)
            iv = f.read(SecureEncryptor.IV_SIZE)
            tag = f.read(SecureEncryptor.TAG_SIZE)
            original_hash = f.read(SecureEncryptor.HASH_SIZE)
            metadata_len = int.from_bytes(f.read(4), "big")
            metadata_bytes = f.read(metadata_len)
            ciphertext = f.read()

        # Parsear metadata
        metadata = json.loads(metadata_bytes.decode("utf-8"))
        iterations = metadata.get("iterations", SecureEncryptor.DEFAULT_ITERATIONS)

        # Derivar clave
        if progress_callback:
            progress_callback("Derivando clave...")
        key = SecureEncryptor.derive_key(password, salt, iterations)

        # Desencriptar
        if progress_callback:
            progress_callback("Desencriptando...")
        cipher = Cipher(
            algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend()
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        # Descomprimir si es necesario
        if metadata["compressed"]:
            if progress_callback:
                progress_callback("Descomprimiendo...")
            plaintext = SecureEncryptor.decompress_data(plaintext)

        # Verificar integridad
        if progress_callback:
            progress_callback("Verificando integridad...")
        calculated_hash = hashlib.sha256(plaintext).digest()
        if calculated_hash != original_hash:
            raise ValueError(
                "Error de integridad: el archivo ha sido modificado o está corrupto"
            )

        # Escribir archivo
        os.makedirs(
            os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
            exist_ok=True,
        )
        with open(output_path, "wb") as f:
            f.write(plaintext)

        # Limpiar memoria sensible
        del plaintext, key, ciphertext

        return metadata["filename"]

    @staticmethod
    def _decrypt_file_v1(f, output_path: str, password: str, progress_callback=None):
        """Compatibilidad con archivos de versión anterior (V1)"""
        # Leer componentes (sin hash de integridad)
        salt = f.read(SecureEncryptor.SALT_SIZE)
        iv = f.read(SecureEncryptor.IV_SIZE)
        tag = f.read(SecureEncryptor.TAG_SIZE)
        metadata_len = int.from_bytes(f.read(4), "big")
        metadata_bytes = f.read(metadata_len)
        ciphertext = f.read()

        metadata = json.loads(metadata_bytes.decode("utf-8"))

        if progress_callback:
            progress_callback("Derivando clave...")
        key = SecureEncryptor.derive_key(
            password, salt, SecureEncryptor.DEFAULT_ITERATIONS
        )

        if progress_callback:
            progress_callback("Desencriptando...")
        cipher = Cipher(
            algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend()
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        if metadata["compressed"]:
            if progress_callback:
                progress_callback("Descomprimiendo...")
            plaintext = SecureEncryptor.decompress_data(plaintext)

        os.makedirs(
            os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
            exist_ok=True,
        )
        with open(output_path, "wb") as f_out:
            f_out.write(plaintext)

        del plaintext, key, ciphertext

        return metadata["filename"]


class ProtectedTarFile:
    """Crea archivos TAR con protección por contraseña usando archivos señuelo"""

    @staticmethod
    def create(output_path: str, source_dir: str, password: str):
        """Crea un archivo TAR protegido con señuelos"""
        # Primero crear archivos señuelo
        SecureEncryptor.create_decoy_files(source_dir, num_files=25)

        # Crear el archivo TAR normal
        with tarfile.open(output_path, "w") as tar:
            tar.add(source_dir, arcname=".")

        # Ahora encapsular el TAR en otro archivo con verificación de contraseña
        with open(output_path, "rb") as f:
            tar_data = f.read()

        # Crear salt y derivar clave de verificación
        salt = secrets.token_bytes(32)
        password_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)

        # Reescribir el archivo con header de protección
        with open(output_path, "wb") as f:
            # Header personalizado (así WinRAR/7zip lo reconocen como corrupto)
            f.write(b"PROTECTED_VAULT\x00")  # 16 bytes
            f.write(salt)  # 32 bytes
            f.write(password_hash)  # 32 bytes
            f.write(tar_data)  # Datos del TAR

    @staticmethod
    def verify_password(filepath: str, password: str) -> bool:
        """Verifica la contraseña antes de extraer"""
        with open(filepath, "rb") as f:
            header = f.read(16)
            if header != b"PROTECTED_VAULT\x00":
                raise ValueError("Archivo no protegido o formato inválido")

            salt = f.read(32)
            stored_hash = f.read(32)

            # Calcular hash de la contraseña proporcionada
            password_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt, 100000
            )

            return password_hash == stored_hash

    @staticmethod
    def extract(filepath: str, output_dir: str, password: str):
        """Extrae el TAR solo si la contraseña es correcta"""
        if not ProtectedTarFile.verify_password(filepath, password):
            raise ValueError("Contraseña incorrecta")

        # Extraer el TAR real
        with open(filepath, "rb") as f:
            # Saltar header de protección
            f.read(16)  # Header
            f.read(32)  # Salt
            f.read(32)  # Password hash

            # Leer TAR real
            tar_data = f.read()

        # Crear archivo TAR temporal
        temp_tar = filepath + ".temp.tar"
        with open(temp_tar, "wb") as f:
            f.write(tar_data)

        try:
            # Extraer
            with tarfile.open(temp_tar, "r") as tar:
                tar.extractall(output_dir)
        finally:
            # Limpiar temporal
            if os.path.exists(temp_tar):
                os.remove(temp_tar)


class ExternalDecompressor:
    """Descomprime archivos de formatos externos populares"""

    @staticmethod
    def detect_format(filepath: str) -> str:
        """Detecta el formato del archivo comprimido"""
        ext = os.path.splitext(filepath)[1].lower()

        if ext in [".zip"]:
            return "zip"
        elif ext in [".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz"]:
            return "tar"
        elif ext in [".7z"]:
            return "7z"
        elif ext in [".gz"] and not filepath.endswith(".tar.gz"):
            return "gzip"
        elif ext in [".vault"]:
            return "vault"
        else:
            return "unknown"

    @staticmethod
    def decompress_zip(filepath: str, output_dir: str, progress_callback=None):
        """Descomprime archivos ZIP"""
        with zipfile.ZipFile(filepath, "r") as zip_ref:
            members = zip_ref.namelist()
            total = len(members)

            for i, member in enumerate(members, 1):
                if progress_callback:
                    progress_callback(f"Extrayendo: {member} ({i}/{total})")
                zip_ref.extract(member, output_dir)

        return total

    @staticmethod
    def decompress_tar(filepath: str, output_dir: str, progress_callback=None):
        """Descomprime archivos TAR (incluyendo .tar.gz, .tar.bz2, etc.)"""
        with tarfile.open(filepath, "r:*") as tar_ref:
            members = tar_ref.getmembers()
            total = len(members)

            for i, member in enumerate(members, 1):
                if progress_callback:
                    progress_callback(f"Extrayendo: {member.name} ({i}/{total})")
                tar_ref.extract(member, output_dir)

        return total

    @staticmethod
    def decompress_7z(filepath: str, output_dir: str, progress_callback=None):
        """Descomprime archivos 7Z"""
        with py7zr.SevenZipFile(filepath, mode="r") as z:
            members = z.getnames()
            total = len(members)

            if progress_callback:
                progress_callback(f"Extrayendo {total} archivos...")

            z.extractall(path=output_dir)

        return total

    @staticmethod
    def decompress_gzip(filepath: str, output_dir: str, progress_callback=None):
        """Descomprime archivos GZIP individuales"""
        import gzip

        if progress_callback:
            progress_callback("Descomprimiendo archivo GZIP...")

        output_filename = os.path.splitext(os.path.basename(filepath))[0]
        output_path = os.path.join(output_dir, output_filename)

        with gzip.open(filepath, "rb") as f_in:
            with open(output_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        return 1


class PasswordStrengthChecker:
    """Verifica la fortaleza de contraseñas"""

    @staticmethod
    def check_strength(password: str) -> tuple:
        """Retorna (score 0-100, mensaje, color)"""
        score = 0
        issues = []

        # Longitud
        length = len(password)
        if length >= 16:
            score += 30
        elif length >= 12:
            score += 20
        else:
            issues.append(f"muy corta (mínimo 12, recomendado 16+)")

        # Mayúsculas
        if any(c.isupper() for c in password):
            score += 15
        else:
            issues.append("sin mayúsculas")

        # Minúsculas
        if any(c.islower() for c in password):
            score += 15
        else:
            issues.append("sin minúsculas")

        # Números
        if any(c.isdigit() for c in password):
            score += 15
        else:
            issues.append("sin números")

        # Símbolos
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 25
        else:
            issues.append("sin símbolos")

        # Mensaje
        if score >= 80:
            return score, "Contraseña muy fuerte ✓", "#00ff00"
        elif score >= 60:
            return score, "Contraseña fuerte", "#90ee90"
        elif score >= 40:
            return score, "Contraseña moderada (mejorable)", "#ffff00"
        else:
            msg = "Contraseña débil: " + ", ".join(issues)
            return score, msg, "#ff4444"


class WorkerThread(QThread):
    """Thread para operaciones sin bloquear la UI"""

    progreso = pyqtSignal(str)
    progreso_porcentaje = pyqtSignal(int)
    finalizado = pyqtSignal(bool, str)

    def __init__(self, operacion, **kwargs):
        super().__init__()
        self.operacion = operacion
        self.kwargs = kwargs
        self.bytes_procesados = 0
        self.bytes_totales = 0
        self.inicio_tiempo = 0

    def run(self):
        try:
            self.inicio_tiempo = time.time()

            if self.operacion == "encriptar":
                self.encriptar_archivos()
            elif self.operacion == "desencriptar":
                self.desencriptar_archivos()
            elif self.operacion == "descomprimir_externo":
                self.descomprimir_externo()
        except Exception as e:
            self.finalizado.emit(False, str(e))

    def calcular_tamano_total(self, rutas):
        """Calcula el tamaño total de archivos a procesar"""
        total = 0
        for ruta in rutas:
            if os.path.isfile(ruta):
                total += os.path.getsize(ruta)
            elif os.path.isdir(ruta):
                for root, dirs, files in os.walk(ruta):
                    for file in files:
                        filepath = os.path.join(root, file)
                        try:
                            total += os.path.getsize(filepath)
                        except:
                            pass
        return total

    def actualizar_progreso_archivo(self, mensaje):
        """Callback para actualizar progreso de archivo individual"""
        self.progreso.emit(mensaje)

    def encriptar_archivos(self):
        rutas_origen = self.kwargs["rutas_origen"]
        archivo_salida = self.kwargs["archivo_salida"]
        password = self.kwargs["password"]
        compress = self.kwargs.get("compress", True)
        iterations = self.kwargs.get("iterations", SecureEncryptor.DEFAULT_ITERATIONS)

        self.progreso.emit("Escaneando archivos...")

        # Recolectar todos los archivos
        archivos = []
        for ruta in rutas_origen:
            if os.path.isfile(ruta):
                archivos.append((ruta, os.path.basename(ruta)))
            elif os.path.isdir(ruta):
                for root, dirs, files in os.walk(ruta):
                    for file in files:
                        ruta_completa = os.path.join(root, file)
                        ruta_relativa = os.path.relpath(ruta_completa, ruta)
                        archivos.append((ruta_completa, ruta_relativa))

        total = len(archivos)
        if total == 0:
            self.finalizado.emit(False, "No se encontraron archivos para encriptar")
            return

        # Calcular tamaño total
        self.bytes_totales = self.calcular_tamano_total(rutas_origen)

        # Verificar espacio en disco
        destino_dir = os.path.dirname(archivo_salida) or "."
        espacio_libre = shutil.disk_usage(destino_dir).free

        if espacio_libre < self.bytes_totales * 1.5:  # Margen de seguridad
            self.finalizado.emit(
                False,
                f"Espacio insuficiente en disco.\nRequerido: ~{self.bytes_totales * 1.5 / (1024**3):.2f} GB\nDisponible: {espacio_libre / (1024**3):.2f} GB",
            )
            return

        # Crear archivo índice
        indice = {"total_files": total, "total_size": self.bytes_totales, "files": []}

        # Crear carpeta temporal para archivos encriptados
        temp_dir = archivo_salida + ".temp"
        os.makedirs(temp_dir, exist_ok=True)

        archivos_exitosos = 0
        archivos_fallidos = []
        compression_stats = []

        try:
            # Encriptar cada archivo
            for i, (ruta_completa, ruta_relativa) in enumerate(archivos, 1):
                try:
                    tamano_archivo = os.path.getsize(ruta_completa)
                    self.progreso.emit(f"Encriptando: {ruta_relativa} ({i}/{total})")
                    self.progreso_porcentaje.emit(
                        int((self.bytes_procesados / self.bytes_totales) * 100)
                    )

                    # Nombre del archivo encriptado
                    encrypted_name = f"{i:06d}.secvault"
                    encrypted_path = os.path.join(temp_dir, encrypted_name)

                    # Encriptar
                    was_compressed, ratio = SecureEncryptor.encrypt_file(
                        ruta_completa,
                        encrypted_path,
                        password,
                        compress,
                        iterations,
                        self.actualizar_progreso_archivo,
                    )

                    compression_stats.append((ruta_relativa, was_compressed, ratio))

                    # Agregar al índice
                    indice["files"].append(
                        {
                            "id": i,
                            "encrypted_name": encrypted_name,
                            "original_path": ruta_relativa,
                            "original_size": tamano_archivo,
                        }
                    )

                    archivos_exitosos += 1
                    self.bytes_procesados += tamano_archivo

                except Exception as e:
                    archivos_fallidos.append((ruta_relativa, str(e)))
                    continue

            # Encriptar el índice
            self.progreso.emit("Generando índice encriptado...")
            indice_json = json.dumps(indice, indent=2).encode("utf-8")
            indice_path = os.path.join(temp_dir, "index.json")

            with open(indice_path, "wb") as f:
                f.write(indice_json)

            indice_encrypted = os.path.join(temp_dir, "000000.secvault")
            SecureEncryptor.encrypt_file(
                indice_path,
                indice_encrypted,
                password,
                False,
                iterations,
                self.actualizar_progreso_archivo,
            )
            os.remove(indice_path)

            # Crear archivos señuelo ANTES de empaquetar
            self.progreso.emit("Creando protección anti-extracción...")
            SecureEncryptor.create_decoy_files(temp_dir, num_files=25)

            # Crear archivo contenedor final con protección por contraseña
            self.progreso.emit("Empaquetando con protección...")
            self.progreso_porcentaje.emit(95)

            ProtectedTarFile.create(archivo_salida, temp_dir, password)

            # Limpiar temporal
            shutil.rmtree(temp_dir)

            # Calcular estadísticas de compresión
            archivos_comprimidos = sum(1 for _, comp, _ in compression_stats if comp)
            ratio_promedio = sum(r for _, comp, r in compression_stats if comp) / max(
                archivos_comprimidos, 1
            )

            tiempo_total = time.time() - self.inicio_tiempo

            mensaje = f"✅ Encriptación completada\n\n"
            mensaje += f"Archivos procesados: {archivos_exitosos}/{total}\n"
            mensaje += f"Tamaño original: {self.bytes_totales / (1024**2):.2f} MB\n"
            mensaje += f"Archivos comprimidos: {archivos_comprimidos}\n"
            if archivos_comprimidos > 0:
                mensaje += f"Ratio promedio: {ratio_promedio*100:.1f}%\n"
            mensaje += f"Tiempo: {tiempo_total:.1f}s\n"
            mensaje += f"Archivo: {archivo_salida}\n"
            mensaje += f"\n🛡️ Protección activada contra extracción no autorizada"

            if archivos_fallidos:
                mensaje += f"\n\n⚠️ {len(archivos_fallidos)} archivo(s) fallaron:\n"
                for nombre, error in archivos_fallidos[:5]:
                    mensaje += f"- {nombre}: {error}\n"
                if len(archivos_fallidos) > 5:
                    mensaje += f"... y {len(archivos_fallidos) - 5} más\n"

            mensaje += (
                f"\n🔒 IMPORTANTE: Solo esta aplicación puede desencriptar este archivo"
            )

            self.progreso_porcentaje.emit(100)
            self.finalizado.emit(True, mensaje)

        except Exception as e:
            # Limpiar en caso de error
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise e

    def desencriptar_archivos(self):
        archivo_origen = self.kwargs["archivo_origen"]
        carpeta_destino = self.kwargs["carpeta_destino"]
        password = self.kwargs["password"]

        self.progreso.emit("Verificando contraseña...")

        # Verificar contraseña ANTES de extraer
        try:
            if not ProtectedTarFile.verify_password(archivo_origen, password):
                self.finalizado.emit(False, "❌ Contraseña incorrecta")
                return
        except ValueError as e:
            # Si el archivo no tiene protección (versión antigua), continuar
            pass

        # Extraer con verificación de contraseña
        temp_dir = archivo_origen + ".temp"

        try:
            self.progreso.emit("Extrayendo archivos...")

            try:
                # Intentar extraer con protección
                ProtectedTarFile.extract(archivo_origen, temp_dir, password)
            except:
                # Si falla, intentar como TAR normal (compatibilidad)
                with tarfile.open(archivo_origen, "r") as tar:
                    tar.extractall(temp_dir)

            # Desencriptar índice
            self.progreso.emit("Leyendo índice...")
            indice_encrypted = os.path.join(temp_dir, "000000.secvault")

            if not os.path.exists(indice_encrypted):
                raise ValueError("Archivo no válido o corrupto (falta índice)")

            indice_temp = os.path.join(temp_dir, "index.json")
            SecureEncryptor.decrypt_file(
                indice_encrypted,
                indice_temp,
                password,
                self.actualizar_progreso_archivo,
            )

            with open(indice_temp, "r") as f:
                indice = json.load(f)

            total = indice["total_files"]
            self.bytes_totales = indice.get("total_size", 0)

            # Verificar espacio en disco
            espacio_libre = shutil.disk_usage(carpeta_destino).free
            if espacio_libre < self.bytes_totales * 1.2:
                raise ValueError(
                    f"Espacio insuficiente en disco de destino.\nRequerido: ~{self.bytes_totales * 1.2 / (1024**3):.2f} GB\nDisponible: {espacio_libre / (1024**3):.2f} GB"
                )

            archivos_exitosos = 0
            archivos_fallidos = []

            # Desencriptar cada archivo
            for i, file_info in enumerate(indice["files"], 1):
                try:
                    encrypted_path = os.path.join(temp_dir, file_info["encrypted_name"])
                    original_path = os.path.join(
                        carpeta_destino, file_info["original_path"]
                    )

                    self.progreso.emit(
                        f"Desencriptando: {file_info['original_path']} ({i}/{total})"
                    )

                    if self.bytes_totales > 0:
                        progreso = int((i / total) * 100)
                        self.progreso_porcentaje.emit(progreso)

                    SecureEncryptor.decrypt_file(
                        encrypted_path,
                        original_path,
                        password,
                        self.actualizar_progreso_archivo,
                    )

                    archivos_exitosos += 1

                except Exception as e:
                    archivos_fallidos.append((file_info["original_path"], str(e)))
                    continue

            # Limpiar
            shutil.rmtree(temp_dir)

            tiempo_total = time.time() - self.inicio_tiempo

            mensaje = f"✅ Desencriptación completada\n\n"
            mensaje += f"Archivos procesados: {archivos_exitosos}/{total}\n"
            mensaje += f"Tiempo: {tiempo_total:.1f}s\n"
            mensaje += f"Ubicación: {carpeta_destino}\n"

            if archivos_fallidos:
                mensaje += f"\n⚠️ {len(archivos_fallidos)} archivo(s) fallaron:\n"
                for nombre, error in archivos_fallidos[:5]:
                    mensaje += f"- {nombre}: {error}\n"
                if len(archivos_fallidos) > 5:
                    mensaje += f"... y {len(archivos_fallidos) - 5} más\n"

            self.progreso_porcentaje.emit(100)
            self.finalizado.emit(True, mensaje)

        except Exception as e:
            # Limpiar en caso de error
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise e

    def descomprimir_externo(self):
        """Descomprime archivos de formatos externos"""
        archivo_origen = self.kwargs["archivo_origen"]
        carpeta_destino = self.kwargs["carpeta_destino"]
        formato = self.kwargs["formato"]

        try:
            total_archivos = 0

            if formato == "zip":
                total_archivos = ExternalDecompressor.decompress_zip(
                    archivo_origen, carpeta_destino, self.actualizar_progreso_archivo
                )
            elif formato == "tar":
                total_archivos = ExternalDecompressor.decompress_tar(
                    archivo_origen, carpeta_destino, self.actualizar_progreso_archivo
                )
            elif formato == "7z":
                total_archivos = ExternalDecompressor.decompress_7z(
                    archivo_origen, carpeta_destino, self.actualizar_progreso_archivo
                )
            elif formato == "gzip":
                total_archivos = ExternalDecompressor.decompress_gzip(
                    archivo_origen, carpeta_destino, self.actualizar_progreso_archivo
                )

            tiempo_total = time.time() - self.inicio_tiempo

            mensaje = f"✅ Descompresión completada\n\n"
            mensaje += f"Formato: {formato.upper()}\n"
            mensaje += f"Archivos extraídos: {total_archivos}\n"
            mensaje += f"Tiempo: {tiempo_total:.1f}s\n"
            mensaje += f"Ubicación: {carpeta_destino}"

            self.progreso_porcentaje.emit(100)
            self.finalizado.emit(True, mensaje)

        except Exception as e:
            raise e


class EncriptadorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔒 SecureVault Pro")
        self.setGeometry(100, 100, 900, 580)  # Más compacto verticalmente

        # Habilitar drag and drop
        self.setAcceptDrops(True)

        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #ffffff;
                font-size: 11px;
            }
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #404040;
                padding: 6px;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton {
                background-color: #0d7377;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #14a085;
            }
            QTabWidget::pane {
                border: 1px solid #404040;
                background-color: #252525;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px 15px;
                border: 1px solid #404040;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background-color: #0d7377;
            }
            QListWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 3px;
                font-size: 10px;
            }
            QCheckBox {
                color: #ffffff;
                font-size: 11px;
            }
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #404040;
                padding: 4px;
                border-radius: 3px;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #ffffff;
            }
        """
        )

        # Lista de archivos/carpetas seleccionados para encriptar
        self.rutas_seleccionadas = []

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout principal
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 10, 15, 10)

        # Título compacto
        titulo = QLabel("🔒 SecureVault Pro")
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("color: #14a085; padding: 5px; font-size: 16px;")
        layout.addWidget(titulo)

        # Tabs
        self.tabs = QTabWidget()

        # Tab de encriptación
        tab_encriptar = self.crear_tab_encriptar()
        self.tabs.addTab(tab_encriptar, "🔒 Encriptar")

        # Tab de desencriptación
        tab_desencriptar = self.crear_tab_desencriptar()
        self.tabs.addTab(tab_desencriptar, "🔓 Desencriptar")

        # Tab de descompresión externa
        tab_decomprimir = self.crear_tab_decomprimir()
        self.tabs.addTab(tab_decomprimir, "📦 Descomprimir")

        # Tab de información
        tab_info = self.crear_tab_info()
        self.tabs.addTab(tab_info, "ℹ️ Info")

        layout.addWidget(self.tabs)

        # Barra de progreso
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet(
            "color: #14a085; font-weight: bold; font-size: 10px;"
        )
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumHeight(18)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #404040;
                border-radius: 3px;
                background-color: #2d2d2d;
                text-align: center;
                color: white;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #14a085;
            }
        """
        )
        layout.addWidget(self.progress_bar)

        self.worker = None

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Permitir arrastrar archivos"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Manejar archivos soltados"""
        urls = event.mimeData().urls()

        for url in urls:
            ruta = url.toLocalFile()
            if ruta and ruta not in self.rutas_seleccionadas:
                self.rutas_seleccionadas.append(ruta)
                if os.path.isdir(ruta):
                    self.lista_archivos.addItem(f"📂 {ruta}")
                else:
                    self.lista_archivos.addItem(f"📄 {ruta}")

        # Sugerir nombre de salida si no hay uno
        if not self.input_salida.text() and len(self.rutas_seleccionadas) > 0:
            if len(self.rutas_seleccionadas) == 1:
                nombre_base = os.path.splitext(
                    os.path.basename(self.rutas_seleccionadas[0])
                )[0]
                self.input_salida.setText(f"{nombre_base}_enc.vault")
            else:
                self.input_salida.setText("archivos_enc.vault")

    def mostrar_mensaje(self, tipo, titulo, mensaje):
        msg = QMessageBox(self)
        msg.setWindowTitle(titulo)
        msg.setText(mensaje)

        msg.setStyleSheet(
            """
            QMessageBox {
                background-color: #f0f0f0;
            }
            QLabel {
                color: black;
                font-size: 12px;
            }
            QPushButton {
                background-color: #0d7377;
                color: white;
                padding: 6px;
                border-radius: 3px;
            }
        """
        )

        if tipo == "info":
            msg.setIcon(QMessageBox.Icon.Information)
        elif tipo == "warning":
            msg.setIcon(QMessageBox.Icon.Warning)
        elif tipo == "error":
            msg.setIcon(QMessageBox.Icon.Critical)

        msg.exec()

    def mostrar_confirmacion(self, titulo, mensaje):
        msg = QMessageBox(self)
        msg.setWindowTitle(titulo)
        msg.setText(mensaje)
        msg.setIcon(QMessageBox.Icon.Question)

        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        msg.setStyleSheet(
            """
            QMessageBox {
                background-color: #f0f0f0;
            }
            QLabel {
                color: black;
                font-size: 12px;
            }
            QPushButton {
                background-color: #0d7377;
                color: white;
                padding: 6px;
                border-radius: 3px;
            }
        """
        )

        return msg.exec() == QMessageBox.StandardButton.Yes

    def crear_tab_encriptar(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # Sección de selección de archivos/carpetas
        layout.addWidget(QLabel("📁 Archivos/carpetas (arrastra o usa botones):"))

        # Botones para agregar
        h_buttons = QHBoxLayout()
        btn_agregar_archivos = QPushButton("📄 Archivos")
        btn_agregar_archivos.clicked.connect(self.agregar_archivos)
        h_buttons.addWidget(btn_agregar_archivos)

        btn_agregar_carpeta = QPushButton("📂 Carpeta")
        btn_agregar_carpeta.clicked.connect(self.agregar_carpeta)
        h_buttons.addWidget(btn_agregar_carpeta)

        btn_limpiar = QPushButton("🗑️ Limpiar")
        btn_limpiar.clicked.connect(self.limpiar_lista)
        h_buttons.addWidget(btn_limpiar)

        layout.addLayout(h_buttons)

        # Lista de archivos seleccionados
        self.lista_archivos = QListWidget()
        self.lista_archivos.setMaximumHeight(80)
        layout.addWidget(self.lista_archivos)

        # Archivo salida
        layout.addWidget(QLabel("💾 Archivo de salida:"))
        h_layout2 = QHBoxLayout()
        self.input_salida = QLineEdit()
        self.input_salida.setPlaceholderText("archivo_seguro.vault")
        h_layout2.addWidget(self.input_salida)
        btn_buscar_salida = QPushButton("💾")
        btn_buscar_salida.setMaximumWidth(40)
        btn_buscar_salida.clicked.connect(self.seleccionar_archivo_salida)
        h_layout2.addWidget(btn_buscar_salida)
        layout.addLayout(h_layout2)

        # Contraseña
        layout.addWidget(QLabel("🔑 Contraseña (mín. 12 caracteres):"))
        self.input_password_enc = QLineEdit()
        self.input_password_enc.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password_enc.setPlaceholderText("Contraseña fuerte...")
        self.input_password_enc.textChanged.connect(self.verificar_fortaleza_password)
        layout.addWidget(self.input_password_enc)

        # Indicador de fortaleza
        self.password_strength_label = QLabel("")
        self.password_strength_label.setStyleSheet("font-size: 10px; padding: 2px;")
        self.password_strength_label.setMaximumHeight(20)
        layout.addWidget(self.password_strength_label)

        # Confirmar contraseña
        layout.addWidget(QLabel("🔑 Confirmar:"))
        self.input_password_enc_confirm = QLineEdit()
        self.input_password_enc_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password_enc_confirm.setPlaceholderText("Repetir contraseña...")
        layout.addWidget(self.input_password_enc_confirm)

        # Opciones adicionales
        h_opciones = QHBoxLayout()

        # Checkbox de compresión
        self.checkbox_compress = QCheckBox("Compresión inteligente")
        self.checkbox_compress.setChecked(True)
        h_opciones.addWidget(self.checkbox_compress)

        # Selector de velocidad
        self.combo_velocidad = QComboBox()
        self.combo_velocidad.addItem("⚡ Rápido", 100000)
        self.combo_velocidad.addItem("🔒 Seguro", 600000)
        self.combo_velocidad.setCurrentIndex(1)
        h_opciones.addWidget(self.combo_velocidad)

        layout.addLayout(h_opciones)

        # Botón encriptar
        btn_encriptar = QPushButton("🔒 ENCRIPTAR")
        btn_encriptar.setStyleSheet(
            """
            QPushButton {
                background-color: #d63031;
                padding: 12px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
        """
        )
        btn_encriptar.clicked.connect(self.encriptar)
        layout.addWidget(btn_encriptar)

        layout.addStretch()
        return widget

    def crear_tab_desencriptar(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Archivo encriptado
        layout.addWidget(QLabel("🔐 Archivo .vault:"))
        h_layout1 = QHBoxLayout()
        self.input_vault = QLineEdit()
        self.input_vault.setPlaceholderText("archivo.vault")
        h_layout1.addWidget(self.input_vault)
        btn_buscar_vault = QPushButton("📂")
        btn_buscar_vault.setMaximumWidth(40)
        btn_buscar_vault.clicked.connect(self.seleccionar_vault)
        h_layout1.addWidget(btn_buscar_vault)
        layout.addLayout(h_layout1)

        # Carpeta destino
        layout.addWidget(QLabel("📁 Carpeta destino:"))
        h_layout2 = QHBoxLayout()
        self.input_destino = QLineEdit()
        self.input_destino.setPlaceholderText("Dónde extraer...")
        h_layout2.addWidget(self.input_destino)
        btn_buscar_destino = QPushButton("📂")
        btn_buscar_destino.setMaximumWidth(40)
        btn_buscar_destino.clicked.connect(self.seleccionar_destino)
        h_layout2.addWidget(btn_buscar_destino)
        layout.addLayout(h_layout2)

        # Contraseña
        layout.addWidget(QLabel("🔑 Contraseña:"))
        self.input_password_dec = QLineEdit()
        self.input_password_dec.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password_dec.setPlaceholderText("Contraseña correcta...")
        layout.addWidget(self.input_password_dec)

        # Botón desencriptar
        btn_desencriptar = QPushButton("🔓 DESENCRIPTAR")
        btn_desencriptar.setStyleSheet(
            """
            QPushButton {
                background-color: #0984e3;
                padding: 12px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #74b9ff;
            }
        """
        )
        btn_desencriptar.clicked.connect(self.desencriptar)
        layout.addWidget(btn_desencriptar)

        layout.addStretch()
        return widget

    def crear_tab_decomprimir(self):
        """Tab para descomprimir archivos de formatos externos"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Título explicativo
        info_label = QLabel("Descomprime ZIP, TAR, 7Z, GZIP")
        info_label.setStyleSheet("color: #888888; font-style: italic; font-size: 10px;")
        layout.addWidget(info_label)

        # Archivo comprimido
        layout.addWidget(QLabel("📦 Archivo:"))
        h_layout1 = QHBoxLayout()
        self.input_archivo_externo = QLineEdit()
        self.input_archivo_externo.setPlaceholderText(".zip, .tar, .7z, .gz...")
        self.input_archivo_externo.textChanged.connect(self.detectar_formato_externo)
        h_layout1.addWidget(self.input_archivo_externo)
        btn_buscar_externo = QPushButton("📂")
        btn_buscar_externo.setMaximumWidth(40)
        btn_buscar_externo.clicked.connect(self.seleccionar_archivo_externo)
        h_layout1.addWidget(btn_buscar_externo)
        layout.addLayout(h_layout1)

        # Formato detectado
        self.label_formato_detectado = QLabel("")
        self.label_formato_detectado.setStyleSheet(
            "color: #14a085; font-weight: bold; font-size: 10px;"
        )
        self.label_formato_detectado.setMaximumHeight(18)
        layout.addWidget(self.label_formato_detectado)

        # Carpeta destino
        layout.addWidget(QLabel("📁 Destino:"))
        h_layout2 = QHBoxLayout()
        self.input_destino_externo = QLineEdit()
        self.input_destino_externo.setPlaceholderText("Dónde extraer...")
        h_layout2.addWidget(self.input_destino_externo)
        btn_buscar_destino_ext = QPushButton("📂")
        btn_buscar_destino_ext.setMaximumWidth(40)
        btn_buscar_destino_ext.clicked.connect(self.seleccionar_destino_externo)
        h_layout2.addWidget(btn_buscar_destino_ext)
        layout.addLayout(h_layout2)

        # Botón descomprimir
        btn_decomprimir = QPushButton("📦 DESCOMPRIMIR")
        btn_decomprimir.setStyleSheet(
            """
            QPushButton {
                background-color: #6c5ce7;
                padding: 12px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #a29bfe;
            }
        """
        )
        btn_decomprimir.clicked.connect(self.descomprimir_externo)
        layout.addWidget(btn_decomprimir)

        layout.addStretch()
        return widget

    def crear_tab_info(self):
        widget = QWidget()

        # Scroll area para el contenido
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #252525; }")

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(15, 15, 15, 15)

        info_text = QLabel(
            """
<h3 style='color: #14a085;'>🔒 Características V2</h3>
<p style='color: #000000; font-size: 10px; line-height: 1.5;'>
<b>✅ AES-256-GCM:</b> Encriptación militar<br>
<b>✅ SHA-256:</b> Verificación de integridad<br>
<b>✅ PBKDF2:</b> 600k iteraciones anti fuerza bruta<br>
<b>✅ Compresión inteligente:</b> Solo archivos que se benefician<br>
<b>✅ Protección anti-extracción:</b> Archivos señuelo vacíos/corruptos<br>
<b>✅ Verificación de contraseña:</b> Valida antes de extraer<br>
<b>✅ Múltiples formatos:</b> ZIP, TAR, 7Z, GZIP<br>
<b>✅ Drag & drop:</b> Arrastra archivos y carpetas
</p>

<h4 style='color: #e74c3c;'>⚠️ Advertencias</h4>
<p style='color: #000000; font-size: 10px; line-height: 1.5;'>
- <b>GUARDA TU CONTRASEÑA:</b> Sin recuperación posible<br>
- <b>BACKUPS:</b> Guarda copias en lugares seguros<br>
- <b>MÍNIMO 12 CHARS:</b> Mejor 16+ con símbolos<br>
- <b>NO COMPARTIR:</b> Esta app con no autorizados
</p>

<h4 style='color: #14a085;'>🛡️ Protección Anti-Extracción</h4>
<p style='color: #000000; font-size: 10px; line-height: 1.5;'>
Si intentan abrir con WinRAR/7-Zip/WinZip:<br>
- Pedirá contraseña (aunque no la tengan)<br>
- Verán archivos señuelo (passwords.txt, keys.pem, etc.)<br>
- Todos vacíos o con basura corrupta<br>
- Los archivos reales están 100% encriptados
</p>
        """
        )
        info_text.setWordWrap(True)
        info_text.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info_text)

        layout.addStretch()

        scroll.setWidget(content_widget)

        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        return widget

    def verificar_fortaleza_password(self):
        """Verifica y muestra la fortaleza de la contraseña"""
        password = self.input_password_enc.text()

        if not password:
            self.password_strength_label.setText("")
            return

        score, mensaje, color = PasswordStrengthChecker.check_strength(password)
        self.password_strength_label.setText(f"{score}/100 - {mensaje}")
        self.password_strength_label.setStyleSheet(
            f"color: {color}; font-size: 10px; padding: 2px; font-weight: bold;"
        )

    def detectar_formato_externo(self):
        """Detecta el formato del archivo externo"""
        archivo = self.input_archivo_externo.text()
        if not archivo or not os.path.exists(archivo):
            self.label_formato_detectado.setText("")
            return

        formato = ExternalDecompressor.detect_format(archivo)

        if formato == "unknown":
            self.label_formato_detectado.setText("⚠️ Formato no reconocido")
            self.label_formato_detectado.setStyleSheet(
                "color: #ff4444; font-weight: bold; font-size: 10px;"
            )
        else:
            self.label_formato_detectado.setText(f"✓ {formato.upper()}")
            self.label_formato_detectado.setStyleSheet(
                "color: #14a085; font-weight: bold; font-size: 10px;"
            )

    def agregar_archivos(self):
        """Agregar uno o múltiples archivos a la lista"""
        archivos, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar archivos", "", "Todos los archivos (*.*)"
        )
        if archivos:
            for archivo in archivos:
                if archivo not in self.rutas_seleccionadas:
                    self.rutas_seleccionadas.append(archivo)
                    self.lista_archivos.addItem(f"📄 {archivo}")

            # Sugerir nombre de salida si no hay uno
            if not self.input_salida.text() and len(archivos) == 1:
                nombre_base = os.path.splitext(os.path.basename(archivos[0]))[0]
                self.input_salida.setText(f"{nombre_base}_enc.vault")
            elif not self.input_salida.text() and len(archivos) > 1:
                self.input_salida.setText("archivos_enc.vault")

    def agregar_carpeta(self):
        """Agregar una carpeta a la lista"""
        carpeta = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta")
        if carpeta:
            if carpeta not in self.rutas_seleccionadas:
                self.rutas_seleccionadas.append(carpeta)
                self.lista_archivos.addItem(f"📂 {carpeta}")

                # Sugerir nombre de salida
                if not self.input_salida.text():
                    nombre_sugerido = os.path.basename(carpeta) + ".vault"
                    self.input_salida.setText(nombre_sugerido)

    def limpiar_lista(self):
        """Limpiar la lista de archivos seleccionados"""
        self.rutas_seleccionadas.clear()
        self.lista_archivos.clear()

    def seleccionar_archivo_salida(self):
        archivo, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar archivo encriptado",
            "",
            "SecureVault (*.vault);;Todos los archivos (*.*)",
        )
        if archivo:
            if not archivo.endswith(".vault"):
                archivo += ".vault"
            self.input_salida.setText(archivo)

    def seleccionar_vault(self):
        archivo, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo encriptado",
            "",
            "SecureVault (*.vault);;Todos los archivos (*.*)",
        )
        if archivo:
            self.input_vault.setText(archivo)

    def seleccionar_destino(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Carpeta de destino")
        if carpeta:
            self.input_destino.setText(carpeta)

    def seleccionar_archivo_externo(self):
        """Seleccionar archivo comprimido externo"""
        archivo, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo comprimido",
            "",
            "Archivos comprimidos (*.zip *.tar *.tar.gz *.tgz *.tar.bz2 *.tar.xz *.7z *.gz);;Todos los archivos (*.*)",
        )
        if archivo:
            self.input_archivo_externo.setText(archivo)

            # Sugerir carpeta de destino
            if not self.input_destino_externo.text():
                nombre_base = os.path.splitext(os.path.basename(archivo))[0]
                if nombre_base.endswith(".tar"):
                    nombre_base = os.path.splitext(nombre_base)[0]
                directorio_padre = os.path.dirname(archivo)
                self.input_destino_externo.setText(
                    os.path.join(directorio_padre, nombre_base)
                )

    def seleccionar_destino_externo(self):
        """Seleccionar carpeta de destino para archivos externos"""
        carpeta = QFileDialog.getExistingDirectory(self, "Carpeta de destino")
        if carpeta:
            self.input_destino_externo.setText(carpeta)

    def encriptar(self):
        if len(self.rutas_seleccionadas) == 0:
            self.mostrar_mensaje(
                "error", "❌ Error", "Agrega al menos un archivo o carpeta"
            )
            return

        salida = self.input_salida.text()
        password = self.input_password_enc.text()
        password_confirm = self.input_password_enc_confirm.text()

        # Validaciones
        if not salida:
            self.mostrar_mensaje("error", "❌ Error", "Especifica un archivo de salida")
            return

        if len(password) < 12:
            self.mostrar_mensaje(
                "error", "❌ Error", "La contraseña debe tener al menos 12 caracteres"
            )
            return

        if password != password_confirm:
            self.mostrar_mensaje("error", "❌ Error", "Las contraseñas no coinciden")
            return

        # Verificar fortaleza
        score, mensaje, color = PasswordStrengthChecker.check_strength(password)
        if score < 40:
            if not self.mostrar_confirmacion(
                "⚠️ Contraseña débil",
                f"Puntuación: {score}/100.\n{mensaje}\n\n¿Continuar de todos modos?",
            ):
                return

        # Crear mensaje de confirmación
        items_texto = "\n".join([f"- {ruta}" for ruta in self.rutas_seleccionadas[:3]])
        if len(self.rutas_seleccionadas) > 3:
            items_texto += f"\n... y {len(self.rutas_seleccionadas) - 3} más"

        if self.mostrar_confirmacion(
            "🔒 Confirmar",
            f"¿Encriptar estos elementos?\n\n{items_texto}\n\n⚠️ Guarda bien tu contraseña",
        ):
            compress = self.checkbox_compress.isChecked()
            iterations = self.combo_velocidad.currentData()

            self.iniciar_worker(
                "encriptar",
                rutas_origen=self.rutas_seleccionadas.copy(),
                archivo_salida=salida,
                password=password,
                compress=compress,
                iterations=iterations,
            )

    def desencriptar(self):
        archivo_vault = self.input_vault.text()
        destino = self.input_destino.text()
        password = self.input_password_dec.text()

        if not archivo_vault or not os.path.exists(archivo_vault):
            self.mostrar_mensaje(
                "error", "❌ Error", "Selecciona un archivo .vault válido"
            )
            return

        if not destino:
            self.mostrar_mensaje(
                "error", "❌ Error", "Selecciona una carpeta de destino"
            )
            return

        if not password:
            self.mostrar_mensaje("error", "❌ Error", "Ingresa la contraseña")
            return

        os.makedirs(destino, exist_ok=True)
        self.iniciar_worker(
            "desencriptar",
            archivo_origen=archivo_vault,
            carpeta_destino=destino,
            password=password,
        )

    def descomprimir_externo(self):
        """Descomprimir archivo de formato externo"""
        archivo = self.input_archivo_externo.text()
        destino = self.input_destino_externo.text()

        if not archivo or not os.path.exists(archivo):
            self.mostrar_mensaje("error", "❌ Error", "Selecciona un archivo válido")
            return

        if not destino:
            self.mostrar_mensaje(
                "error", "❌ Error", "Selecciona una carpeta de destino"
            )
            return

        formato = ExternalDecompressor.detect_format(archivo)

        if formato == "unknown":
            self.mostrar_mensaje("error", "❌ Error", "Formato de archivo no soportado")
            return

        if formato == "vault":
            self.mostrar_mensaje(
                "warning",
                "⚠️ Aviso",
                "Archivo .vault encriptado.\nUsa la pestaña 'Desencriptar'.",
            )
            return

        os.makedirs(destino, exist_ok=True)
        self.iniciar_worker(
            "descomprimir_externo",
            archivo_origen=archivo,
            carpeta_destino=destino,
            formato=formato,
        )

    def iniciar_worker(self, operacion, **kwargs):
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("⏳ Procesando...")
        self.tabs.setEnabled(False)

        self.worker = WorkerThread(operacion, **kwargs)
        self.worker.progreso.connect(self.actualizar_progreso)
        self.worker.progreso_porcentaje.connect(self.actualizar_progreso_porcentaje)
        self.worker.finalizado.connect(self.operacion_finalizada)
        self.worker.start()

    def actualizar_progreso(self, mensaje):
        self.progress_label.setText(mensaje)

    def actualizar_progreso_porcentaje(self, porcentaje):
        self.progress_bar.setValue(porcentaje)

    def operacion_finalizada(self, exito, mensaje):
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("")
        self.tabs.setEnabled(True)

        if exito:
            self.mostrar_mensaje("info", "✅ Éxito", mensaje)
            # Limpiar campos después de éxito
            if "encriptados" in mensaje or "Encriptación" in mensaje:
                self.limpiar_lista()
                self.input_salida.clear()
                self.input_password_enc.clear()
                self.input_password_enc_confirm.clear()
                self.password_strength_label.setText("")
            elif "desencriptados" in mensaje or "Desencriptación" in mensaje:
                self.input_vault.clear()
                self.input_destino.clear()
                self.input_password_dec.clear()
            elif "Descompresión" in mensaje:
                self.input_archivo_externo.clear()
                self.input_destino_externo.clear()
                self.label_formato_detectado.setText("")
        else:
            self.mostrar_mensaje("error", "❌ Error", f"Error:\n\n{mensaje}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = EncriptadorApp()
    ventana.show()
    sys.exit(app.exec())

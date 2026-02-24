import json
import hashlib
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag
import zlib


class SecureEncryptor:
    MAGIC_HEADER_V2 = b"SECVAULT_V2"
    MAGIC_HEADER_V1 = b"SECVAULT_V1"

    SALT_SIZE = 32
    IV_SIZE = 16
    TAG_SIZE = 16
    KEY_SIZE = 32  # AES-256
    HASH_SIZE = 32  # SHA-256 (solo V2)

    DEFAULT_ITERATIONS = 600000  # V2
    V1_ITERATIONS = 600000  # en tu código V1 usa DEFAULT_ITERATIONS fijo

    @staticmethod
    def derive_key(password: str, salt: bytes, iterations: int) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=SecureEncryptor.KEY_SIZE,
            salt=salt,
            iterations=iterations,
            backend=default_backend(),
        )
        return kdf.derive(password.encode("utf-8"))

    @staticmethod
    def decompress_data(data: bytes) -> bytes:
        return zlib.decompress(data)

    @staticmethod
    def decrypt_file(input_path: str, output_path: str, password: str) -> str:
        input_path = str(input_path)
        output_path = str(output_path)

        with open(input_path, "rb") as f:
            header = f.read(len(SecureEncryptor.MAGIC_HEADER_V2))  # 11 bytes

            if header == SecureEncryptor.MAGIC_HEADER_V1:
                return SecureEncryptor._decrypt_file_v1(f, output_path, password)

            if header != SecureEncryptor.MAGIC_HEADER_V2:
                raise ValueError(f"Header inválido: {header!r}")

            # ---- V2 ----
            salt = f.read(SecureEncryptor.SALT_SIZE)
            iv = f.read(SecureEncryptor.IV_SIZE)
            tag = f.read(SecureEncryptor.TAG_SIZE)
            original_hash = f.read(SecureEncryptor.HASH_SIZE)
            metadata_len = int.from_bytes(f.read(4), "big")
            metadata_bytes = f.read(metadata_len)
            ciphertext = f.read()

        metadata = json.loads(metadata_bytes.decode("utf-8"))
        iterations = metadata.get("iterations", SecureEncryptor.DEFAULT_ITERATIONS)

        key = SecureEncryptor.derive_key(password, salt, iterations)

        cipher = Cipher(
            algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend()
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        if metadata.get("compressed"):
            plaintext = SecureEncryptor.decompress_data(plaintext)

        calc = hashlib.sha256(plaintext).digest()
        if calc != original_hash:
            raise ValueError("Hash no coincide (archivo corrupto o modificado)")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(plaintext)
        return metadata.get("filename", Path(output_path).name)

    @staticmethod
    def _decrypt_file_v1(f, output_path: str, password: str) -> str:
        # ---- V1 ---- (sin hash original)
        salt = f.read(SecureEncryptor.SALT_SIZE)
        iv = f.read(SecureEncryptor.IV_SIZE)
        tag = f.read(SecureEncryptor.TAG_SIZE)
        metadata_len = int.from_bytes(f.read(4), "big")
        metadata_bytes = f.read(metadata_len)
        ciphertext = f.read()

        metadata = json.loads(metadata_bytes.decode("utf-8"))
        iterations = SecureEncryptor.V1_ITERATIONS  # tu código V1 lo fija así

        key = SecureEncryptor.derive_key(password, salt, iterations)

        cipher = Cipher(
            algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend()
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        if metadata.get("compressed"):
            plaintext = SecureEncryptor.decompress_data(plaintext)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(plaintext)
        return metadata.get("filename", Path(output_path).name)


def try_passwords_on_index(
    index_secvault: Path, passwords: list[str]
) -> tuple[str | None, Path | None]:
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)

    for i, pw in enumerate(passwords, 1):
        pw = pw.strip()
        if not pw:
            continue
        out_path = out_dir / "index.json"

        try:
            name = SecureEncryptor.decrypt_file(str(index_secvault), str(out_path), pw)
            print(
                f"✅ Password #{i} OK -> decrypt({index_secvault.name}) => {out_path} (name={name})"
            )
            return pw, out_path
        except InvalidTag:
            print(f"❌ Password #{i} NO -> InvalidTag (contraseña incorrecta)")
        except Exception as e:
            print(f"❌ Password #{i} NO -> {type(e).__name__}: {e}")

    return None, None


def main():
    base = Path(".")
    f0 = base / "000000.secvault"
    f1 = base / "000001.secvault"

    if not f0.exists():
        raise SystemExit(
            "No existe 000000.secvault en esta carpeta. Ejecuta en vault_extract."
        )

    passwords = [
        r"WbWvfi7>$vQkOJ,fjKL]]W%n|FIJppv]",
        r"uqGMlQ<{s*gvPbBPqk;sx0B39Dd5TE-&",
    ]

    pw_ok, index_path = try_passwords_on_index(f0, passwords)
    if not pw_ok:
        print("\n👉 Ninguna contraseña abrió el índice. Posibles causas:")
        print("   - las contraseñas tienen un caracter extra (espacio/salto de línea)")
        print("   - el archivo no corresponde a esas contraseñas (otro vault/otro set)")
        print("   - falta(n) .secvault reales (extracción incompleta)")
        return

    # intenta leer el índice como JSON (si lo es)
    try:
        idx = json.loads(index_path.read_text("utf-8"))
        print("\n📄 Índice JSON leído OK. Keys:", list(idx.keys()))
    except Exception as e:
        print("\n⚠️ El index desencriptado NO parece JSON:", e)
        print("   Primeros bytes:", index_path.read_bytes()[:80])
        return

    # Si existe 000001.secvault, intenta desencriptarlo a partir del índice o directo
    if f1.exists():
        out_dir = Path("out")
        out_file = out_dir / "000001.decrypted.bin"
        try:
            name = SecureEncryptor.decrypt_file(str(f1), str(out_file), pw_ok)
            print(f"\n✅ decrypt(000001.secvault) OK => {out_file} (name={name})")
        except InvalidTag:
            print(
                "\n❌ 000001.secvault: InvalidTag (si abre índice pero no este, puede ser otra contraseña/capa)"
            )
        except Exception as e:
            print("\n❌ Error desencriptando 000001.secvault:", type(e).__name__, e)


if __name__ == "__main__":
    main()

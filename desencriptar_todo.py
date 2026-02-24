import json
from pathlib import Path
from cryptography.exceptions import InvalidTag

# Reusa la clase SecureEncryptor del probar_pass.py
from probar_pass import SecureEncryptor

PASSWORD = r"uqGMlQ<{s*gvPbBPqk;sx0B39Dd5TE-&"

BASE = Path(".")
INDEX_PATH = BASE / "out" / "index.json"
OUT_DIR = BASE / "out" / "files"


def main():
    if not INDEX_PATH.exists():
        raise SystemExit("No existe out/index.json. Corre primero probar_pass.py")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    index = json.loads(INDEX_PATH.read_text("utf-8"))
    files = index.get("files", [])
    total = len(files)

    ok = 0
    fail = 0

    for i, info in enumerate(files, 1):
        enc_name = info["encrypted_name"]  # ej: 000001.secvault
        original_path = info["original_path"]  # ej: docs/intro.txt
        enc_path = BASE / enc_name
        out_path = OUT_DIR / original_path

        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            real_name = SecureEncryptor.decrypt_file(
                str(enc_path), str(out_path), PASSWORD
            )
            print(f"✅ {i}/{total} {enc_name} -> {original_path} (name={real_name})")
            ok += 1
        except InvalidTag:
            print(
                f"❌ {i}/{total} {enc_name} -> InvalidTag (password incorrecta para este archivo o corrupto)"
            )
            fail += 1
        except FileNotFoundError:
            print(
                f"❌ {i}/{total} {enc_name} -> No existe en carpeta (te falta extraerlo del .vault)"
            )
            fail += 1
        except Exception as e:
            print(f"❌ {i}/{total} {enc_name} -> {type(e).__name__}: {e}")
            fail += 1

    print("\nResumen:")
    print("OK:", ok)
    print("FALLAS:", fail)
    print("Salida:", OUT_DIR)


if __name__ == "__main__":
    main()

import sqlite3
import json
import base64
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
KEY_DIR = BASE_DIR / "test_keys"


def load_private_key(private_key_path: Path):
    return serialization.load_pem_private_key(
        private_key_path.read_bytes(),
        password=None
    )


def hybrid_decrypt_with_private_key(private_key_path: Path, encrypted_blob_json: str) -> bytes:
    private_key = load_private_key(private_key_path)
    payload = json.loads(encrypted_blob_json)

    encrypted_key = base64.b64decode(payload["encrypted_key"].encode("utf-8"))
    nonce = base64.b64decode(payload["nonce"].encode("utf-8"))
    ciphertext = base64.b64decode(payload["ciphertext"].encode("utf-8"))

    aes_key = private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    aesgcm = AESGCM(aes_key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext


def main():
    package_id = input("package_id 입력: ").strip()
    private_key_filename = input("private key 파일명 입력 (예: beneficiary1_private.pem): ").strip()

    private_key_path = KEY_DIR / private_key_filename
    if not private_key_path.exists():
        print("[오류] private key 파일 없음")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT package_id, recipient_id, recipient_role, encrypted_package_blob
        FROM recovery_packages
        WHERE package_id = ?
    """, (package_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        print("[오류] package 없음")
        return

    plaintext = hybrid_decrypt_with_private_key(private_key_path, row["encrypted_package_blob"])

    print("\n=== 복호화 결과 ===")
    print("package_id:", row["package_id"])
    print("recipient_id:", row["recipient_id"])
    print("recipient_role:", row["recipient_role"])
    print("plaintext:", plaintext.decode("utf-8"))

    try:
        payload = json.loads(plaintext.decode("utf-8"))
        print("\n=== JSON 파싱 ===")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    except Exception:
        print("[경고] JSON 파싱 실패")


if __name__ == "__main__":
    main()
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


def decrypt_asset_file(storage_path: Path, dek_b64: str, nonce_b64: str) -> bytes:
    ciphertext = storage_path.read_bytes()
    dek = base64.b64decode(dek_b64.encode("utf-8"))
    nonce = base64.b64decode(nonce_b64.encode("utf-8"))

    aesgcm = AESGCM(dek)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext


def main():
    package_id = input("package_id 입력: ").strip()
    private_key_filename = input("beneficiary private key 파일명 입력 (예: beneficiary1_private.pem): ").strip()
    target_asset_id = input("복호화할 asset_id 입력: ").strip()

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
    package_row = cursor.fetchone()

    if not package_row:
        conn.close()
        print("[오류] package 없음")
        return

    # 1. package 복호화
    package_plaintext = hybrid_decrypt_with_private_key(
        private_key_path,
        package_row["encrypted_package_blob"]
    )
    package_payload = json.loads(package_plaintext.decode("utf-8"))

    print("\n=== package 복호화 성공 ===")
    print("package_id:", package_row["package_id"])
    print("recipient_id:", package_row["recipient_id"])

    vault_contents = package_payload.get("vault_contents")
    if not vault_contents:
        conn.close()
        print("[오류] package 안에 vault_contents 없음")
        return

    assets = vault_contents.get("assets", [])
    target_meta = None
    for item in assets:
        if item.get("asset_id") == target_asset_id:
            target_meta = item
            break

    if not target_meta:
        conn.close()
        print("[오류] package 안에 해당 asset_id 메타 없음")
        return

    # 2. assets 테이블에서 storage_path 조회
    cursor.execute("""
        SELECT asset_id, asset_name, storage_path, mime_type
        FROM assets
        WHERE asset_id = ?
    """, (target_asset_id,))
    asset_row = cursor.fetchone()
    conn.close()

    if not asset_row:
        print("[오류] assets 테이블에 해당 asset 없음")
        return

    storage_path = Path(asset_row["storage_path"])
    if not storage_path.exists():
        print("[오류] storage 파일 없음:", storage_path)
        return

    dek_b64 = target_meta["dek"]
    nonce_b64 = target_meta["nonce"]

    # 3. 실제 asset 파일 복호화
    asset_plaintext = decrypt_asset_file(storage_path, dek_b64, nonce_b64)

    print("\n=== asset 복호화 성공 ===")
    print("asset_id:", asset_row["asset_id"])
    print("asset_name:", asset_row["asset_name"])
    print("mime_type:", asset_row["mime_type"])
    print("storage_path:", asset_row["storage_path"])

    # mime_type 기반으로 확장자 결정 후 파일로 저장
    mime_to_ext = {
        "text/plain":                    ".txt",
        "application/pdf":               ".pdf",
        "application/msword":            ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "image/jpeg":                    ".jpg",
        "image/png":                     ".png",
        "video/mp4":                     ".mp4",
        "video/quicktime":               ".mov",
        "audio/mpeg":                    ".mp3",
    }

    mime = asset_row["mime_type"] or ""
    ext = mime_to_ext.get(mime, "")

    # 파일명 결정: asset_name에 이미 확장자 있으면 그대로, 없으면 추가
    asset_name = asset_row["asset_name"]
    if ext and not asset_name.endswith(ext):
        output_filename = f"recovered_{asset_name}{ext}"
    else:
        output_filename = f"recovered_{asset_name}"

    output_path = Path(output_filename)
    output_path.write_bytes(asset_plaintext)

    print("\n=== 복구 완료 ===")
    print("asset_id  :", asset_row["asset_id"])
    print("asset_name:", asset_row["asset_name"])
    print("mime_type :", mime or "(미지정)")
    print("저장 경로 :", output_path.resolve())
    print("파일 크기 :", len(asset_plaintext), "bytes")

    # credential(텍스트)은 내용도 바로 출력
    if mime.startswith("text/") or mime == "":
        try:
            print("\n=== 내용 ===")
            print(asset_plaintext.decode("utf-8"))
        except UnicodeDecodeError:
            pass


if __name__ == "__main__":
    main()
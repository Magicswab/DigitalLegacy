import json
import base64
from crypto.crypto_utils import encrypt_bytes, decrypt_bytes


def b64encode_bytes(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def b64decode_str(data: str) -> bytes:
    return base64.b64decode(data.encode("utf-8"))


def serialize_vault(vault_dict: dict) -> bytes:
    """
    vault dict -> JSON bytes
    """
    return json.dumps(vault_dict, ensure_ascii=False, indent=2).encode("utf-8")


def deserialize_vault(vault_bytes: bytes) -> dict:
    """
    JSON bytes -> dict
    """
    return json.loads(vault_bytes.decode("utf-8"))


def encrypt_vault(vault_dict: dict, mk: bytes) -> dict:
    """
    vault dict를 bytes로 직렬화 후 MK로 암호화
    반환:
    {
        "encrypted_blob": bytes,
        "nonce": bytes
    }
    """
    vault_bytes = serialize_vault(vault_dict)
    result = encrypt_bytes(vault_bytes, mk)

    return {
        "encrypted_blob": result["ciphertext"],
        "nonce": result["nonce"]
    }


def decrypt_vault(encrypted_blob: bytes, nonce: bytes, mk: bytes) -> dict:
    """
    암호화된 vault blob 복호화 -> dict 복원
    """
    vault_bytes = decrypt_bytes(encrypted_blob, nonce, mk)
    return deserialize_vault(vault_bytes)
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_dek() -> bytes:
    """
    256-bit DEK 생성
    """
    return AESGCM.generate_key(bit_length=256)


def encrypt_bytes(plaintext: bytes, dek: bytes) -> dict:
    """
    바이트 데이터를 AES-256-GCM으로 암호화
    반환:
    {
        "ciphertext": ...,
        "nonce": ...
    }
    """
    aesgcm = AESGCM(dek)
    nonce = os.urandom(12)  # GCM 권장 nonce 길이
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    return {
        "ciphertext": ciphertext,
        "nonce": nonce
    }


def decrypt_bytes(ciphertext: bytes, nonce: bytes, dek: bytes) -> bytes:
    """
    AES-256-GCM 복호화
    """
    aesgcm = AESGCM(dek)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext


def encrypt_text(text: str, dek: bytes) -> dict:
    """
    문자열 암호화
    """
    plaintext = text.encode("utf-8")
    return encrypt_bytes(plaintext, dek)


def decrypt_text(ciphertext: bytes, nonce: bytes, dek: bytes) -> str:
    """
    문자열 복호화
    """
    plaintext = decrypt_bytes(ciphertext, nonce, dek)
    return plaintext.decode("utf-8")


def encrypt_file(input_path: str, output_path: str, dek: bytes) -> dict:
    """
    파일 전체를 읽어서 암호화 후 output_path에 저장
    """
    with open(input_path, "rb") as f:
        plaintext = f.read()

    result = encrypt_bytes(plaintext, dek)

    with open(output_path, "wb") as f:
        f.write(result["ciphertext"])

    return {
        "nonce": result["nonce"],
        "ciphertext_size": len(result["ciphertext"])
    }


def decrypt_file(input_path: str, output_path: str, dek: bytes, nonce: bytes):
    """
    암호화된 파일을 복호화해서 output_path에 저장
    """
    with open(input_path, "rb") as f:
        ciphertext = f.read()

    plaintext = decrypt_bytes(ciphertext, nonce, dek)

    with open(output_path, "wb") as f:
        f.write(plaintext)
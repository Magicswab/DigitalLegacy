import os
import json
import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def load_public_key(pem_str: str):
    return serialization.load_pem_public_key(pem_str.encode("utf-8"))


def hybrid_encrypt_with_public_key(public_key_pem: str, plaintext: bytes) -> str:
    """
    하이브리드 암호화:
    1) 랜덤 AES key 생성
    2) plaintext를 AES-GCM으로 암호화
    3) AES key를 RSA-OAEP로 암호화
    4) JSON(base64 인코딩) 문자열 반환
    """
    public_key = load_public_key(public_key_pem)

    # 1. AES key 생성
    aes_key = AESGCM.generate_key(bit_length=256)
    aesgcm = AESGCM(aes_key)

    # 2. AES-GCM 암호화
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    # 3. AES key를 RSA 공개키로 암호화
    encrypted_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    # 4. JSON payload로 묶어서 반환
    payload = {
        "alg": "RSA-OAEP + AES-256-GCM",
        "encrypted_key": base64.b64encode(encrypted_key).decode("utf-8"),
        "nonce": base64.b64encode(nonce).decode("utf-8"),
        "ciphertext": base64.b64encode(ciphertext).decode("utf-8")
    }

    return json.dumps(payload, ensure_ascii=False)
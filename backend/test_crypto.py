from crypto.crypto_utils import (
    generate_dek,
    encrypt_text,
    decrypt_text
)
from crypto.vault_utils import (
    encrypt_vault,
    decrypt_vault
)


def main():
    print("=== 암호 모듈 테스트 시작 ===")

    # 1. DEK/MK 생성
    dek = generate_dek()
    mk = generate_dek()

    print(f"DEK 길이: {len(dek)} bytes")
    print(f"MK 길이: {len(mk)} bytes")

    # 2. 텍스트 암복호화 테스트
    sample_text = "이것은 테스트용 credential 메모입니다."
    enc_result = encrypt_text(sample_text, dek)
    dec_text = decrypt_text(
        enc_result["ciphertext"],
        enc_result["nonce"],
        dek
    )

    print("\n[텍스트 암복호화]")
    print("원문:", sample_text)
    print("복호화:", dec_text)

    # 3. vault 암복호화 테스트
    vault_dict = {
        "vault_version": 1,
        "assets": [
            {
                "asset_id": "asset_001",
                "dek": "dummy_wrapped_dek_001",
                "algorithm": "AES-256-GCM",
                "nonce": "dummy_nonce_001",
                "chunked": False,
                "chunk_size": None
            },
            {
                "asset_id": "asset_002",
                "dek": "dummy_wrapped_dek_002",
                "algorithm": "AES-256-GCM",
                "nonce": "dummy_nonce_002",
                "chunked": True,
                "chunk_size": 4194304
            }
        ]
    }

    vault_enc = encrypt_vault(vault_dict, mk)
    vault_dec = decrypt_vault(
        vault_enc["encrypted_blob"],
        vault_enc["nonce"],
        mk
    )

    print("\n[vault 암복호화]")
    print("원본 vault:", vault_dict)
    print("복원 vault:", vault_dec)

    print("\n=== 암호 모듈 테스트 완료 ===")


if __name__ == "__main__":
    main()
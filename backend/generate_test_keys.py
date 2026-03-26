from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
KEY_DIR = BASE_DIR / "test_keys"
KEY_DIR.mkdir(exist_ok=True)


USERS = [
    "owner1",
    "advisor1",
    "trustee1",
    "beneficiary1",
    "beneficiary2",
]


def main():
    for username in USERS:
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        public_key = private_key.public_key()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        (KEY_DIR / f"{username}_private.pem").write_bytes(private_pem)
        (KEY_DIR / f"{username}_public.pem").write_bytes(public_pem)

        print(f"[생성 완료] {username}")

    print(f"\n키 저장 위치: {KEY_DIR}")


if __name__ == "__main__":
    main()
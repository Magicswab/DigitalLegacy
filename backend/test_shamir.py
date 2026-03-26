from crypto.shamir_utils import generate_recovery_secret, split_secret, reconstruct_secret_bytes


def main():
    secret = generate_recovery_secret(32)
    print("원본 secret:", secret.hex())

    shares = split_secret(secret, threshold=3, num_shares=5)
    print("\n생성된 shares:")
    for s in shares:
        print(s)

    subset = shares[:3]
    recovered = reconstruct_secret_bytes(subset, original_length=32)

    print("\n복원 secret:", recovered.hex())
    print("일치 여부:", secret == recovered)


if __name__ == "__main__":
    main()
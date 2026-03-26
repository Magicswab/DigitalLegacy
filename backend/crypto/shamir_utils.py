import secrets
from typing import List, Tuple

# 큰 소수 (256비트보다 충분히 큰 prime)
PRIME = 2**521 - 1


def secret_bytes_to_int(secret_bytes: bytes) -> int:
    return int.from_bytes(secret_bytes, byteorder="big")


def secret_int_to_bytes(secret_int: int, length: int) -> bytes:
    return secret_int.to_bytes(length, byteorder="big")


def _eval_polynomial(coefficients: List[int], x: int, prime: int) -> int:
    """
    f(x) = a0 + a1*x + a2*x^2 + ...
    """
    result = 0
    power = 1
    for coeff in coefficients:
        result = (result + coeff * power) % prime
        power = (power * x) % prime
    return result


def split_secret(secret_bytes: bytes, threshold: int, num_shares: int, prime: int = PRIME) -> List[Tuple[int, int]]:
    """
    secret_bytes를 threshold-of-num_shares 방식으로 분할
    반환: [(x1, y1), (x2, y2), ...]
    """
    if threshold < 2:
        raise ValueError("threshold는 최소 2 이상이어야 함")
    if num_shares < threshold:
        raise ValueError("num_shares는 threshold 이상이어야 함")

    secret_int = secret_bytes_to_int(secret_bytes)

    if secret_int >= prime:
        raise ValueError("secret이 prime보다 커서 분할 불가")

    # 다항식 계수: a0 = secret, 나머지는 랜덤
    coefficients = [secret_int] + [secrets.randbelow(prime) for _ in range(threshold - 1)]

    shares = []
    for x in range(1, num_shares + 1):
        y = _eval_polynomial(coefficients, x, prime)
        shares.append((x, y))

    return shares


def _mod_inverse(a: int, prime: int) -> int:
    return pow(a, -1, prime)


def reconstruct_secret(shares: List[Tuple[int, int]], prime: int = PRIME) -> int:
    """
    라그랑주 보간으로 f(0) 복원
    입력: [(x1, y1), (x2, y2), ...]
    반환: secret_int
    """
    if len(shares) < 2:
        raise ValueError("복원을 위해 최소 2개 이상의 share 필요")

    secret = 0

    for j, (xj, yj) in enumerate(shares):
        numerator = 1
        denominator = 1

        for m, (xm, _) in enumerate(shares):
            if m != j:
                numerator = (numerator * (-xm)) % prime
                denominator = (denominator * (xj - xm)) % prime

        lagrange_coeff = numerator * _mod_inverse(denominator, prime)
        secret = (prime + secret + (yj * lagrange_coeff)) % prime

    return secret


def reconstruct_secret_bytes(shares: List[Tuple[int, int]], original_length: int, prime: int = PRIME) -> bytes:
    secret_int = reconstruct_secret(shares, prime)
    return secret_int_to_bytes(secret_int, original_length)


def generate_recovery_secret(length: int = 32) -> bytes:
    """
    recovery용 secret 생성 (기본 32 bytes)
    """
    return secrets.token_bytes(length)
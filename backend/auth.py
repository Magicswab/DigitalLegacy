import bcrypt
from models import get_user_by_username


def hash_password(plain: str) -> str:
    """비밀번호를 bcrypt로 해싱하여 문자열로 반환"""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """입력된 비밀번호와 저장된 해시를 비교"""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def authenticate_user(username, password):
    user = get_user_by_username(username)

    if not user:
        return None

    # bcrypt 해시 검증 (평문 비교 제거)
    if not verify_password(password, user["password_hash"]):
        return None

    return user
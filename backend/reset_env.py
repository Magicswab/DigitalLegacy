from pathlib import Path
import subprocess
import os

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
ASSET_DIR = BASE_DIR / "storage" / "assets"


def main():
    print("=== 환경 초기화 시작 ===")

    # 1. DB 삭제
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"[삭제] DB 파일: {DB_PATH}")
    else:
        print("[정보] DB 파일 없음")

    # 2. storage/assets 내부 파일 삭제
    if ASSET_DIR.exists():
        for item in ASSET_DIR.iterdir():
            if item.is_file():
                item.unlink()
                print(f"[삭제] asset 파일: {item.name}")
    else:
        ASSET_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[생성] asset 디렉터리: {ASSET_DIR}")

    # 3. DB 재생성
    print("[실행] init_db.py")
    result = subprocess.run(["python", "init_db.py"], cwd=BASE_DIR)

    if result.returncode != 0:
        print("[오류] init_db.py 실행 실패")
        return

    print("=== 환경 초기화 완료 ===")


if __name__ == "__main__":
    main()
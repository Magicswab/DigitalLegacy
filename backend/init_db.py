import os
import sqlite3
from pathlib import Path


def main():
    # 현재 파일(init_db.py)이 있는 폴더 기준
    base_dir = Path(__file__).resolve().parent

    db_path = base_dir / "app.db"
    schema_path = base_dir / "schema.sql"

    # schema.sql 파일 존재 확인
    if not schema_path.exists():
        print(f"[오류] schema.sql 파일을 찾을 수 없습니다: {schema_path}")
        return

    # SQLite DB 연결 (없으면 자동 생성)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys = ON;")

    try:
        # schema.sql 읽기
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        # SQL 전체 실행
        cursor.executescript(schema_sql)

        conn.commit()
        print("[성공] 데이터베이스 초기화 완료")
        print(f"[DB 파일 위치] {db_path}")

        # 생성된 테이블 목록 확인
        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name;
        """)
        tables = cursor.fetchall()

        print("\n[생성된 테이블 목록]")
        for table in tables:
            print(f" - {table[0]}")

    except sqlite3.Error as e:
        print(f"[SQLite 오류] {e}")
    except Exception as e:
        print(f"[일반 오류] {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
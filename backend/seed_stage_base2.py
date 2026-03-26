import sqlite3
from pathlib import Path
from datetime import datetime
import uuid
from crypto.crypto_utils import generate_dek

BASE_DIR = Path(__file__).resolve().parent
KEY_DIR = BASE_DIR / "test_keys"
DB_PATH = BASE_DIR / "app.db"

def read_public_key(filename: str) -> str:
    return (KEY_DIR / filename).read_text(encoding="utf-8")


def now():
    return datetime.utcnow().isoformat()


def main():
    if not DB_PATH.exists():
        print("[오류] app.db 없음. 먼저 reset_env.py 또는 init_db.py 실행 필요")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    current_time = now()

    try:
        print("=== base seed 시작 ===")

        # -------------------------
        # 1. users 생성
        # -------------------------
        users = [
    ("u_owner_1", "owner1", "1234", "Owner One", "owner", read_public_key("owner1_public.pem")),
    ("u_advisor_1", "advisor1", "1234", "Advisor One", "legal_advisor", read_public_key("advisor1_public.pem")),
    ("u_trustee_1", "trustee1", "1234", "Trustee One", "trustee", read_public_key("trustee1_public.pem")),
    ("u_beneficiary_1", "beneficiary1", "1234", "Beneficiary One", "beneficiary", read_public_key("beneficiary1_public.pem")),
    ("u_beneficiary_2", "beneficiary2", "1234", "Beneficiary Two", "beneficiary", read_public_key("beneficiary2_public.pem")),
]
        for user_id, username, password, display_name, role, public_key in users:
            cursor.execute("""
                INSERT OR REPLACE INTO users (
                    user_id, username, password_hash, display_name, role,
                    public_key, public_key_status, is_active, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                username,
                password,
                display_name,
                role,
                public_key,
                "active",
                1,
                current_time,
                current_time
            ))

        # -------------------------
        # 2. plan 생성
        # -------------------------
        plan_id = "plan_test_001"

        cursor.execute("""
            INSERT OR REPLACE INTO legacy_plans (
                plan_id, owner_id, title, description, status,
                share_threshold, share_total, created_at, updated_at, finalized_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plan_id,
            "u_owner_1",
            "Test Legacy Plan",
            "자동 테스트용 상속 계획",
            "drafting",
            3,
            5,
            current_time,
            current_time,
            None
        ))

        # -------------------------
        # 3. participant 연결
        # -------------------------
        participants = [
            ("pp_001", plan_id, "u_advisor_1", "legal_advisor"),
            ("pp_002", plan_id, "u_trustee_1", "trustee"),
            ("pp_003", plan_id, "u_beneficiary_1", "beneficiary"),
            ("pp_004", plan_id, "u_beneficiary_2", "beneficiary"),
        ]

        for participant_id, p_plan_id, user_id, participant_role in participants:
            cursor.execute("""
                INSERT OR REPLACE INTO plan_participants (
                    participant_id, plan_id, user_id, participant_role,
                    is_required, invited_at, accepted_at, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                participant_id,
                p_plan_id,
                user_id,
                participant_role,
                1,
                current_time,
                current_time,
                "accepted"
            ))

        # -------------------------
        # 4. system_state 생성
        # -------------------------
        cursor.execute("""
            INSERT OR REPLACE INTO system_state (
                state_id, plan_id, owner_id, current_state, last_activity_at,
                last_checkin_at, pending_started_at, escalated_at,
                inheritance_activated_at, recovered_at,
                inactivity_threshold_sec, grace_period_sec, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "state_test_001",
            plan_id,
            "u_owner_1",
            "active",
            current_time,
            current_time,
            None,
            None,
            None,
            None,
            300,
            120,
            current_time
        ))

        # -------------------------
        # 5. 개발용 MK 저장
        # -------------------------
        mk = generate_dek()

        cursor.execute("""
            INSERT OR REPLACE INTO plan_master_keys_temp (
                plan_id, mk_blob, created_at, updated_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            plan_id,
            mk,
            current_time,
            current_time
        ))

        conn.commit()

        print("=== base seed 완료 ===")
        print(f"plan_id = {plan_id}")
        print("owner_id = u_owner_1")
        print("advisor_id = u_advisor_1")
        print("trustee_id = u_trustee_1")
        print("beneficiary_ids = u_beneficiary_1, u_beneficiary_2")

    except Exception as e:
        conn.rollback()
        print(f"[오류] {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
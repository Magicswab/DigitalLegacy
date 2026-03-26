from database import get_db_connection
import time, threading
from datetime import datetime, timedelta, UTC
from pathlib import Path
from crypto.crypto_utils import generate_dek
import uuid
import json
import base64


def now():
    return datetime.utcnow().isoformat()


def create_user(username, password, display_name, role, public_key, already_hashed=False):
    conn = get_db_connection()
    cursor = conn.cursor()

    user_id = f"u_{uuid.uuid4().hex[:8]}"
    current_time = now()

    # bcrypt로 비밀번호 해싱 (already_hashed=True면 이미 해시된 값 그대로 사용)
    if already_hashed:
        password_hash = password
    else:
        import bcrypt as _bcrypt
        password_hash = _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")

    cursor.execute("""
        INSERT INTO users (
            user_id,
            username,
            password_hash,
            display_name,
            role,
            public_key,
            public_key_status,
            is_active,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        username,
        password_hash,         # bcrypt 해시 저장
        display_name,
        role,
        public_key,
        "active",
        1,
        current_time,
        current_time
    ))

    conn.commit()
    conn.close()

    return user_id


def get_user_by_username(username):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM users WHERE username = ?
    """, (username,))

    user = cursor.fetchone()
    conn.close()

    return user


def now():
    return datetime.utcnow().isoformat()


def create_plan(owner_id, title, description=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    plan_id = f"plan_{uuid.uuid4().hex[:8]}"
    current_time = now()

    cursor.execute("""
        INSERT INTO legacy_plans (
            plan_id, owner_id, title, description, status,
            share_threshold, share_total, created_at, updated_at, finalized_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        plan_id,
        owner_id,
        title,
        description,
        "drafting",
        3,
        5,
        current_time,
        current_time,
        None
    ))

    # plan 생성 시 기본 system_state도 같이 생성
    state_id = f"state_{uuid.uuid4().hex[:8]}"
    cursor.execute("""
        INSERT INTO system_state (
            state_id, plan_id, owner_id, current_state, last_activity_at,
            pending_started_at, escalated_at, inheritance_activated_at,
            inactivity_threshold_sec, grace_period_sec, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        state_id,
        plan_id,
        owner_id,
        "active",
        current_time,
        None,
        None,
        None,
        300,   # 데모용 5분
        120,   # 데모용 2분
        current_time
    ))

    conn.commit()
    conn.close()

        # 개발용 임시 MK 생성 및 저장
    mk = generate_dek()
    save_temp_mk(plan_id, mk)

    return plan_id


def get_plan_by_id(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM legacy_plans WHERE plan_id = ?
    """, (plan_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def add_participant(plan_id, user_id, participant_role, is_required=True):
    conn = get_db_connection()
    cursor = conn.cursor()

    participant_id = f"pp_{uuid.uuid4().hex[:8]}"
    current_time = now()

    cursor.execute("""
        INSERT INTO plan_participants (
            participant_id, plan_id, user_id, participant_role,
            is_required, invited_at, accepted_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        participant_id,
        plan_id,
        user_id,
        participant_role,
        1 if is_required else 0,
        current_time,
        current_time,
        "accepted"
    ))

    conn.commit()
    conn.close()

    return participant_id


def get_participants_by_plan(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT participant_id, plan_id, user_id, participant_role, status
        FROM plan_participants
        WHERE plan_id = ?
        ORDER BY participant_role, user_id
    """, (plan_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_state_by_plan(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM system_state WHERE plan_id = ?
    """, (plan_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM users WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def b64d(data: str) -> bytes:
    return base64.b64decode(data.encode("utf-8"))


def get_key_vault_by_plan(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM key_vault WHERE plan_id = ?
    """, (plan_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def insert_asset(
    asset_id,
    plan_id,
    owner_id,
    asset_name,
    asset_type,
    mime_type,
    storage_path,
    original_size,
    encrypted_size,
    file_hash,
):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    cursor.execute("""
        INSERT INTO assets (
            asset_id, plan_id, owner_id, asset_name, asset_type,
            mime_type, storage_path, original_size, encrypted_size,
            file_hash, created_at, updated_at, is_deleted
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        asset_id,
        plan_id,
        owner_id,
        asset_name,
        asset_type,
        mime_type,
        storage_path,
        original_size,
        encrypted_size,
        file_hash,
        current_time,
        current_time,
        0
    ))

    conn.commit()
    conn.close()


def upsert_key_vault(plan_id, owner_id, encrypted_vault_blob, vault_version=1, mk_version=1):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    existing = get_key_vault_by_plan(plan_id)

    if existing:
        cursor.execute("""
            UPDATE key_vault
            SET encrypted_vault_blob = ?, vault_version = ?, mk_version = ?, updated_at = ?
            WHERE plan_id = ?
        """, (
            encrypted_vault_blob,
            vault_version,
            mk_version,
            current_time,
            plan_id
        ))
    else:
        vault_id = f"vault_{uuid.uuid4().hex[:8]}"
        cursor.execute("""
            INSERT INTO key_vault (
                vault_id, plan_id, owner_id, encrypted_vault_blob,
                vault_version, mk_version, updated_at, integrity_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vault_id,
            plan_id,
            owner_id,
            encrypted_vault_blob,
            vault_version,
            mk_version,
            current_time,
            None
        ))

    conn.commit()
    conn.close()


def save_temp_mk(plan_id, mk_blob):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    cursor.execute("""
        INSERT OR REPLACE INTO plan_master_keys_temp (
            plan_id, mk_blob, created_at, updated_at
        )
        VALUES (
            ?,
            ?,
            COALESCE((SELECT created_at FROM plan_master_keys_temp WHERE plan_id = ?), ?),
            ?
        )
    """, (
        plan_id,
        mk_blob,
        plan_id,
        current_time,
        current_time
    ))

    conn.commit()
    conn.close()


def get_temp_mk(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT mk_blob FROM plan_master_keys_temp
        WHERE plan_id = ?
    """, (plan_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return row["mk_blob"]


def get_key_vault_by_plan(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM key_vault WHERE plan_id = ?
    """, (plan_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def upsert_key_vault(plan_id, owner_id, encrypted_vault_blob, vault_nonce, vault_version=1, mk_version=1):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    cursor.execute("""
        SELECT vault_id FROM key_vault WHERE plan_id = ?
    """, (plan_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE key_vault
            SET encrypted_vault_blob = ?,
                vault_nonce = ?,
                vault_version = ?,
                mk_version = ?,
                updated_at = ?
            WHERE plan_id = ?
        """, (
            encrypted_vault_blob,
            vault_nonce,
            vault_version,
            mk_version,
            current_time,
            plan_id
        ))
    else:
        vault_id = f"vault_{uuid.uuid4().hex[:8]}"
        cursor.execute("""
            INSERT INTO key_vault (
                vault_id, plan_id, owner_id, encrypted_vault_blob,
                vault_nonce, vault_version, mk_version,
                updated_at, integrity_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vault_id,
            plan_id,
            owner_id,
            encrypted_vault_blob,
            vault_nonce,
            vault_version,
            mk_version,
            current_time,
            None
        ))

    conn.commit()
    conn.close()


def update_plan_status(plan_id, new_status):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    cursor.execute("""
        UPDATE legacy_plans
        SET status = ?, updated_at = ?, finalized_at = ?
        WHERE plan_id = ?
    """, (
        new_status,
        current_time,
        current_time,
        plan_id
    ))

    conn.commit()
    conn.close()


def get_required_participants(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM plan_participants
        WHERE plan_id = ? AND status = 'accepted'
        ORDER BY participant_role, user_id
    """, (plan_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def clear_assigned_shares(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM assigned_shares
        WHERE plan_id = ?
    """, (plan_id,))

    conn.commit()
    conn.close()


def insert_assigned_share(
    share_id,
    plan_id,
    recipient_id,
    recipient_role,
    encrypted_share_blob,
    share_index
):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    cursor.execute("""
        INSERT INTO assigned_shares (
            share_id, plan_id, recipient_id, recipient_role,
            encrypted_share_blob, share_index,
            issued_at, viewed_at, delivery_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        share_id,
        plan_id,
        recipient_id,
        recipient_role,
        encrypted_share_blob,
        share_index,
        current_time,
        None,
        "issued"
    ))

    conn.commit()
    conn.close()


def insert_audit_log(
    log_id,
    plan_id,
    actor_id,
    action_type,
    target_type,
    target_id,
    details_json,
    integrity_hash=None
):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    cursor.execute("""
        INSERT INTO audit_logs (
            log_id, plan_id, actor_id, action_type,
            target_type, target_id, occurred_at,
            details_json, integrity_hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        log_id,
        plan_id,
        actor_id,
        action_type,
        target_type,
        target_id,
        current_time,
        details_json,
        integrity_hash
    ))

    conn.commit()
    conn.close()


def get_assigned_shares_by_plan(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT share_id, plan_id, recipient_id, recipient_role,
               share_index, issued_at, viewed_at, delivery_status
        FROM assigned_shares
        WHERE plan_id = ?
        ORDER BY share_index
    """, (plan_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows


def activate_inheritance_state(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    # 실제 상태머신 갱신
    cursor.execute("""
        UPDATE system_state
        SET current_state = ?,
            inheritance_activated_at = ?,
            updated_at = ?
        WHERE plan_id = ?
    """, (
        "inheritance_activated",
        current_time,
        current_time,
        plan_id
    ))

    # plan의 큰 상태도 같이 갱신
    cursor.execute("""
        UPDATE legacy_plans
        SET status = ?,
            updated_at = ?
        WHERE plan_id = ?
    """, (
        "inheritance_ready",
        current_time,
        plan_id
    ))

    conn.commit()
    conn.close()
    

def get_participant_counts(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT participant_role, COUNT(*) as cnt
        FROM plan_participants
        WHERE plan_id = ? AND status = 'accepted'
        GROUP BY participant_role
    """, (plan_id,))

    rows = cursor.fetchall()
    conn.close()

    result = {
        "legal_advisor": 0,
        "trustee": 0,
        "beneficiary": 0
    }

    for row in rows:
        result[row["participant_role"]] = row["cnt"]

    return result


def get_participant_counts(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT participant_role, COUNT(*) as cnt
        FROM plan_participants
        WHERE plan_id = ? AND status = 'accepted'
        GROUP BY participant_role
    """, (plan_id,))

    rows = cursor.fetchall()
    conn.close()

    result = {
        "legal_advisor": 0,
        "trustee": 0,
        "beneficiary": 0
    }

    for row in rows:
        result[row["participant_role"]] = row["cnt"]

    return result


def update_plan_status(plan_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    cursor.execute("""
        UPDATE legacy_plans
        SET status = ?, updated_at = ?
        WHERE plan_id = ?
    """, (
        status,
        current_time,
        plan_id
    ))

    conn.commit()
    conn.close()


def get_assigned_shares_by_plan(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT share_id, plan_id, recipient_id, recipient_role, share_scope, encrypted_share_blob,
               share_index, issued_at, viewed_at, delivery_status
        FROM assigned_shares
        WHERE plan_id = ?
        ORDER BY share_index
    """, (plan_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_assigned_shares_by_plan(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM assigned_shares
        WHERE plan_id = ?
    """, (plan_id,))

    conn.commit()
    conn.close()


def create_audit_log(plan_id, actor_id, action_type, target_type, target_id, details_json=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    log_id = f"log_{uuid.uuid4().hex[:8]}"

    cursor.execute("""
        INSERT INTO audit_logs (
            log_id, plan_id, actor_id, action_type,
            target_type, target_id, occurred_at,
            details_json, integrity_hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        log_id,
        plan_id,
        actor_id,
        action_type,
        target_type,
        target_id,
        current_time,
        details_json,
        None
    ))

    conn.commit()
    conn.close()

    return log_id


def get_asset_by_id(asset_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM assets
        WHERE asset_id = ? AND is_deleted = 0
    """, (asset_id,))

    row = cursor.fetchone()
    conn.close()
    return row


def update_asset_record(asset_id, asset_name, mime_type, original_size, encrypted_size, file_hash):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    cursor.execute("""
        UPDATE assets
        SET asset_name = ?,
            mime_type = ?,
            original_size = ?,
            encrypted_size = ?,
            file_hash = ?,
            updated_at = ?
        WHERE asset_id = ?
    """, (
        asset_name,
        mime_type,
        original_size,
        encrypted_size,
        file_hash,
        current_time,
        asset_id
    ))

    conn.commit()
    conn.close()


def update_asset_record(asset_id, asset_name, mime_type, original_size, encrypted_size, file_hash):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    cursor.execute("""
        UPDATE assets
        SET asset_name = ?,
            mime_type = ?,
            original_size = ?,
            encrypted_size = ?,
            file_hash = ?,
            updated_at = ?
        WHERE asset_id = ?
    """, (
        asset_name,
        mime_type,
        original_size,
        encrypted_size,
        file_hash,
        current_time,
        asset_id
    ))

    conn.commit()
    conn.close()


def create_assigned_share(plan_id, recipient_id, recipient_role, share_scope, encrypted_share_blob, share_index):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        current_time = now()

        share_id = f"share_{uuid.uuid4().hex[:8]}"

        cursor.execute("""
            INSERT OR REPLACE INTO assigned_shares (
                share_id, plan_id, recipient_id, recipient_role,
                share_scope, encrypted_share_blob, share_index,
                issued_at, viewed_at, delivery_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            share_id,
            plan_id,
            recipient_id,
            recipient_role,
            share_scope,
            encrypted_share_blob,
            share_index,
            current_time,
            None,
            "issued"
        ))

        conn.commit()
        return share_id
    finally:
        conn.close()


def get_assigned_shares_by_plan_and_scope(plan_id, share_scope):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM assigned_shares
        WHERE plan_id = ?
          AND share_scope = ?
        ORDER BY share_index
    """, (plan_id, share_scope))

    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_assigned_shares_by_plan_and_scope(plan_id, share_scope):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM assigned_shares
            WHERE plan_id = ?
              AND share_scope = ?
        """, (plan_id, share_scope))
        conn.commit()
    finally:
        conn.close()


def is_legal_advisor_for_plan(plan_id, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 1
        FROM plan_participants
        WHERE plan_id = ?
          AND user_id = ?
          AND participant_role = 'legal_advisor'
          AND status = 'accepted'
        LIMIT 1
    """, (plan_id, user_id))

    row = cursor.fetchone()
    conn.close()

    return row is not None


def create_recovery_session(plan_id, threshold_required=3, trustee_required=True, beneficiary_required_count=2):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    recovery_id = f"recovery_{uuid.uuid4().hex[:8]}"

    cursor.execute("""
        INSERT INTO recovery_sessions (
            recovery_id, plan_id, status, threshold_required,
            trustee_required, beneficiary_required_count,
            created_at, expires_at, completed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        recovery_id,
        plan_id,
        "open",
        threshold_required,
        1 if trustee_required else 0,
        beneficiary_required_count,
        current_time,
        current_time,   # 지금은 TTL 단순화
        None
    ))

    conn.commit()
    conn.close()

    return recovery_id


def create_recovery_session(plan_id, threshold_required=3, trustee_required=True, beneficiary_required_count=2):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    recovery_id = f"recovery_{uuid.uuid4().hex[:8]}"

    cursor.execute("""
        INSERT INTO recovery_sessions (
            recovery_id, plan_id, status, threshold_required,
            trustee_required, beneficiary_required_count,
            created_at, expires_at, completed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        recovery_id,
        plan_id,
        "open",
        threshold_required,
        1 if trustee_required else 0,
        beneficiary_required_count,
        current_time,
        current_time,   # 지금은 TTL 단순화
        None
    ))

    conn.commit()
    conn.close()

    return recovery_id


def create_submitted_share(
    recovery_id,
    actor_id,
    actor_role,
    share_id,
    submitted_share_payload,
    is_valid=True,
    validation_note=None
):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        current_time = now()
        submission_id = f"submission_{uuid.uuid4().hex[:8]}"

        cursor.execute("""
            INSERT INTO submitted_shares (
                submission_id, recovery_id, actor_id, actor_role,
                share_id, submitted_share_payload, submitted_at, is_valid, validation_note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            submission_id,
            recovery_id,
            actor_id,
            actor_role,
            share_id,
            submitted_share_payload,
            current_time,
            1 if is_valid else 0,
            validation_note
        ))

        conn.commit()
        return submission_id
    finally:
        conn.close()


def get_submitted_shares_by_recovery(recovery_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT submission_id, recovery_id, actor_id, actor_role,
               share_id, submitted_share_payload,
               submitted_at, is_valid, validation_note
        FROM submitted_shares
        WHERE recovery_id = ?
        ORDER BY submitted_at
    """, (recovery_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows



def get_assigned_share_by_id(share_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM assigned_shares
        WHERE share_id = ?
    """, (share_id,))

    row = cursor.fetchone()
    conn.close()
    return row


def create_recovery_package(recovery_id, recipient_id, recipient_role, encrypted_package_blob):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    package_id = f"package_{uuid.uuid4().hex[:8]}"

    cursor.execute("""
        INSERT INTO recovery_packages (
            package_id, recovery_id, recipient_id, recipient_role,
            encrypted_package_blob, created_at, expires_at,
            delivered_at, package_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        package_id,
        recovery_id,
        recipient_id,
        recipient_role,
        encrypted_package_blob,
        current_time,
        current_time,
        None,
        "available"
    ))

    conn.commit()
    conn.close()

    return package_id


def get_recovery_packages_by_recovery(recovery_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM recovery_packages
        WHERE recovery_id = ?
        ORDER BY created_at
    """, (recovery_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows


def evaluate_recovery_threshold(recovery_id):
    recovery = get_recovery_session_by_id(recovery_id)
    if not recovery:
        return None

    submissions = get_submitted_shares_by_recovery(recovery_id)

    valid_submissions = [s for s in submissions if s["is_valid"] == 1]

    trustee_present = any(s["actor_role"] == "trustee" for s in valid_submissions)
    beneficiary_count = sum(1 for s in valid_submissions if s["actor_role"] == "beneficiary")
    valid_count = len(valid_submissions)

    success = (
        valid_count >= recovery["threshold_required"]
        and (not recovery["trustee_required"] or trustee_present)
        and beneficiary_count >= recovery["beneficiary_required_count"]
    )

    return {
        "valid_count": valid_count,
        "trustee_present": trustee_present,
        "beneficiary_count": beneficiary_count,
        "success": success
    }


def complete_recovery_session(recovery_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    cursor.execute("""
        UPDATE recovery_sessions
        SET status = ?, completed_at = ?
        WHERE recovery_id = ?
    """, (
        "completed",
        current_time,
        recovery_id
    ))

    conn.commit()
    conn.close()


def get_recovery_session_by_id(recovery_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM recovery_sessions
        WHERE recovery_id = ?
    """, (recovery_id,))

    row = cursor.fetchone()
    conn.close()
    return row


def save_recovery_secret(plan_id, recovery_secret_blob):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    cursor.execute("""
        INSERT OR REPLACE INTO plan_recovery_secrets_temp (
            plan_id, recovery_secret_blob, created_at, updated_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        plan_id,
        recovery_secret_blob,
        current_time,
        current_time
    ))

    conn.commit()
    conn.close()


def get_recovery_secret(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT recovery_secret_blob
        FROM plan_recovery_secrets_temp
        WHERE plan_id = ?
    """, (plan_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return row["recovery_secret_blob"]


def save_inheritance_key_material(plan_id, ik_key_blob, wrapped_mk_ik_blob, wrapped_mk_ik_nonce):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    cursor.execute("""
        INSERT OR REPLACE INTO plan_inheritance_keys_temp (
            plan_id, ik_key_blob, wrapped_mk_ik_blob, wrapped_mk_ik_nonce,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        plan_id,
        ik_key_blob,
        wrapped_mk_ik_blob,
        wrapped_mk_ik_nonce,
        current_time,
        current_time
    ))

    conn.commit()
    conn.close()


def get_inheritance_key_material(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM plan_inheritance_keys_temp
        WHERE plan_id = ?
    """, (plan_id,))

    row = cursor.fetchone()
    conn.close()
    return row



def save_operational_key_material(plan_id, ok_key_blob, wrapped_mk_ok_blob, wrapped_mk_ok_nonce):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = now()

    cursor.execute("""
        INSERT OR REPLACE INTO plan_operational_keys_temp (
            plan_id, ok_key_blob, wrapped_mk_ok_blob, wrapped_mk_ok_nonce,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        plan_id,
        ok_key_blob,
        wrapped_mk_ok_blob,
        wrapped_mk_ok_nonce,
        current_time,
        current_time
    ))

    conn.commit()
    conn.close()


def get_operational_key_material(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM plan_operational_keys_temp
        WHERE plan_id = ?
    """, (plan_id,))

    row = cursor.fetchone()
    conn.close()
    return row


def upsert_deadman_policy(plan_id, checkin_interval_days, grace_period_days, is_enabled):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        current_time = now()
        policy_id = f"policy_{uuid.uuid4().hex[:8]}"

        cursor.execute("""
            INSERT OR REPLACE INTO deadman_policies (
                policy_id, plan_id, checkin_interval_days,
                grace_period_days, is_enabled, created_at, updated_at
            )
            VALUES (
                COALESCE((SELECT policy_id FROM deadman_policies WHERE plan_id = ?), ?),
                ?, ?, ?, ?, ?, ?
            )
        """, (
            plan_id,
            policy_id,
            plan_id,
            checkin_interval_days,
            grace_period_days,
            1 if is_enabled else 0,
            current_time,
            current_time
        ))

        conn.commit()
    finally:
        conn.close()


def get_deadman_policy_by_plan(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM deadman_policies
        WHERE plan_id = ?
    """, (plan_id,))

    row = cursor.fetchone()
    conn.close()
    return row


def update_system_state(
    plan_id,
    current_state=None,
    last_checkin_at=None,
    pending_started_at=None,
    escalated_at=None,
    inheritance_activated_at=None,
    recovered_at=None
):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        current_time = now()

        existing = get_state_by_plan(plan_id)
        if not existing:
            raise ValueError("system_state 없음")

        cursor.execute("""
            UPDATE system_state
            SET current_state = ?,
                last_checkin_at = ?,
                pending_started_at = ?,
                escalated_at = ?,
                inheritance_activated_at = ?,
                recovered_at = ?,
                updated_at = ?
            WHERE plan_id = ?
        """, (
            current_state if current_state is not None else existing["current_state"],
            last_checkin_at if last_checkin_at is not None else existing["last_checkin_at"],
            pending_started_at if pending_started_at is not None else existing["pending_started_at"],
            escalated_at if escalated_at is not None else existing["escalated_at"],
            inheritance_activated_at if inheritance_activated_at is not None else existing["inheritance_activated_at"],
            recovered_at if recovered_at is not None else existing["recovered_at"],
            current_time,
            plan_id
        ))

        conn.commit()
    finally:
        conn.close()


def get_all_deadman_enabled_plans():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.plan_id, p.owner_id,
               d.checkin_interval_days, d.grace_period_days, d.is_enabled
        FROM legacy_plans p
        JOIN deadman_policies d ON p.plan_id = d.plan_id
        WHERE d.is_enabled = 1
    """)

    rows = cursor.fetchall()
    conn.close()
    return rows

def evaluate_state_logic(plan_id: str):
    state = get_state_by_plan(plan_id)
    if not state:
        return None

    policy = get_deadman_policy_by_plan(plan_id)
    if not policy or policy["is_enabled"] != 1:
        return None

    current_state = state["current_state"]

    if current_state in ["inheritance_activated", "recovered"]:
        return current_state

    now_dt = datetime.utcnow()

    last_checkin_raw = state["last_checkin_at"]
    if not last_checkin_raw:
        return current_state

    last_checkin_dt = datetime.fromisoformat(last_checkin_raw.replace("Z", "+00:00"))
    pending_deadline = last_checkin_dt + timedelta(days=policy["checkin_interval_days"])

    if current_state == "active":
        if now_dt > pending_deadline:
            update_system_state(
                plan_id=plan_id,
                current_state="pending_confirmation",
                pending_started_at=now()
            )

            plan = get_plan_by_id(plan_id)
            if plan:
                create_notification(
                    user_id=plan["owner_id"],
                    plan_id=plan_id,
                    notification_type="deadman_pending_confirmation",
                    message="장기간 check-in이 없어 pending_confirmation 상태로 전이되었습니다. 확인이 필요합니다."
                )

            return "pending_confirmation"
        return "active"

    if current_state == "pending_confirmation":
        pending_started_raw = state["pending_started_at"]
        if not pending_started_raw:
            return current_state

        pending_started_dt = datetime.fromisoformat(pending_started_raw.replace("Z", "+00:00"))
        escalated_deadline = pending_started_dt + timedelta(days=policy["grace_period_days"])

        if now_dt > escalated_deadline:
            update_system_state(
                plan_id=plan_id,
                current_state="escalated",
                escalated_at=now()
            )

            # escalated 진입 시 trustee 전원에게 승인 요청 알림 발송
            plan = get_plan_by_id(plan_id)
            if plan:
                participants = get_participants_by_plan(plan_id)
                for p in participants:
                    if p["participant_role"] == "trustee":
                        create_notification(
                            user_id=p["user_id"],
                            plan_id=plan_id,
                            notification_type="inheritance_approval_request",
                            message="상속 승인 요청이 있습니다. 검토 후 승인해주세요."
                        )

            return "escalated"

    return current_state


def scheduler_loop():
    while True:
        try:
            plans = get_all_deadman_enabled_plans()
            for plan in plans:
                evaluate_state_logic(plan["plan_id"])
        except Exception as e:
            print(f"[scheduler 오류] {e}")

        time.sleep(60)


def get_plans_by_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.plan_id, p.owner_id, p.title, p.description, p.status,
               p.share_threshold, p.share_total,
               p.created_at, p.updated_at, p.finalized_at
        FROM legacy_plans p
        LEFT JOIN plan_participants pp ON p.plan_id = pp.plan_id
        WHERE p.owner_id = ?
           OR pp.user_id = ?
        GROUP BY p.plan_id
        ORDER BY p.created_at DESC
    """, (user_id, user_id))

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_assets_by_plan(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT asset_id, plan_id, owner_id, asset_name, asset_type,
               mime_type, storage_path, original_size, encrypted_size,
               file_hash, is_deleted, created_at, updated_at
        FROM assets
        WHERE plan_id = ?
          AND is_deleted = 0
        ORDER BY created_at DESC
    """, (plan_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_assigned_shares_by_recipient(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT share_id, plan_id, recipient_id, recipient_role,
               share_scope, share_index,
               issued_at, viewed_at, delivery_status
        FROM assigned_shares
        WHERE recipient_id = ?
        ORDER BY issued_at DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_packages_by_recipient(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT rp.package_id, rp.recovery_id, rp.recipient_id, rp.recipient_role,
               rp.created_at, rp.expires_at, rp.delivered_at, rp.package_status,
               rp.encrypted_package_blob,
               rs.plan_id
        FROM recovery_packages rp
        LEFT JOIN recovery_sessions rs ON rp.recovery_id = rs.recovery_id
        WHERE rp.recipient_id = ?
        ORDER BY rp.created_at DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows


def create_notification(user_id, plan_id, notification_type, message):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        notification_id = f"notif_{uuid.uuid4().hex[:8]}"
        current_time = now()

        cursor.execute("""
            INSERT INTO notifications (
                notification_id, user_id, plan_id, notification_type,
                message, is_read, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            notification_id,
            user_id,
            plan_id,
            notification_type,
            message,
            0,
            current_time
        ))

        conn.commit()
        return notification_id
    finally:
        conn.close()



def get_notifications_by_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT notification_id, user_id, plan_id, notification_type,
               message, is_read, created_at
        FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows


def mark_notification_as_read(notification_id, user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE notifications
            SET is_read = 1
            WHERE notification_id = ?
              AND user_id = ?
        """, (notification_id, user_id))

        conn.commit()
    finally:
        conn.close()


def create_state_transition_approval(plan_id, requested_transition, approver_id, approver_role, approval_status="approved"):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        approval_id = f"approval_{uuid.uuid4().hex[:8]}"
        current_time = now()

        cursor.execute("""
            INSERT OR REPLACE INTO state_transition_approvals (
                approval_id, plan_id, requested_transition,
                approver_id, approver_role, approval_status, created_at
            )
            VALUES (
                COALESCE(
                    (SELECT approval_id
                     FROM state_transition_approvals
                     WHERE plan_id = ?
                       AND requested_transition = ?
                       AND approver_id = ?),
                    ?
                ),
                ?, ?, ?, ?, ?, ?
            )
        """, (
            plan_id,
            requested_transition,
            approver_id,
            approval_id,
            plan_id,
            requested_transition,
            approver_id,
            approver_role,
            approval_status,
            current_time
        ))

        conn.commit()
    finally:
        conn.close()


def get_recovery_sessions_by_plan(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM recovery_sessions
        WHERE plan_id = ?
        ORDER BY created_at DESC
    """, (plan_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_approvals_by_plan_and_transition(plan_id, requested_transition):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM state_transition_approvals
        WHERE plan_id = ?
          AND requested_transition = ?
          AND approval_status = 'approved'
        ORDER BY created_at DESC
    """, (plan_id, requested_transition))

    rows = cursor.fetchall()
    conn.close()
    return rows
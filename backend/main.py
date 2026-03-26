from fastapi import FastAPI, HTTPException
import time, threading
from datetime import datetime, timedelta, UTC
from schemas import (
    RegisterRequest,
    LoginRequest,
    CreatePlanRequest,
    AddParticipantRequest,
    FinalizePlanRequest
)
from models import (
    create_user,
    get_user_by_username,
    get_user_by_id,
    create_plan,
    get_plan_by_id,
    add_participant,
    get_participants_by_plan,
    get_state_by_plan,
    insert_asset,
    get_key_vault_by_plan,
    upsert_key_vault,
    save_temp_mk,
    get_temp_mk,
    update_plan_status,
    get_required_participants,
    clear_assigned_shares,
    insert_assigned_share,
    insert_audit_log,
    get_assigned_shares_by_plan,
    activate_inheritance_state,
    get_participant_counts,
    delete_assigned_shares_by_plan_and_scope,
    create_audit_log,
    get_asset_by_id,
    update_asset_record,
    is_legal_advisor_for_plan,
    create_assigned_share,
    create_recovery_session,
    get_recovery_session_by_id,
    create_submitted_share,
    get_submitted_shares_by_recovery,
    get_assigned_share_by_id,
    create_recovery_package,
    get_recovery_packages_by_recovery,
    evaluate_recovery_threshold,
    complete_recovery_session,
    save_recovery_secret,
    get_recovery_secret,
    get_inheritance_key_material,
    save_inheritance_key_material,
    save_operational_key_material,
    get_operational_key_material,
    upsert_deadman_policy,
    get_deadman_policy_by_plan,
    update_system_state,
    now,
    evaluate_state_logic,
    scheduler_loop,
    get_plans_by_user,
    get_assets_by_plan,
    get_assigned_shares_by_recipient,
    get_packages_by_recipient,
    create_notification,
    get_notifications_by_user,
    mark_notification_as_read,
    create_state_transition_approval,
    get_approvals_by_plan_and_transition,
    get_recovery_sessions_by_plan
)
from auth import authenticate_user

from schemas import CreateAssetRequest

from schemas import FinalizePlanRequest, UpdateAssetRequest

from schemas import CreateRecoverySessionRequest, SubmitShareRequest

from schemas import DeadmanPolicyRequest, CheckinRequest

from schemas import TrusteeApprovalRequest, NotificationReadRequest

from crypto.crypto_utils import generate_dek, encrypt_text
from crypto.vault_utils import encrypt_vault, decrypt_vault
from crypto.shamir_utils import generate_recovery_secret, split_secret, reconstruct_secret_bytes
from crypto.crypto_utils import encrypt_bytes, decrypt_bytes
from crypto.public_key_utils import hybrid_encrypt_with_public_key
from storage_utils import make_asset_storage_path
import uuid, hashlib, json, base64

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Digital Legacy Backend Running"}


# ---------------------------
# 회원가입
# ---------------------------
@app.post("/register")
def register(req: RegisterRequest):
    existing = get_user_by_username(req.username)

    if existing:
        raise HTTPException(status_code=400, detail="이미 존재하는 사용자")

    user_id = create_user(
        req.username,
        req.password,
        req.display_name,
        req.role,
        req.public_key
    )

    return {
        "message": "회원가입 성공",
        "user_id": user_id
    }


# ---------------------------
# 로그인
# ---------------------------
@app.post("/login")
def login(req: LoginRequest):
    user = authenticate_user(req.username, req.password)

    if not user:
        raise HTTPException(status_code=401, detail="로그인 실패")

    return {
        "message": "로그인 성공",
        "user_id": user["user_id"],
        "role": user["role"]
    }


# ---------------------------
# 내 정보 조회
# ---------------------------
@app.get("/me/{username}")
def get_me(username: str):
    user = get_user_by_username(username)

    if not user:
        raise HTTPException(status_code=404, detail="사용자 없음")

    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "role": user["role"],
        "public_key": user["public_key"]
    }


# ---------------------------
# plan 생성
# ---------------------------
@app.post("/plans")
def create_plan_api(req: CreatePlanRequest):
    owner = get_user_by_id(req.owner_id)

    if not owner:
        raise HTTPException(status_code=404, detail="owner 없음")

    if owner["role"] != "owner":
        raise HTTPException(status_code=400, detail="owner 역할 계정이 아님")

    plan_id = create_plan(req.owner_id, req.title, req.description)

    return {
        "message": "plan 생성 성공",
        "plan_id": plan_id
    }

# ---------------------------
# plan 조회
# ---------------------------
@app.get("/plans/{plan_id}")
def get_plan_api(plan_id: str):
    plan = get_plan_by_id(plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="plan 없음")

    participants = get_participants_by_plan(plan_id)
    state = get_state_by_plan(plan_id)

    return {
        "plan_id": plan["plan_id"],
        "owner_id": plan["owner_id"],
        "title": plan["title"],
        "description": plan["description"],
        "status": plan["status"],
        "current_state": state["current_state"] if state else None,
        "share_threshold": plan["share_threshold"],
        "share_total": plan["share_total"],
        "participants": [
            {
                "participant_id": p["participant_id"],
                "user_id": p["user_id"],
                "participant_role": p["participant_role"],
                "status": p["status"],
                **({
                    "username": u["username"],
                    "display_name": u["display_name"]
                } if (u := get_user_by_id(p["user_id"])) else {
                    "username": None,
                    "display_name": None
                })
            }
            for p in participants
        ]
    }


# ---------------------------
# participant 등록
# ---------------------------
@app.post("/participants")
def add_participant_api(req: AddParticipantRequest):
    participant_id = add_participant(
        req.plan_id,
        req.user_id,
        req.participant_role,
        req.is_required
    )

    return {
        "message": "participant 등록 성공",
        "participant_id": participant_id
    }


# ---------------------------
# state 조회
# ---------------------------
@app.get("/plans/{plan_id}/state")
def get_state_api(plan_id: str):
    state = get_state_by_plan(plan_id)
    if not state:
        raise HTTPException(status_code=404, detail="system_state 없음")

    return {
        "plan_id": plan_id,
        "current_state": state["current_state"],
        "last_activity_at": state["last_activity_at"],
        "last_checkin_at": state["last_checkin_at"],
        "pending_started_at": state["pending_started_at"],
        "escalated_at": state["escalated_at"],
        "inheritance_activated_at": state["inheritance_activated_at"],
        "recovered_at": state["recovered_at"],
        "updated_at": state["updated_at"]
    }


@app.post("/assets")
def create_asset_api(req: CreateAssetRequest):
    # 1. owner 존재 확인
    owner = get_user_by_id(req.owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="owner 없음")
    if owner["role"] != "owner":
        raise HTTPException(status_code=400, detail="owner 역할 계정이 아님")

    # 2. plan 존재 확인
    plan = get_plan_by_id(req.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan 없음")

    # 3. asset_type 검증
    if req.asset_type not in ["credential", "document", "media"]:
        raise HTTPException(status_code=400, detail="asset_type 오류")

    # 4. asset_id 생성
    asset_id = f"asset_{uuid.uuid4().hex[:8]}"

    # 5. DEK 생성
    dek = generate_dek()

    # 6. content 암호화 (base64 디코딩 후 AES-256-GCM — 텍스트/문서/미디어 모두 지원)
    try:
        raw_bytes = base64.b64decode(req.content)
    except Exception:
        raise HTTPException(status_code=400, detail="content가 올바른 base64 형식이 아닙니다")

    enc_result = encrypt_bytes(raw_bytes, dek)
    ciphertext = enc_result["ciphertext"]
    nonce = enc_result["nonce"]

    # 7. 스토리지 저장
    storage_path_obj = make_asset_storage_path(asset_id)
    with open(storage_path_obj, "wb") as f:
        f.write(ciphertext)

    storage_path = str(storage_path_obj)
    original_size = len(raw_bytes)
    encrypted_size = len(ciphertext)
    file_hash = hashlib.sha256(ciphertext).hexdigest()

    # 8. assets 테이블 저장
    insert_asset(
        asset_id=asset_id,
        plan_id=req.plan_id,
        owner_id=req.owner_id,
        asset_name=req.asset_name,
        asset_type=req.asset_type,
        mime_type=req.mime_type,
        storage_path=storage_path,
        original_size=original_size,
        encrypted_size=encrypted_size,
        file_hash=file_hash,
    )

        # 9. plan별 개발용 MK 로드
    mk = get_temp_mk(req.plan_id)
    if not mk:
        raise HTTPException(status_code=500, detail="MK 없음 (plan 초기화 문제)")

    existing_vault = get_key_vault_by_plan(req.plan_id)

    if existing_vault:
        try:
            encrypted_blob = existing_vault["encrypted_vault_blob"]
            vault_nonce = existing_vault["vault_nonce"]

            vault_dict = decrypt_vault(
                encrypted_blob=encrypted_blob,
                nonce=vault_nonce,
                mk=mk
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"기존 vault 복호화 실패: {str(e)}")
    else:
        vault_dict = {
            "vault_version": 1,
            "assets": []
        }
    
    # 10. 새 자산 메타를 vault에 추가
    vault_dict["assets"].append({
        "asset_id": asset_id,
        "asset_name": req.asset_name,
        "asset_type": req.asset_type,
        "mime_type": req.mime_type or "application/octet-stream",
        "dek": base64.b64encode(dek).decode("utf-8"),
        "algorithm": "AES-256-GCM",
        "nonce": base64.b64encode(nonce).decode("utf-8"),
        "chunked": False,
        "chunk_size": None
    })

    # 11. vault 암호화
    vault_enc = encrypt_vault(vault_dict, mk)

    # 12. key_vault 저장
    upsert_key_vault(
        plan_id=req.plan_id,
        owner_id=req.owner_id,
        encrypted_vault_blob=vault_enc["encrypted_blob"],
        vault_nonce=vault_enc["nonce"],
        vault_version=1,
        mk_version=1
    )

    return {
        "message": "자산 등록 성공",
        "asset_id": asset_id,
        "storage_path": storage_path,
        "original_size": original_size,
        "encrypted_size": encrypted_size
    }




@app.post("/plans/{plan_id}/finalize")
def finalize_plan_api(plan_id: str, req: FinalizePlanRequest):
    # 1. plan 존재 확인
    plan = get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan 없음")

    # 2. owner 확인
    owner = get_user_by_id(req.owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="owner 없음")
    if owner["role"] != "owner":
        raise HTTPException(status_code=400, detail="owner 역할 계정이 아님")

    # 3. 이 plan의 owner인지 확인
    if plan["owner_id"] != req.owner_id:
        raise HTTPException(status_code=403, detail="이 plan의 owner가 아님")

    # 4. 이미 finalize 되었는지 확인
    if plan["status"] == "inheritance_ready":
        raise HTTPException(status_code=400, detail="이미 finalize된 plan")

    # 5. participant 구성 검증
    counts = get_participant_counts(plan_id)

    if counts["legal_advisor"] < 1:
        raise HTTPException(status_code=400, detail="legal_advisor 최소 1명 필요")
    if counts["trustee"] < 1:
        raise HTTPException(status_code=400, detail="trustee 최소 1명 필요")
    if counts["beneficiary"] < 2:
        raise HTTPException(status_code=400, detail="beneficiary 최소 2명 필요")

    participants = get_participants_by_plan(plan_id)

    # 6. plan의 MK 로드
    mk = get_temp_mk(plan_id)
    if not mk:
        raise HTTPException(status_code=500, detail="plan의 MK 없음")

    # -----------------------------
    # A. IK 경로 준비
    # -----------------------------
    recovery_recipients = []
    for p in participants:
        role = p["participant_role"]
        if role in ["trustee", "beneficiary"]:
            recovery_recipients.append(p)

    if len(recovery_recipients) < 3:
        raise HTTPException(status_code=400, detail="inheritance share 발급 대상자가 3명 미만임")

    # 기존 inheritance share 삭제
    delete_assigned_shares_by_plan_and_scope(plan_id, "inheritance")

    # IK_key 생성
    ik_key = generate_recovery_secret(32)

    # IK_key로 MK wrap
    wrapped_ik_result = encrypt_bytes(mk, ik_key)
    wrapped_mk_ik_blob = wrapped_ik_result["ciphertext"]
    wrapped_mk_ik_nonce = wrapped_ik_result["nonce"]

    # IK material 저장
    save_inheritance_key_material(
        plan_id=plan_id,
        ik_key_blob=ik_key,
        wrapped_mk_ik_blob=wrapped_mk_ik_blob,
        wrapped_mk_ik_nonce=wrapped_mk_ik_nonce
    )

    # IK_key를 3-of-N 분할
    ik_threshold = 3
    ik_total_shares = len(recovery_recipients)

    ik_shares = split_secret(
        secret_bytes=ik_key,
        threshold=ik_threshold,
        num_shares=ik_total_shares
    )

    issued_ik_share_ids = []
    ik_share_index = 1

    for participant, share in zip(recovery_recipients, ik_shares):
        x, y = share

        share_payload = {
            "x": x,
            "y": str(y),
            "threshold": ik_threshold,
            "total": ik_total_shares
        }

        share_plaintext = json.dumps(
            share_payload,
            ensure_ascii=False
        ).encode("utf-8")

        recipient_user = get_user_by_id(participant["user_id"])
        if not recipient_user:
            raise HTTPException(status_code=404, detail="IK share recipient user 없음")

        recipient_public_key = recipient_user["public_key"]
        if not recipient_public_key:
            raise HTTPException(status_code=400, detail="IK recipient public key 없음")

        share_blob = hybrid_encrypt_with_public_key(
            recipient_public_key,
            share_plaintext
        )

        share_id = create_assigned_share(
            plan_id=plan_id,
            recipient_id=participant["user_id"],
            recipient_role=participant["participant_role"],
            share_scope="inheritance",
            encrypted_share_blob=share_blob,
            share_index=ik_share_index
        )

        issued_ik_share_ids.append(share_id)
        ik_share_index += 1

    # -----------------------------
    # B. OK 경로 준비
    # -----------------------------
    owner_user = get_user_by_id(plan["owner_id"])
    if not owner_user:
        raise HTTPException(status_code=404, detail="owner user 없음")

    advisor_participants = [
        p for p in participants
        if p["participant_role"] == "legal_advisor"
    ]
    if len(advisor_participants) < 1:
        raise HTTPException(status_code=400, detail="legal advisor 없음")

    advisor_user = get_user_by_id(advisor_participants[0]["user_id"])
    if not advisor_user:
        raise HTTPException(status_code=404, detail="advisor user 없음")

    # 기존 operational share 삭제
    delete_assigned_shares_by_plan_and_scope(plan_id, "operational")

    # OK_key 생성
    ok_key = generate_recovery_secret(32)

    # OK_key로 MK wrap
    wrapped_ok_result = encrypt_bytes(mk, ok_key)
    wrapped_mk_ok_blob = wrapped_ok_result["ciphertext"]
    wrapped_mk_ok_nonce = wrapped_ok_result["nonce"]

    # OK material 저장
    save_operational_key_material(
        plan_id=plan_id,
        ok_key_blob=ok_key,
        wrapped_mk_ok_blob=wrapped_mk_ok_blob,
        wrapped_mk_ok_nonce=wrapped_mk_ok_nonce
    )

    # OK_key를 2-of-2 분할
    ok_shares = split_secret(
        secret_bytes=ok_key,
        threshold=2,
        num_shares=2
    )

    ok_recipients = [
        {
            "user_id": owner_user["user_id"],
            "participant_role": "owner"
        },
        {
            "user_id": advisor_user["user_id"],
            "participant_role": "legal_advisor"
        }
    ]

    issued_ok_share_ids = []
    ok_share_index = 1

    for participant, share in zip(ok_recipients, ok_shares):
        x, y = share

        share_payload = {
            "x": x,
            "y": str(y),
            "threshold": 2,
            "total": 2
        }

        share_plaintext = json.dumps(
            share_payload,
            ensure_ascii=False
        ).encode("utf-8")

        recipient_user = get_user_by_id(participant["user_id"])
        if not recipient_user:
            raise HTTPException(status_code=404, detail="OK share recipient user 없음")

        recipient_public_key = recipient_user["public_key"]
        if not recipient_public_key:
            raise HTTPException(status_code=400, detail="OK recipient public key 없음")

        share_blob = hybrid_encrypt_with_public_key(
            recipient_public_key,
            share_plaintext
        )

        share_id = create_assigned_share(
            plan_id=plan_id,
            recipient_id=participant["user_id"],
            recipient_role=participant["participant_role"],
            share_scope="operational",
            encrypted_share_blob=share_blob,
            share_index=ok_share_index
        )

        issued_ok_share_ids.append(share_id)
        ok_share_index += 1

    # 7. plan 상태 업데이트
    update_plan_status(plan_id, "inheritance_ready")

    # 8. audit log 기록
    create_audit_log(
        plan_id=plan_id,
        actor_id=req.owner_id,
        action_type="plan_finalized",
        target_type="legacy_plan",
        target_id=plan_id,
        details_json=json.dumps({
            "ik_issued_share_count": len(issued_ik_share_ids),
            "ok_issued_share_count": len(issued_ok_share_ids),
            "ik_threshold": ik_threshold,
            "ik_total_shares": ik_total_shares,
            "ok_threshold": 2,
            "ok_total_shares": 2
        })
    )

    return {
        "message": "plan finalize 성공",
        "plan_id": plan_id,
        "plan_status": "inheritance_ready",
        "current_state_note": "system_state.current_state는 아직 active 상태로 유지됨",
        "participant_counts": counts,
        "ik_issued_share_ids": issued_ik_share_ids,
        "ok_issued_share_ids": issued_ok_share_ids
    }


@app.get("/plans/{plan_id}/shares")
def get_plan_shares_api(plan_id: str):
    plan = get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan 없음")

    shares = get_assigned_shares_by_plan(plan_id)

    return {
        "plan_id": plan_id,
        "shares": [
            {
                "share_id": row["share_id"],
                "recipient_id": row["recipient_id"],
                "recipient_role": row["recipient_role"],
                "share_index": row["share_index"],
                "issued_at": row["issued_at"],
                "viewed_at": row["viewed_at"],
                "delivery_status": row["delivery_status"],
                "encrypted_share_blob": row["encrypted_share_blob"],
                "share_scope": row["share_scope"]
            }
            for row in shares
        ]
    }


@app.post("/plans/{plan_id}/activate-inheritance")
def activate_inheritance_api(plan_id: str):
    plan = get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan 없음")

    # 🔥 1. 현재 상태 가져오기
    state = get_state_by_plan(plan_id)
    if not state:
        raise HTTPException(status_code=404, detail="system_state 없음")

    # 🔥 2. 상태 체크 (핵심)
    if state["current_state"] != "escalated":
        raise HTTPException(
            status_code=400,
            detail="현재 상태가 escalated가 아니므로 상속 활성화 불가"
        )

    approvals = get_approvals_by_plan_and_transition(plan_id, "inheritance_activated")
    trustee_approvals = [a for a in approvals if a["approver_role"] == "trustee"]

    if len(trustee_approvals) < 1:
        raise HTTPException(
            status_code=400,
            detail="trustee 승인 없이 상속 활성화 불가"
        )

    # 🔥 3. 상태 업데이트
    update_system_state(
        plan_id=plan_id,
        current_state="inheritance_activated",
        inheritance_activated_at=now()
    )

    return {
        "message": "상속 모드 전환 성공",
        "plan_id": plan_id,
        "current_state": "inheritance_activated"
    }


@app.put("/assets/{asset_id}")
def update_asset_api(asset_id: str, req: UpdateAssetRequest):

    # 1. asset 확인 (plan_id는 asset에서 가져와야 함)
    asset = get_asset_by_id(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="asset 없음")

    plan_id = asset["plan_id"]

    # plan_id 확보 후 state 체크
    state = get_state_by_plan(plan_id)
    if not state:
        raise HTTPException(status_code=404, detail="system_state 없음")

    if state["current_state"] not in ["active", "pending_confirmation"]:
        raise HTTPException(
            status_code=400,
            detail="현재 상태에서는 운영 경로 자산 수정이 허용되지 않음"
        )

    # 2. owner 확인
    owner = get_user_by_id(req.owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="owner 없음")
    if owner["role"] != "owner":
        raise HTTPException(status_code=400, detail="owner 역할 계정이 아님")

    if asset["owner_id"] != req.owner_id:
        raise HTTPException(status_code=403, detail="이 asset의 owner가 아님")

    # 3. advisor 확인
    advisor = get_user_by_id(req.advisor_id)
    if not advisor:
        raise HTTPException(status_code=404, detail="advisor 없음")
    if advisor["role"] != "legal_advisor":
        raise HTTPException(status_code=400, detail="legal_advisor 역할 계정이 아님")

    if not is_legal_advisor_for_plan(plan_id, req.advisor_id):
        raise HTTPException(status_code=403, detail="이 plan의 legal advisor가 아님")

    # 4. owner/advisor share 확인
    owner_share = get_assigned_share_by_id(req.owner_share_id)
    if not owner_share:
        raise HTTPException(status_code=404, detail="owner share 없음")

    advisor_share = get_assigned_share_by_id(req.advisor_share_id)
    if not advisor_share:
        raise HTTPException(status_code=404, detail="advisor share 없음")

    # 5. share가 해당 사용자에게 발급된 것인지 확인
    if owner_share["recipient_id"] != req.owner_id:
        raise HTTPException(status_code=403, detail="owner에게 발급된 share가 아님")
    if advisor_share["recipient_id"] != req.advisor_id:
        raise HTTPException(status_code=403, detail="advisor에게 발급된 share가 아님")

    # 6. operational share인지 확인
    if owner_share["share_scope"] != "operational":
        raise HTTPException(status_code=400, detail="owner share가 operational share가 아님")
    if advisor_share["share_scope"] != "operational":
        raise HTTPException(status_code=400, detail="advisor share가 operational share가 아님")

    # 7. OK share payload 형식 검사
    try:
        owner_payload = req.owner_decrypted_share_payload
        advisor_payload = req.advisor_decrypted_share_payload

        owner_x = int(owner_payload["x"])
        owner_y = int(owner_payload["y"])

        advisor_x = int(advisor_payload["x"])
        advisor_y = int(advisor_payload["y"])
    except Exception:
        raise HTTPException(status_code=400, detail="OK share payload 형식 오류")

    # 8. OK key material 로드
    ok_material = get_operational_key_material(plan_id)
    if not ok_material:
        raise HTTPException(status_code=500, detail="OK key material 없음")

    wrapped_mk_ok_blob = ok_material["wrapped_mk_ok_blob"]
    wrapped_mk_ok_nonce = ok_material["wrapped_mk_ok_nonce"]
    original_ok_key = ok_material["ok_key_blob"]

    # 9. owner+advisor OK share로 OK_key 복원
    try:
        reconstructed_ok_key = reconstruct_secret_bytes(
            shares=[(owner_x, owner_y), (advisor_x, advisor_y)],
            original_length=len(original_ok_key)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OK_key 복원 실패: {str(e)}")

    # 10. 복원된 OK_key 검증
    if reconstructed_ok_key != original_ok_key:
        raise HTTPException(status_code=400, detail="복원된 OK_key 불일치")

    # 11. reconstructed OK_key로 MK unwrap
    try:
        mk = decrypt_bytes(
            ciphertext=wrapped_mk_ok_blob,
            nonce=wrapped_mk_ok_nonce,
            dek=reconstructed_ok_key
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OK 경로 MK unwrap 실패: {str(e)}")

    # 12. key_vault 로드
    key_vault = get_key_vault_by_plan(plan_id)
    if not key_vault:
        raise HTTPException(status_code=404, detail="key_vault 없음")

    # 13. recovered MK로 vault 복호화
    try:
        vault_dict = decrypt_vault(
            encrypted_blob=key_vault["encrypted_vault_blob"],
            nonce=key_vault["vault_nonce"],
            mk=mk
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"vault 복호화 실패: {str(e)}")

    # 14. vault 안에서 target asset 메타 찾기
    target_meta = None
    for item in vault_dict["assets"]:
        if item["asset_id"] == asset_id:
            target_meta = item
            break

    if not target_meta:
        raise HTTPException(status_code=404, detail="vault 안에 asset 메타 없음")

    # 15. 새 DEK 생성
    new_dek = generate_dek()

    # 16. 새 content 암호화 (등록과 동일하게 base64 디코딩 후 raw bytes 암호화)
    try:
        raw_bytes = base64.b64decode(req.new_content)
    except Exception:
        raise HTTPException(status_code=400, detail="new_content가 올바른 base64 형식이 아닙니다")

    enc_result = encrypt_bytes(raw_bytes, new_dek)
    ciphertext = enc_result["ciphertext"]
    nonce = enc_result["nonce"]

    # 17. 기존 storage 파일 덮어쓰기
    storage_path = asset["storage_path"]
    with open(storage_path, "wb") as f:
        f.write(ciphertext)

    # 18. assets 테이블 갱신
    original_size = len(raw_bytes)
    encrypted_size = len(ciphertext)
    file_hash = hashlib.sha256(ciphertext).hexdigest()

    update_asset_record(
        asset_id=asset_id,
        asset_name=req.new_asset_name,
        mime_type=req.mime_type if req.mime_type else asset["mime_type"],
        original_size=original_size,
        encrypted_size=encrypted_size,
        file_hash=file_hash
    )

    # 19. vault 메타 갱신
    target_meta["asset_name"] = req.new_asset_name
    target_meta["mime_type"] = req.mime_type if req.mime_type else asset["mime_type"]
    target_meta["dek"] = base64.b64encode(new_dek).decode("utf-8")
    target_meta["nonce"] = base64.b64encode(nonce).decode("utf-8")
    target_meta["algorithm"] = "AES-256-GCM"
    target_meta["chunked"] = False
    target_meta["chunk_size"] = None

    # 20. vault 재암호화
    vault_enc = encrypt_vault(vault_dict, mk)

    upsert_key_vault(
        plan_id=plan_id,
        owner_id=req.owner_id,
        encrypted_vault_blob=vault_enc["encrypted_blob"],
        vault_nonce=vault_enc["nonce"],
        vault_version=key_vault["vault_version"],
        mk_version=key_vault["mk_version"]
    )

    # 21. audit log 기록
    create_audit_log(
        plan_id=plan_id,
        actor_id=req.owner_id,
        action_type="asset_updated_via_ok_2of2",
        target_type="asset",
        target_id=asset_id,
        details_json=json.dumps({
            "advisor_id": req.advisor_id,
            "owner_share_id": req.owner_share_id,
            "advisor_share_id": req.advisor_share_id,
            "asset_name": req.new_asset_name
        })
    )

    return {
        "message": "자산 수정 성공 (OK 2-of-2 경로)",
        "asset_id": asset_id,
        "plan_id": plan_id,
        "updated_asset_name": req.new_asset_name,
        "original_size": original_size,
        "encrypted_size": encrypted_size
    }


@app.post("/plans/{plan_id}/recovery-sessions")
def create_recovery_session_api(plan_id: str, req: CreateRecoverySessionRequest):
    plan = get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan 없음")

    state = get_state_by_plan(plan_id)
    if not state:
        raise HTTPException(status_code=404, detail="state 없음")

    if state["current_state"] != "inheritance_activated":
        raise HTTPException(status_code=400, detail="상속 모드가 아님")

    requester = get_user_by_id(req.requester_id)
    if not requester:
        raise HTTPException(status_code=404, detail="requester 없음")

    # trustee만 recovery session 생성 가능
    if requester["role"] != "trustee":
        raise HTTPException(
            status_code=403,
            detail=f"Recovery Session은 신탁인(trustee)만 생성할 수 있습니다. 현재 역할: {requester['role']}"
        )

    # 해당 플랜의 trustee 참가자인지 확인
    participants = get_participants_by_plan(plan_id)
    is_plan_trustee = any(
        p["user_id"] == req.requester_id and p["participant_role"] == "trustee"
        for p in participants
    )
    if not is_plan_trustee:
        raise HTTPException(status_code=403, detail="이 플랜의 신탁인이 아닙니다")

    recovery_id = create_recovery_session(plan_id)

    # 수혜자 전원에게 알림 발송 (생성자 정보 포함)
    requester_name = requester["display_name"] or requester["username"]
    for p in participants:
        if p["participant_role"] == "beneficiary":
            create_notification(
                user_id=p["user_id"],
                plan_id=plan_id,
                notification_type="recovery_session_created",
                message=(
                    f"신탁인 '{requester_name}'이(가) Recovery Session을 생성했습니다. "
                    f"Share를 제출하여 자산 복구를 진행해주세요. "
                    f"(Session ID: {recovery_id})"
                )
            )

    create_audit_log(
        plan_id=plan_id,
        actor_id=req.requester_id,
        action_type="recovery_session_created",
        target_type="recovery_session",
        target_id=recovery_id,
        details_json=json.dumps({
            "note": "IK recovery session created by trustee",
            "requester_name": requester_name
        })
    )

    return {
        "message": "recovery session 생성 성공",
        "recovery_id": recovery_id,
        "plan_id": plan_id,
        "created_by": requester_name
    }


@app.post("/recovery-sessions/{recovery_id}/submit-share")
def submit_share_api(recovery_id: str, req: SubmitShareRequest):
    recovery = get_recovery_session_by_id(recovery_id)
    if not recovery:
        raise HTTPException(status_code=404, detail="recovery session 없음")

    if recovery["status"] != "open":
        raise HTTPException(status_code=400, detail="열린 recovery session이 아님")

    actor = get_user_by_id(req.actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail="actor 없음")

    assigned_share = get_assigned_share_by_id(req.share_id)
    if not assigned_share:
        raise HTTPException(status_code=404, detail="assigned share 없음")

    # share가 이 actor에게 발급된 것인지 확인
    if assigned_share["recipient_id"] != req.actor_id:
        raise HTTPException(status_code=403, detail="본인에게 발급된 share가 아님")

    # recovery session의 plan과 share의 plan이 같은지 확인
    if assigned_share["plan_id"] != recovery["plan_id"]:
        raise HTTPException(status_code=400, detail="share의 plan이 recovery session과 다름")

    actor_role = assigned_share["recipient_role"]

    try:
        submitted_share_payload = req.decrypted_share_payload
        x = int(submitted_share_payload["x"])
        y = int(submitted_share_payload["y"])
    except Exception:
        raise HTTPException(status_code=400, detail="decrypted_share_payload 형식 오류")

    # 에러3 수정: 같은 share를 같은 recovery에 중복 제출하면 UNIQUE constraint 터짐
    existing_submissions = get_submitted_shares_by_recovery(recovery_id)
    for es in existing_submissions:
        if es["share_id"] == req.share_id:
            raise HTTPException(status_code=409, detail="이미 제출된 share입니다 (중복 제출 불가)")
        if es["actor_id"] == req.actor_id:
            raise HTTPException(status_code=409, detail="이미 이 복구 세션에 share를 제출하셨습니다")

    submission_id = create_submitted_share(
        recovery_id=recovery_id,
        actor_id=req.actor_id,
        actor_role=actor_role,
        share_id=req.share_id,
        submitted_share_payload=json.dumps(req.decrypted_share_payload, ensure_ascii=False),
        is_valid=True,
        validation_note=None
    )

    # threshold 검사
    result = evaluate_recovery_threshold(recovery_id)

    created_packages = []
    created_package_infos = []  # 블록 밖에서 초기화 (UnboundLocalError 수정)

    if result["success"]:
        if recovery["status"] == "open":
            submissions = get_submitted_shares_by_recovery(recovery_id)

            print("[DEBUG] submissions keys =", [list(dict(s).keys()) for s in submissions])
            print("[DEBUG] submissions rows =", [dict(s) for s in submissions])

            valid_submissions = [s for s in submissions if s["is_valid"] == 1]

            share_points = []
            for s in valid_submissions:
                share_payload = json.loads(s["submitted_share_payload"])
                x = int(share_payload["x"])
                y = int(share_payload["y"])
                share_points.append((x, y))

            share_points = share_points[:3]

            # 1. IK 관련 재료 로드
            ik_material = get_inheritance_key_material(recovery["plan_id"])
            if not ik_material:
                raise HTTPException(status_code=500, detail="IK key material 없음")

            original_ik_key = ik_material["ik_key_blob"]
            wrapped_mk_ik_blob = ik_material["wrapped_mk_ik_blob"]
            wrapped_mk_ik_nonce = ik_material["wrapped_mk_ik_nonce"]

            # 2. share로 IK_key 복원
            try:
                reconstructed_ik_key = reconstruct_secret_bytes(
                    shares=share_points,
                    original_length=len(original_ik_key)
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"IK_key 복원 실패: {str(e)}")

            # 3. IK_key 일치 확인
            if reconstructed_ik_key != original_ik_key:
                raise HTTPException(status_code=400, detail="복원된 IK_key 불일치")

            # 4. IK_key로 MK unwrap
            try:
                recovered_mk = decrypt_bytes(
                    ciphertext=wrapped_mk_ik_blob,
                    nonce=wrapped_mk_ik_nonce,
                    dek=reconstructed_ik_key
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"MK unwrap 실패: {str(e)}")

            # 5. recovered_mk로 key_vault 복호화 가능한지 확인
            key_vault = get_key_vault_by_plan(recovery["plan_id"])
            if not key_vault:
                raise HTTPException(status_code=404, detail="key_vault 없음")

            try:
                vault_dict = decrypt_vault(
                    encrypted_blob=key_vault["encrypted_vault_blob"],
                    nonce=key_vault["vault_nonce"],
                    mk=recovered_mk
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"key_vault 복호화 실패: {str(e)}")

            # 6. 복구 성공 처리
            complete_recovery_session(recovery_id)

            created_packages = []
            created_package_infos = []

            participants = get_participants_by_plan(recovery["plan_id"])
            for p in participants:
                if p["participant_role"] != "beneficiary":
                    continue

                recovery_package_payload = {
                    "package_type": "recovered_key_vault_package",
                    "plan_id": recovery["plan_id"],
                    "recipient_id": p["user_id"],
                    "created_for_recovery_id": recovery_id,
                    "asset_count": len(vault_dict.get("assets", [])),
                    "vault_version": vault_dict.get("vault_version", 1),
                    "vault_contents": vault_dict
                }

                package_plaintext = json.dumps(
                    recovery_package_payload,
                    ensure_ascii=False
                ).encode("utf-8")

                recipient_user = get_user_by_id(p["user_id"])
                if not recipient_user:
                    raise HTTPException(status_code=404, detail="package recipient user 없음")

                recipient_public_key = recipient_user["public_key"]
                if not recipient_public_key:
                    raise HTTPException(status_code=400, detail="package recipient public key 없음")

                package_blob = hybrid_encrypt_with_public_key(
                    recipient_public_key,
                    package_plaintext
                )

                package_id = create_recovery_package(
                    recovery_id=recovery_id,
                    recipient_id=p["user_id"],
                    recipient_role="beneficiary",
                    encrypted_package_blob=package_blob
                )
                created_packages.append(package_id)
                created_package_infos.append({
                    "package_id": package_id,
                    "recipient_id": p["user_id"],
                    "recipient_role": p["participant_role"]
                })

            update_system_state(
                plan_id=recovery["plan_id"],
                current_state="recovered",
                recovered_at=now()
            )

    create_audit_log(
        plan_id=recovery["plan_id"],
        actor_id=req.actor_id,
        action_type="share_submitted",
        target_type="recovery_session",
        target_id=recovery_id,
        details_json=f'{{"share_id":"{req.share_id}","submission_id":"{submission_id}"}}'
    )

    return {
        "message": "share 제출 성공",
        "submission_id": submission_id,
        "recovery_id": recovery_id,
        "threshold_result": result,
        "success": result["success"],
        "created_package_ids": created_packages,
        "created_packages": created_package_infos
    }


@app.get("/recovery-sessions/{recovery_id}")
def get_recovery_session_api(recovery_id: str):
    recovery = get_recovery_session_by_id(recovery_id)
    if not recovery:
        raise HTTPException(status_code=404, detail="recovery session 없음")

    submissions = get_submitted_shares_by_recovery(recovery_id)
    result = evaluate_recovery_threshold(recovery_id)
    packages = get_recovery_packages_by_recovery(recovery_id)

    return {
        "recovery_id": recovery["recovery_id"],
        "plan_id": recovery["plan_id"],
        "status": recovery["status"],
        "threshold_required": recovery["threshold_required"],
        "trustee_required": recovery["trustee_required"],
        "beneficiary_required_count": recovery["beneficiary_required_count"],
        "threshold_result": result,
        "submissions": [
            {
                "submission_id": s["submission_id"],
                "actor_id": s["actor_id"],
                "actor_role": s["actor_role"],
                "share_id": s["share_id"],
                "is_valid": s["is_valid"]
            }
            for s in submissions
        ],
        "packages": [
            {
                "package_id": p["package_id"],
                "recipient_id": p["recipient_id"],
                "recipient_role": p["recipient_role"],
                "package_status": p["package_status"]
            }
            for p in packages
        ]
    }


@app.get("/plans/{plan_id}/recovery-sessions")
def get_plan_recovery_sessions_api(plan_id: str):
    plan = get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan 없음")

    sessions = get_recovery_sessions_by_plan(plan_id)

    return {
        "plan_id": plan_id,
        "sessions": [
            {
                "recovery_id": s["recovery_id"],
                "status": s["status"],
                "threshold_required": s["threshold_required"],
                "created_at": s["created_at"],
            }
            for s in sessions
        ]
    }




@app.post("/plans/{plan_id}/deadman-policy")
def set_deadman_policy_api(plan_id: str, req: DeadmanPolicyRequest):
    plan = get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan 없음")

    if plan["owner_id"] != req.owner_id:
        raise HTTPException(status_code=403, detail="이 plan의 owner가 아님")

    if req.checkin_interval_days <= 0:
        raise HTTPException(status_code=400, detail="checkin_interval_days는 1 이상이어야 함")
    if req.grace_period_days < 0:
        raise HTTPException(status_code=400, detail="grace_period_days는 0 이상이어야 함")

    upsert_deadman_policy(
        plan_id=plan_id,
        checkin_interval_days=req.checkin_interval_days,
        grace_period_days=req.grace_period_days,
        is_enabled=req.is_enabled
    )

    create_audit_log(
        plan_id=plan_id,
        actor_id=req.owner_id,
        action_type="deadman_policy_updated",
        target_type="deadman_policy",
        target_id=plan_id,
        details_json=json.dumps({
            "checkin_interval_days": req.checkin_interval_days,
            "grace_period_days": req.grace_period_days,
            "is_enabled": req.is_enabled
        })
    )

    return {
        "message": "deadman policy 설정 성공",
        "plan_id": plan_id,
        "checkin_interval_days": req.checkin_interval_days,
        "grace_period_days": req.grace_period_days,
        "is_enabled": req.is_enabled
    }


@app.post("/plans/{plan_id}/checkin")
def owner_checkin_api(plan_id: str, req: CheckinRequest):
    plan = get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan 없음")

    if plan["owner_id"] != req.owner_id:
        raise HTTPException(status_code=403, detail="이 plan의 owner가 아님")

    state = get_state_by_plan(plan_id)
    if not state:
        raise HTTPException(status_code=404, detail="system_state 없음")

    current_time = now()

    update_system_state(
        plan_id=plan_id,
        current_state="active",
        last_checkin_at=current_time,
        pending_started_at=None,
        escalated_at=None
    )

    create_audit_log(
        plan_id=plan_id,
        actor_id=req.owner_id,
        action_type="owner_checkin",
        target_type="system_state",
        target_id=plan_id,
        details_json=json.dumps({"new_state": "active"})
    )

    return {
        "message": "check-in 성공",
        "plan_id": plan_id,
        "current_state": "active",
        "last_checkin_at": current_time
    }


@app.post("/plans/{plan_id}/evaluate-state")
def evaluate_state_api(plan_id: str):
    plan = get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan 없음")

    new_state = evaluate_state_logic(plan_id)
    if new_state is None:
        raise HTTPException(status_code=400, detail="평가 불가")

    return {
        "message": "상태 평가 완료",
        "plan_id": plan_id,
        "current_state": new_state
    }


@app.on_event("startup")
def start_scheduler():
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    print("[scheduler] deadman state evaluator started")


@app.get("/users/{user_id}/plans")
def get_user_plans_api(user_id: str):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user 없음")

    plans = get_plans_by_user(user_id)

    return {
        "user_id": user_id,
        "plans": [
            {
                "plan_id": row["plan_id"],
                "owner_id": row["owner_id"],
                "title": row["title"],
                "description": row["description"],
                "status": row["status"],
                "share_threshold": row["share_threshold"],
                "share_total": row["share_total"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "finalized_at": row["finalized_at"]
            }
            for row in plans
        ]
    }


@app.get("/plans/{plan_id}/assets")
def get_plan_assets_api(plan_id: str):
    plan = get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan 없음")

    assets = get_assets_by_plan(plan_id)

    return {
        "plan_id": plan_id,
        "assets": [
            {
                "asset_id": row["asset_id"],
                "plan_id": row["plan_id"],
                "owner_id": row["owner_id"],
                "asset_name": row["asset_name"],
                "asset_type": row["asset_type"],
                "mime_type": row["mime_type"],
                "storage_path": row["storage_path"],
                "original_size": row["original_size"],
                "encrypted_size": row["encrypted_size"],
                "file_hash": row["file_hash"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
            for row in assets
        ]
    }


@app.get("/assets/{asset_id}/encrypted-blob")
def get_asset_encrypted_blob_api(asset_id: str):
    """암호화된 자산 파일(.bin)을 base64로 반환 — 브라우저 복호화용"""
    asset = get_asset_by_id(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="asset 없음")

    storage_path = asset["storage_path"]
    try:
        with open(storage_path, "rb") as f:
            encrypted_bytes = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="암호화 파일 없음")

    return {
        "asset_id": asset_id,
        "asset_name": asset["asset_name"],
        "asset_type": asset["asset_type"],
        "mime_type": asset["mime_type"],
        "original_size": asset["original_size"],
        "encrypted_size": asset["encrypted_size"],
        "encrypted_blob": base64.b64encode(encrypted_bytes).decode("utf-8")
    }


@app.get("/users/{user_id}/shares")
def get_user_shares_api(user_id: str):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user 없음")

    shares = get_assigned_shares_by_recipient(user_id)

    return {
        "user_id": user_id,
        "shares": [
            {
                "share_id": row["share_id"],
                "plan_id": row["plan_id"],
                "recipient_id": row["recipient_id"],
                "recipient_role": row["recipient_role"],
                "share_scope": row["share_scope"],
                "share_index": row["share_index"],
                "issued_at": row["issued_at"],
                "viewed_at": row["viewed_at"],
                "delivery_status": row["delivery_status"]
            }
            for row in shares
        ]
    }


@app.get("/users/{user_id}/packages")
def get_user_packages_api(user_id: str):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user 없음")

    packages = get_packages_by_recipient(user_id)

    return {
        "user_id": user_id,
        "packages": [
            {
                "package_id": row["package_id"],
                "plan_id": row["plan_id"],
                "recovery_id": row["recovery_id"],
                "recipient_id": row["recipient_id"],
                "recipient_role": row["recipient_role"],
                "created_at": row["created_at"],
                "expires_at": row["expires_at"],
                "delivered_at": row["delivered_at"],
                "package_status": row["package_status"],
                "encrypted_package_blob": row["encrypted_package_blob"]
            }
            for row in packages
        ]
    }


@app.post("/plans/{plan_id}/approve-inheritance")
def approve_inheritance_api(plan_id: str, req: TrusteeApprovalRequest):
    plan = get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan 없음")

    trustee = get_user_by_id(req.trustee_id)
    if not trustee:
        raise HTTPException(status_code=404, detail="trustee 없음")
    if trustee["role"] != "trustee":
        raise HTTPException(status_code=400, detail="trustee 역할 계정이 아님")

    participants = get_participants_by_plan(plan_id)
    matched = None
    for p in participants:
        if p["user_id"] == req.trustee_id and p["participant_role"] == "trustee":
            matched = p
            break

    if not matched:
        raise HTTPException(status_code=403, detail="이 plan의 trustee가 아님")

    state = get_state_by_plan(plan_id)
    if not state:
        raise HTTPException(status_code=404, detail="system_state 없음")

    if state["current_state"] != "escalated":
        raise HTTPException(status_code=400, detail="현재 상태가 escalated가 아님")

    create_state_transition_approval(
        plan_id=plan_id,
        requested_transition="inheritance_activated",
        approver_id=req.trustee_id,
        approver_role="trustee",
        approval_status="approved"
    )

    create_audit_log(
        plan_id=plan_id,
        actor_id=req.trustee_id,
        action_type="trustee_approved_inheritance",
        target_type="state_transition_approval",
        target_id=plan_id,
        details_json=json.dumps({
            "requested_transition": "inheritance_activated"
        })
    )

    # trustee 승인 즉시 inheritance_activated로 자동 전환
    update_system_state(
        plan_id=plan_id,
        current_state="inheritance_activated",
        inheritance_activated_at=now()
    )

    # 수혜자(beneficiary) 전원에게 상속 활성화 알림 발송
    participants = get_participants_by_plan(plan_id)
    for p in participants:
        if p["participant_role"] == "beneficiary":
            create_notification(
                user_id=p["user_id"],
                plan_id=plan_id,
                notification_type="inheritance_activated",
                message="상속이 활성화되었습니다. Share를 제출하여 자산을 복구할 수 있습니다."
            )

    create_audit_log(
        plan_id=plan_id,
        actor_id=req.trustee_id,
        action_type="inheritance_activated_auto",
        target_type="system_state",
        target_id=plan_id,
        details_json=json.dumps({"triggered_by": "trustee_approval"})
    )

    return {
        "message": "trustee 승인 완료 → 상속 모드 자동 활성화",
        "plan_id": plan_id,
        "current_state": "inheritance_activated",
        "trustee_id": req.trustee_id
    }


@app.get("/users/{user_id}/notifications")
def get_user_notifications_api(user_id: str):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user 없음")

    notifications = get_notifications_by_user(user_id)

    return {
        "user_id": user_id,
        "notifications": [
            {
                "notification_id": row["notification_id"],
                "plan_id": row["plan_id"],
                "notification_type": row["notification_type"],
                "message": row["message"],
                "is_read": row["is_read"],
                "created_at": row["created_at"]
            }
            for row in notifications
        ]
    }


@app.post("/notifications/{notification_id}/read")
def mark_notification_read_api(notification_id: str, req: NotificationReadRequest):
    user = get_user_by_id(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user 없음")

    mark_notification_as_read(notification_id, req.user_id)

    return {
        "message": "알림 읽음 처리 성공",
        "notification_id": notification_id,
        "user_id": req.user_id
    }


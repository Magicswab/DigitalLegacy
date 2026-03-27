from pydantic import BaseModel
from typing import Any

class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str
    role: str
    public_key: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    user_id: str
    username: str
    display_name: str
    role: str
    public_key: str


class CreatePlanRequest(BaseModel):
    owner_id: str
    title: str
    description: str | None = None
    share_threshold: int = 3
    share_total: int = 5


class AddParticipantRequest(BaseModel):
    plan_id: str
    user_id: str
    participant_role: str   # legal_advisor / trustee / beneficiary
    is_required: bool = True


class PlanResponse(BaseModel):
    plan_id: str
    owner_id: str
    title: str
    description: str | None
    status: str
    share_threshold: int
    share_total: int


class ParticipantResponse(BaseModel):
    participant_id: str
    plan_id: str
    user_id: str
    participant_role: str
    status: str


class StateResponse(BaseModel):
    state_id: str
    plan_id: str
    owner_id: str
    current_state: str
    last_activity_at: str
    inactivity_threshold_sec: int
    grace_period_sec: int


class CreateAssetRequest(BaseModel):
    plan_id: str
    owner_id: str
    asset_name: str
    asset_type: str   # credential / document / media
    mime_type: str | None = None
    content: str      # base64 인코딩된 문자열 (텍스트: btoa(text), 파일: FileReader.readAsDataURL → split(",")[1])


class FinalizePlanRequest(BaseModel):
    owner_id: str


class UpdateAssetRequest(BaseModel):
    owner_id: str
    advisor_id: str
    owner_share_id: str
    advisor_share_id: str
    owner_decrypted_share_payload: dict
    advisor_decrypted_share_payload: dict
    new_asset_name: str
    new_content: str
    mime_type: str | None = None


class CreateRecoverySessionRequest(BaseModel):
    requester_id: str
    reason: str | None = None


class SubmitShareRequest(BaseModel):
    actor_id: str
    share_id: str
    decrypted_share_payload: dict[str, Any]


class DeadmanPolicyRequest(BaseModel):
    owner_id: str
    checkin_interval_days: int
    grace_period_days: int
    is_enabled: bool


class CheckinRequest(BaseModel):
    owner_id: str


class TrusteeApprovalRequest(BaseModel):
    trustee_id: str
    requested_transition: str | None = None


class NotificationReadRequest(BaseModel):
    user_id: str
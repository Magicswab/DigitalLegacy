import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' }
})

// ── Auth ──────────────────────────────────────
export const login = (username, password) =>
  http.post('/login', { username, password })

export const register = (data) =>
  http.post('/register', data)

export const getMe = (username) =>
  http.get(`/me/${username}`)

// ── Plans ─────────────────────────────────────
export const getMyPlans = (userId) =>
  http.get(`/users/${userId}/plans`)

export const getPlan = (planId) =>
  http.get(`/plans/${planId}`)

export const getPlanState = (planId) =>
  http.get(`/plans/${planId}/state`)

export const getPlanAssets = (planId) =>
  http.get(`/plans/${planId}/assets`)

export const getPlanShares = (planId) =>
  http.get(`/plans/${planId}/shares`)

// ── 상태 액션 ────────────────────────────────
export const checkin = (planId, ownerId) =>
  http.post(`/plans/${planId}/checkin`, { owner_id: ownerId })

export const evaluateState = (planId) =>
  http.post(`/plans/${planId}/evaluate-state`)

export const approveInheritance = (planId, trusteeId) =>
  http.post(`/plans/${planId}/approve-inheritance`, {
    trustee_id: trusteeId,
    requested_transition: 'inheritance_activated'
  })

export const setDeadmanPolicy = (planId, ownerId, intervalDays, graceDays, enabled = true) =>
  http.post(`/plans/${planId}/deadman-policy`, {
    owner_id: ownerId,
    checkin_interval_days: intervalDays,
    grace_period_days: graceDays,
    is_enabled: enabled
  })

// ── Share / Recovery ──────────────────────────
export const getMyShares = (userId) =>
  http.get(`/users/${userId}/shares`)

export const createRecoverySession = (planId, requesterId, reason) =>
  http.post(`/plans/${planId}/recovery-sessions`, {
    requester_id: requesterId,
    reason
  })

export const getRecoverySession = (recoveryId) =>
  http.get(`/recovery-sessions/${recoveryId}`)

export const getPlanRecoverySessions = (planId) =>
  http.get(`/plans/${planId}/recovery-sessions`)

export const submitShare = (recoveryId, actorId, shareId, decryptedPayload) =>
  http.post(`/recovery-sessions/${recoveryId}/submit-share`, {
    actor_id: actorId,
    share_id: shareId,
    decrypted_share_payload: decryptedPayload
  })

// ── Packages ──────────────────────────────────
export const getMyPackages = (userId) =>
  http.get(`/users/${userId}/packages`)

// ── Notifications ─────────────────────────────
export const getNotifications = (userId) =>
  http.get(`/users/${userId}/notifications`)

export const markNotificationRead = (notifId, userId) =>
  http.post(`/notifications/${notifId}/read`, { user_id: userId })

export default http

// ── Plan 생성/관리 ─────────────────────────────
export const createPlan = (ownerId, title, description, threshold = 3, total = 5) =>
  http.post('/plans', { owner_id: ownerId, title, description, share_threshold: threshold, share_total: total })

export const addParticipant = (planId, userId, role) =>
  http.post('/participants', { plan_id: planId, user_id: userId, participant_role: role, is_required: true })

export const finalizePlan = (planId, ownerId) =>
  http.post(`/plans/${planId}/finalize`, { owner_id: ownerId })

export const updateAsset = (assetId, data) =>
  http.put(`/assets/${assetId}`, data)

export const getUserByUsername = (username) =>
  http.get(`/me/${username}`)

export const getAssetEncryptedBlob = (assetId) =>
  http.get(`/assets/${assetId}/encrypted-blob`)

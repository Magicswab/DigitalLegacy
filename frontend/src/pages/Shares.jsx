import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { useToast, Card, CardTitle, PageHeader, Empty, Btn, Field, Input, Textarea, Select, LogBox, useLog } from '../components/UI'
import { getMyShares, getMyPlans, createRecoverySession, submitShare, getRecoverySession, getPlanRecoverySessions } from '../api'

export default function Shares() {
  const { user } = useAuth()
  const toast = useToast()
  const { lines, add } = useLog()

  const isTrustee = user?.role === 'trustee'

  const [myShares, setMyShares]         = useState([])
  const [sharesLoading, setSL]          = useState(false)
  const [plans, setPlans]               = useState([])
  const [planId, setPlanId]             = useState('')
  const [reason, setReason]             = useState('inheritance recovery request')
  const [sessionLoading, setSesL]       = useState(false)
  const [recoveryId, setRecoveryId]     = useState('')
  const [shareId, setShareId]           = useState('')
  const [payload, setPayload]           = useState('')
  const [submitLoading, setSubL]        = useState(false)
  const [sessionInfo, setSessionInfo]   = useState(null)
  const [sessionList, setSessionList]   = useState([])
  const [sessListLoading, setSessListL] = useState(false)

  useEffect(() => {
    getMyPlans(user.user_id).then(r => setPlans(r.data.plans || r.data || [])).catch(() => {})
  }, [])

  const loadShares = async () => {
    setSL(true)
    add(`GET /users/${user.user_id}/shares`, 'info')
    try {
      const r = await getMyShares(user.user_id)
      const list = r.data.shares || r.data || []
      setMyShares(list)
      add(`${list.length}개 share 확인됨`, 'ok')
    } catch (e) {
      add(`오류: ${e.response?.data?.detail || e.message}`, 'err')
    } finally { setSL(false) }
  }
  useEffect(() => { loadShares() }, [])

  useEffect(() => {
    if (!planId) { setSessionList([]); return }
    loadSessionList(planId)
  }, [planId])

  const loadSessionList = async (pid) => {
    setSessListL(true)
    try {
      const r = await getPlanRecoverySessions(pid)
      setSessionList(r.data.sessions || r.data || [])
    } catch {
      setSessionList([])
    } finally { setSessListL(false) }
  }

  const handleCreateSession = async () => {
    if (!planId) { toast('플랜을 선택하세요', 'err'); return }
    setSesL(true)
    add(`POST /plans/${planId}/recovery-sessions`, 'info')
    try {
      const r = await createRecoverySession(planId, user.user_id, reason)
      const id = r.data.recovery_id
      setRecoveryId(id)
      toast('Recovery Session 생성 완료! 수혜자들에게 알림이 발송됩니다.', 'ok')
      add(`recovery_id: ${id}`, 'ok')
      loadSessionList(planId)
    } catch (e) {
      toast(e.response?.data?.detail || '생성 실패', 'err')
      add(`오류: ${e.response?.data?.detail || e.message}`, 'err')
    } finally { setSesL(false) }
  }

  const handleSubmit = async () => {
    if (!recoveryId || !shareId || !payload) { toast('모든 필드를 입력하세요', 'err'); return }
    let parsed
    try { parsed = JSON.parse(payload) } catch { toast('Payload는 JSON 형식이어야 합니다', 'err'); return }
    setSubL(true)
    add(`POST /recovery-sessions/${recoveryId}/submit-share`, 'info')
    try {
      const r = await submitShare(recoveryId, user.user_id, shareId, parsed)
      if (r.data.success) {
        toast('임계값 충족! 복구 완료', 'ok')
        add('복구 완료 — 패키지가 생성되었습니다', 'ok')
      } else {
        toast('Share 제출 완료 (임계값 미달, 대기 중)', 'ok')
        add('제출 완료 — 추가 share 대기 중', 'ok')
      }
      const rs = await getRecoverySession(recoveryId)
      setSessionInfo(rs.data)
    } catch (e) {
      toast(e.response?.data?.detail || '제출 실패', 'err')
      add(`오류: ${e.response?.data?.detail || e.message}`, 'err')
    } finally { setSubL(false) }
  }

  const handleCheckSession = async (id) => {
    const targetId = id || recoveryId
    if (!targetId) return
    try {
      const r = await getRecoverySession(targetId)
      setSessionInfo(r.data)
      setRecoveryId(targetId)
      add(`세션 상태: ${r.data.status} | 제출: ${r.data.submissions?.length || 0}/${r.data.threshold_required}`, 'ok')
    } catch (e) { add(`오류: ${e.response?.data?.detail || e.message}`, 'err') }
  }

  const SCOPE_COL = { operational: 'var(--cyan)', inheritance: 'var(--green)' }

  return (
    <div style={{ padding: '24px 28px', animation: 'fadeUp 0.3s ease' }}>
      <PageHeader title="Share 제출" sub="IK 복구 · Shamir 3-of-N · 비동기 프로토콜" />

      {/* 플랜 선택 */}
      <Card>
        <CardTitle>플랜 선택</CardTitle>
        <Select value={planId} onChange={e => setPlanId(e.target.value)}>
          <option value="">— 플랜을 선택하세요 —</option>
          {plans.map(p => (
            <option key={p.plan_id} value={p.plan_id}>{p.title} ({p.status})</option>
          ))}
        </Select>
        {planId && (
          <div style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--mono)', marginTop: 6 }}>
            plan_id: {planId}
          </div>
        )}
      </Card>

      {/* 내 Share 목록 */}
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <CardTitle>내 할당 Share</CardTitle>
          <Btn v="ghost" sm onClick={loadShares} loading={sharesLoading}>새로고침</Btn>
        </div>
        {myShares.length === 0 ? (
          <Empty msg="할당된 Share가 없습니다" />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {myShares.map((s, i) => {
              const sid = s.share_id || s.assigned_share_id || ''
              const scope = s.share_scope || 'inheritance'
              const isSelected = shareId === sid
              return (
                <div key={i} style={{
                  background: isSelected ? 'var(--accent-d)' : 'var(--surface2)',
                  border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                  borderRadius: 'var(--r-sm)', padding: '10px 13px',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  transition: 'all .15s',
                }}>
                  <div>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: SCOPE_COL[scope], marginBottom: 3 }}>
                      SHARE #{s.share_index ?? (i + 1)}
                      <span style={{ color: 'var(--text3)', marginLeft: 8, fontSize: 10 }}>{scope}</span>
                    </div>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text2)' }}>
                      {sid.slice(0, 32)}...
                    </div>
                    {s.plan_id && (
                      <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--text3)', marginTop: 2 }}>
                        plan: {s.plan_id.slice(0, 20)}...
                      </div>
                    )}
                  </div>
                  <Btn v={isSelected ? 'primary' : 'ghost'} sm onClick={() => setShareId(isSelected ? '' : sid)}>
                    {isSelected ? '✓ 선택됨' : '선택'}
                  </Btn>
                </div>
              )
            })}
          </div>
        )}
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        {/* 세션 생성 (trustee 전용) */}
        <Card>
          <CardTitle>① Recovery Session 생성</CardTitle>
          {isTrustee ? (
            <>
              <div style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)', marginBottom: 12, lineHeight: 1.8 }}>
                // inheritance_activated 상태에서만 유효<br />
                // 생성 시 수혜자들에게 알림 발송
              </div>
              <Field label="사유">
                <Input value={reason} onChange={e => setReason(e.target.value)} />
              </Field>
              <Btn v="amber" onClick={handleCreateSession} loading={sessionLoading}
                disabled={!planId} style={{ width: '100%', justifyContent: 'center' }}>
                ⚡ 세션 생성
              </Btn>
              {recoveryId && (
                <div style={{
                  fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--green)', marginTop: 10,
                  padding: '8px', background: 'rgba(79,196,160,0.05)',
                  border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', wordBreak: 'break-all',
                }}>
                  SESSION: {recoveryId}
                </div>
              )}
            </>
          ) : (
            <div style={{
              padding: '20px 0', textAlign: 'center',
              fontSize: 12, color: 'var(--text3)', fontFamily: 'var(--mono)', lineHeight: 2,
            }}>
              🔒 Recovery Session 생성은<br />
              <span style={{ color: 'var(--amber)' }}>신탁인(Trustee)</span>만 가능합니다.<br />
              <span style={{ fontSize: 10 }}>신탁인이 세션을 생성하면 알림을 받습니다.</span>
            </div>
          )}
        </Card>

        {/* Share 제출 */}
        <Card>
          <CardTitle>② Share 제출</CardTitle>
          <div style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)', marginBottom: 12, lineHeight: 1.8 }}>
            // 개인키로 share를 복호화한 후 제출
          </div>
          <Field label="Recovery ID">
            <Input placeholder="아래 목록에서 선택하거나 직접 입력"
              value={recoveryId} onChange={e => setRecoveryId(e.target.value)} />
          </Field>
          <Field label="Share ID">
            <Input placeholder="위에서 Share 선택 또는 직접 입력"
              value={shareId} onChange={e => setShareId(e.target.value)} />
          </Field>
          <Field label="복호화된 Payload (JSON)">
            <Textarea placeholder='{"x": 1, "y": "123456..."}'
              value={payload} onChange={e => setPayload(e.target.value)} />
          </Field>
          <Btn v="primary" onClick={handleSubmit} loading={submitLoading}
            disabled={!recoveryId || !shareId || !payload}
            style={{ width: '100%', justifyContent: 'center' }}>
            ↑ Share 제출
          </Btn>
        </Card>
      </div>

      {/* 이 플랜의 Recovery Session 목록 */}
      {planId && (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <CardTitle>이 플랜의 Recovery Session 목록</CardTitle>
            <Btn v="ghost" sm onClick={() => loadSessionList(planId)} loading={sessListLoading}>새로고침</Btn>
          </div>
          {sessionList.length === 0 ? (
            <Empty msg="생성된 Recovery Session이 없습니다" />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {sessionList.map((s, i) => {
                const rid = s.recovery_id || s.id || ''
                const isActive = rid === recoveryId
                return (
                  <div key={i} style={{
                    padding: '11px 13px',
                    background: isActive ? 'var(--accent-d)' : 'var(--surface2)',
                    border: `1px solid ${isActive ? 'var(--accent)' : 'var(--border)'}`,
                    borderRadius: 'var(--r-sm)',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  }}>
                    <div>
                      <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text)', marginBottom: 3 }}>
                        {rid.slice(0, 36)}...
                      </div>
                      <div style={{ display: 'flex', gap: 10, fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)' }}>
                        <span style={{ color: s.status === 'completed' ? 'var(--green)' : 'var(--amber)' }}>
                          {s.status?.toUpperCase() || 'OPEN'}
                        </span>
                        {s.created_at && <span>{new Date(s.created_at).toLocaleString('ko-KR')}</span>}
                        {s.requester_role && <span>by {s.requester_role}</span>}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <Btn v="ghost" sm onClick={() => handleCheckSession(rid)}>상태 조회</Btn>
                      <Btn v={isActive ? 'primary' : 'surface'} sm onClick={() => setRecoveryId(isActive ? '' : rid)}>
                        {isActive ? '✓ 선택됨' : '선택'}
                      </Btn>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </Card>
      )}

      {/* 세션 상태 상세 */}
      {sessionInfo && (
        <Card>
          <CardTitle>세션 상태 상세</CardTitle>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
            <span style={{ fontSize: 12, color: 'var(--text2)' }}>상태</span>
            <span style={{ fontSize: 12, fontWeight: 700, fontFamily: 'var(--mono)',
              color: sessionInfo.status === 'completed' ? 'var(--green)' : 'var(--amber)' }}>
              {sessionInfo.status?.toUpperCase()}
            </span>
          </div>
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11,
              fontFamily: 'var(--mono)', color: 'var(--text3)', marginBottom: 5 }}>
              <span>임계값 진행률</span>
              <span>{sessionInfo.submissions?.length || 0} / {sessionInfo.threshold_required}</span>
            </div>
            <div style={{ height: 4, background: 'var(--border)', borderRadius: 2 }}>
              <div style={{
                height: '100%',
                width: `${Math.min(100, ((sessionInfo.submissions?.length || 0) / sessionInfo.threshold_required) * 100)}%`,
                background: sessionInfo.threshold_result?.success ? 'var(--green)' : 'var(--cyan)',
                borderRadius: 2, transition: 'width 0.4s',
                boxShadow: sessionInfo.threshold_result?.success ? '0 0 6px var(--green)' : 'none',
              }} />
            </div>
          </div>
          {sessionInfo.submissions?.map((s, i) => (
            <div key={i} style={{
              fontSize: 11, color: 'var(--text2)', fontFamily: 'var(--mono)',
              padding: '4px 0', borderTop: i > 0 ? '1px solid var(--border)' : 'none',
            }}>
              <span style={{ color: 'var(--green)' }}>✓</span> {s.actor_role} // {s.share_id?.slice(0, 24)}...
            </div>
          ))}
        </Card>
      )}

      <Card>
        <CardTitle>시스템 로그</CardTitle>
        <LogBox lines={lines} />
      </Card>
    </div>
  )
}

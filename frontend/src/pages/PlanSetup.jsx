import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { useToast, Card, CardTitle, Btn, Field, Input, Select, Textarea, LogBox, useLog, Divider, PageHeader, RoleBadge, Empty } from '../components/UI'
import { getMyPlans, getPlan, createPlan, addParticipant, finalizePlan, setDeadmanPolicy, getUserByUsername } from '../api'

export default function PlanSetup() {
  const { user } = useAuth()
  const toast = useToast()
  const { lines, add } = useLog()

  const [plans, setPlans]       = useState([])
  const [planId, setPlanId]     = useState('')
  const [planDetail, setPlanDetail] = useState(null)

  // 플랜 생성
  const [newTitle, setNewTitle] = useState('')
  const [newDesc, setNewDesc]   = useState('')
  const [creating, setCreating] = useState(false)

  // 참여자 추가
  const [pUsername, setPUsername] = useState('')
  const [pRole, setPRole]         = useState('legal_advisor')
  const [adding, setAdding]       = useState(false)

  // Deadman 정책
  const [checkinDays, setCheckinDays] = useState(30)
  const [graceDays, setGraceDays]     = useState(7)
  const [policyLoading, setPolicyL]   = useState(false)

  // Finalize
  const [finalizing, setFinalizing] = useState(false)

  const loadPlans = async () => {
    try {
      const r = await getMyPlans(user.user_id)
      setPlans(r.data.plans||r.data||[])
    } catch {}
  }

  const loadPlanDetail = async (pid=planId) => {
    if (!pid) return
    try {
      const r = await getPlan(pid)
      setPlanDetail(r.data)
      add(`플랜 로드: ${r.data.title}`, 'ok')
    } catch (e) { add(`오류: ${e.response?.data?.detail||e.message}`, 'err') }
  }

  useEffect(() => { loadPlans() }, [])
  useEffect(() => { loadPlanDetail() }, [planId])

  // 플랜 생성
  const handleCreatePlan = async () => {
    if (!newTitle.trim()) { toast('플랜 이름을 입력하세요', 'err'); return }
    setCreating(true)
    add('POST /plans 요청...', 'info')
    try {
      const r = await createPlan(user.user_id, newTitle, newDesc)
      const pid = r.data.plan_id
      toast('플랜 생성 완료!', 'ok')
      add(`plan_id: ${pid}`, 'ok')
      await loadPlans()
      setPlanId(pid)
      setNewTitle(''); setNewDesc('')
    } catch (e) {
      toast(e.response?.data?.detail||'플랜 생성 실패', 'err')
      add(`오류: ${e.response?.data?.detail||e.message}`, 'err')
    } finally { setCreating(false) }
  }

  // 참여자 추가
  const handleAddParticipant = async () => {
    if (!planId) { toast('플랜을 먼저 선택하세요', 'err'); return }
    if (!pUsername.trim()) { toast('사용자명을 입력하세요', 'err'); return }
    setAdding(true)
    add(`사용자 조회: ${pUsername}`, 'info')
    try {
      const meRes = await getUserByUsername(pUsername)
      const uid = meRes.data.user_id
      await addParticipant(planId, uid, pRole)
      toast(`${pUsername} 추가 완료!`, 'ok')
      add(`참여자 추가: ${pUsername} (${pRole})`, 'ok')
      setPUsername('')
      loadPlanDetail()
    } catch (e) {
      toast(e.response?.data?.detail||'추가 실패 — 사용자명을 확인하세요', 'err')
      add(`오류: ${e.response?.data?.detail||e.message}`, 'err')
    } finally { setAdding(false) }
  }

  // Deadman 정책 설정
  const handleSetPolicy = async () => {
    if (!planId) { toast('플랜을 먼저 선택하세요', 'err'); return }
    setPolicyL(true)
    add('POST /deadman-policy 요청...', 'info')
    try {
      await setDeadmanPolicy(planId, user.user_id, Number(checkinDays), Number(graceDays), true)
      toast('Deadman 정책 설정 완료!', 'ok')
      add(`체크인 주기: ${checkinDays}일, 유예기간: ${graceDays}일`, 'ok')
    } catch (e) {
      toast(e.response?.data?.detail||'설정 실패', 'err')
      add(`오류: ${e.response?.data?.detail||e.message}`, 'err')
    } finally { setPolicyL(false) }
  }

  // Finalize
  const handleFinalize = async () => {
    if (!planId) { toast('플랜을 먼저 선택하세요', 'err'); return }
    if (!confirm('Finalize하면 IK/OK share가 생성되어 참여자들에게 배포됩니다. 진행하시겠습니까?')) return
    setFinalizing(true)
    add('POST /finalize 요청...', 'info')
    try {
      const r = await finalizePlan(planId, user.user_id)
      toast('🎉 Finalize 완료! IK/OK share 배포됨', 'ok')
      add(`IK share: ${r.data.ik_issued_share_ids?.length}개 발급`, 'ok')
      add(`OK share: ${r.data.ok_issued_share_ids?.length}개 발급`, 'ok')
      loadPlanDetail()
    } catch (e) {
      toast(e.response?.data?.detail||'Finalize 실패', 'err')
      add(`오류: ${e.response?.data?.detail||e.message}`, 'err')
    } finally { setFinalizing(false) }
  }

  const isOwner = user.role === 'owner'
  const participants = planDetail?.participants || []
  const canFinalize = planDetail?.status === 'active' || planDetail?.status === 'drafting'

  return (
    <div style={{ padding:28, animation:'fadeUp .3s ease' }}>
      <PageHeader title="플랜 설정" sub="플랜 생성 · 참여자 관리 · Deadman 정책 · Finalize"/>

      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
        <div>
          {/* 플랜 생성 */}
          {isOwner && (
            <Card>
              <CardTitle>① 새 플랜 생성</CardTitle>
              <Field label="플랜 이름">
                <Input placeholder="예: 홍길동의 디지털 유산" value={newTitle} onChange={e=>setNewTitle(e.target.value)}/>
              </Field>
              <Field label="설명 (선택)">
                <Textarea placeholder="플랜 설명..." value={newDesc} onChange={e=>setNewDesc(e.target.value)} style={{ minHeight:60 }}/>
              </Field>
              <Btn v="primary" onClick={handleCreatePlan} loading={creating}>플랜 생성</Btn>
            </Card>
          )}

          {/* 플랜 선택 */}
          <Card>
            <CardTitle>플랜 선택</CardTitle>
            <Select value={planId} onChange={e=>setPlanId(e.target.value)}>
              <option value="">— 플랜을 선택하세요 —</option>
              {plans.map(p => <option key={p.plan_id} value={p.plan_id}>{p.title} ({p.status})</option>)}
            </Select>
            {planDetail && (
              <div style={{ marginTop:12, padding:'10px 13px', background:'var(--surface2)', borderRadius:'var(--r-sm)', fontSize:12, fontFamily:'var(--mono)', color:'var(--text2)', lineHeight:1.8 }}>
                <div>상태: <span style={{ color:'var(--accent)' }}>{planDetail.status}</span></div>
                <div>threshold: <span style={{ color:'var(--text)' }}>{planDetail.share_threshold}-of-{planDetail.share_total}</span></div>
              </div>
            )}
          </Card>

          {/* Deadman 정책 */}
          {isOwner && (
            <Card>
              <CardTitle>③ Deadman 정책 설정</CardTitle>
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:10 }}>
                <Field label="체크인 주기 (일)">
                  <Input type="number" min="1" value={checkinDays} onChange={e=>setCheckinDays(e.target.value)}/>
                </Field>
                <Field label="유예기간 (일)">
                  <Input type="number" min="0" value={graceDays} onChange={e=>setGraceDays(e.target.value)}/>
                </Field>
              </div>
              <div style={{ fontSize:11, color:'var(--text3)', fontFamily:'var(--mono)', marginBottom:12 }}>
                체크인 없이 {checkinDays}일 경과 → Pending / 추가 {graceDays}일 경과 → Escalated
              </div>
              <Btn v="ghost" onClick={handleSetPolicy} loading={policyLoading} disabled={!planId}>정책 저장</Btn>
            </Card>
          )}
        </div>

        <div>
          {/* 참여자 추가 */}
          {isOwner && (
            <Card>
              <CardTitle>② 참여자 추가</CardTitle>
              <Field label="사용자명 (username)">
                <Input placeholder="등록된 사용자명 입력" value={pUsername} onChange={e=>setPUsername(e.target.value)}/>
              </Field>
              <Field label="역할">
                <Select value={pRole} onChange={e=>setPRole(e.target.value)}>
                  <option value="legal_advisor">Legal Advisor (법적 조언자)</option>
                  <option value="trustee">Trustee (신탁인)</option>
                  <option value="beneficiary">Beneficiary (수혜자)</option>
                </Select>
              </Field>
              <Btn v="success" onClick={handleAddParticipant} loading={adding} disabled={!planId}>참여자 추가</Btn>
            </Card>
          )}

          {/* 참여자 목록 */}
          <Card>
            <CardTitle>참여자 목록</CardTitle>
            {participants.length === 0 ? (
              <Empty msg="참여자가 없습니다"/>
            ) : (
              <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
                {participants.map((p, i) => (
                  <div key={i} style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding:'10px 13px', background:'var(--surface2)', borderRadius:'var(--r-sm)', border:'1px solid var(--border)' }}>
                    <div>
                      <div style={{ fontSize:13, fontWeight:700, marginBottom:3 }}>
                        {p.display_name || p.username || p.user_id}
                      </div>
                      <div style={{ fontSize:11, color:'var(--text3)', fontFamily:'var(--mono)', lineHeight:1.7 }}>
                        {p.username && <span style={{ marginRight:8 }}>@{p.username}</span>}
                        <span>{p.user_id}</span>
                      </div>
                    </div>
                    <div style={{ display:'flex', flexDirection:'column', alignItems:'flex-end', gap:4 }}>
                      <RoleBadge role={p.participant_role}/>
                      <span style={{ fontSize:10, color:'var(--text3)', fontFamily:'var(--mono)' }}>{p.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Finalize */}
          {isOwner && (
            <Card style={{ border:'1px solid rgba(124,111,247,.3)', background:'rgba(124,111,247,.04)' }}>
              <CardTitle>④ Finalize</CardTitle>
              <div style={{ fontSize:12, color:'var(--text2)', lineHeight:1.7, marginBottom:14 }}>
                Finalize 실행 시:<br/>
                • IK (상속 키) → Shamir로 분할 → 신탁인/수혜자에게 배포<br/>
                • OK (운영 키) → 2-of-2 분할 → owner + advisor에게 배포<br/>
                • 이후 share를 잃으면 자산 복구 불가
              </div>
              <div style={{ fontSize:11, color:'var(--text3)', fontFamily:'var(--mono)', marginBottom:14 }}>
                필수 조건: legal_advisor 1명↑ · trustee 1명↑ · beneficiary 2명↑
              </div>
              <Btn
                v="primary"
                onClick={handleFinalize}
                loading={finalizing}
                disabled={!planId || !canFinalize || !isOwner}
                style={{ width:'100%', justifyContent:'center' }}
              >
                🔐 Finalize 실행
              </Btn>
              {planDetail?.status === 'inheritance_ready' && (
                <div style={{ marginTop:10, fontSize:12, color:'var(--green)', fontFamily:'var(--mono)' }}>
                  ✅ 이미 Finalize된 플랜입니다
                </div>
              )}
            </Card>
          )}
        </div>
      </div>

      <Card>
        <CardTitle>API 응답 로그</CardTitle>
        <LogBox lines={lines}/>
      </Card>
    </div>
  )
}

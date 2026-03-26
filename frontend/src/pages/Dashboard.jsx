import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import { useToast, Card, CardTitle, StateBadge, StatCard, Btn, Select, LogBox, useLog, PageHeader } from '../components/UI'
import { getMyPlans, getPlanState, getPlanAssets, checkin, evaluateState, approveInheritance } from '../api'

function timeAgo(d) {
  if (!d) return '—'
  const s = (Date.now() - new Date(d)) / 1000
  if (s < 60) return `${Math.floor(s)}초 전`
  if (s < 3600) return `${Math.floor(s/60)}분 전`
  if (s < 86400) return `${Math.floor(s/3600)}시간 전`
  return `${Math.floor(s/86400)}일 전`
}

const TIMELINE = [
  { key:'active',                label:'운영 모드',    desc:'check-in 정상 · 자산 수정 가능' },
  { key:'pending_confirmation',  label:'중단 모드',    desc:'비활성 감지 · owner 알림 발송' },
  { key:'escalated',             label:'경고 모드',    desc:'신탁인 승인 대기 중' },
  { key:'inheritance_activated', label:'상속 모드',    desc:'share 제출 → 자산 복구 가능' },
]
const IDX = { active:0, pending_confirmation:1, escalated:2, inheritance_activated:3, recovered:3 }
const COL = { active:'var(--green)', pending_confirmation:'var(--amber)', escalated:'var(--red)', inheritance_activated:'var(--accent)', recovered:'var(--green)' }

export default function Dashboard() {
  const { user } = useAuth()
  const toast = useToast()
  const { lines, add } = useLog()
  const [plans, setPlans]   = useState([])
  const [planId, setPlanId] = useState('')
  const [state, setState]   = useState(null)
  const [assets, setAssets] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getMyPlans(user.user_id).then(r => setPlans(r.data.plans||r.data||[])).catch(()=>{})
  }, [])

  const loadState = useCallback(async (pid=planId) => {
    if (!pid) return
    try { const r = await getPlanState(pid); setState(r.data); add(`상태: ${r.data.current_state}`, 'ok') }
    catch (e) { add(`오류: ${e.response?.data?.detail||e.message}`, 'err') }
  }, [planId])

  useEffect(() => { loadState(); if (planId) getPlanAssets(planId).then(r=>setAssets(r.data.assets||[])).catch(()=>{}) }, [planId])

  const handleCheckin = async () => {
    setLoading(true); add('POST /checkin 요청...', 'info')
    try { await checkin(planId, user.user_id); toast('체크인 완료!', 'ok'); add('상태 active 유지', 'ok'); loadState() }
    catch (e) { toast(e.response?.data?.detail||'실패', 'err'); add(`오류: ${e.response?.data?.detail||e.message}`, 'err') }
    finally { setLoading(false) }
  }

  const handleEvaluate = async () => {
    add('POST /evaluate-state 요청...', 'info')
    try { await evaluateState(planId); toast('상태 평가 완료', 'ok'); add('평가 완료', 'ok'); loadState() }
    catch (e) { add(`오류: ${e.response?.data?.detail||e.message}`, 'err') }
  }

  const handleApprove = async () => {
    if (!confirm('상속을 승인하면 즉시 상속 모드로 전환됩니다. 진행하시겠습니까?')) return
    add('POST /approve-inheritance 요청...', 'info')
    try { const r = await approveInheritance(planId, user.user_id); toast('상속 승인 완료!', 'ok'); add(r.data.message, 'ok'); loadState() }
    catch (e) { toast(e.response?.data?.detail||'실패', 'err'); add(`오류: ${e.response?.data?.detail||e.message}`, 'err') }
  }

  const curIdx = IDX[state?.current_state] ?? -1
  const curCol = COL[state?.current_state] || 'var(--text2)'

  return (
    <div style={{ padding:28, animation:'fadeUp .3s ease' }}>
      <PageHeader title="대시보드" sub="플랜 상태 확인 및 운영 제어"/>

      <Card>
        <CardTitle>플랜 선택</CardTitle>
        <div style={{ display:'flex', gap:10 }}>
          <Select value={planId} onChange={e=>setPlanId(e.target.value)} style={{ flex:1 }}>
            <option value="">— 플랜을 선택하세요 —</option>
            {plans.map(p => <option key={p.plan_id} value={p.plan_id}>{p.title} ({p.status})</option>)}
          </Select>
          <Btn v="ghost" sm onClick={()=>loadState()} disabled={!planId}>새로고침</Btn>
        </div>
      </Card>

      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:14, marginBottom:16 }}>
        <StatCard label="현재 상태" value={state ? <StateBadge state={state.current_state}/> : '—'}/>
        <StatCard label="마지막 체크인" value={timeAgo(state?.last_checkin_at)} sub={state?.last_checkin_at ? new Date(state.last_checkin_at).toLocaleString('ko-KR') : ''} color={curCol}/>
        <StatCard label="등록 자산" value={assets.length} sub="개"/>
      </div>

      <Card>
        <CardTitle>액션</CardTitle>
        <div style={{ display:'flex', gap:10, flexWrap:'wrap' }}>
          <Btn v="success" onClick={handleCheckin} loading={loading} disabled={!planId||user.role!=='owner'}>✅ 체크인 (나 살아있어요)</Btn>
          <Btn v="ghost" onClick={handleEvaluate} disabled={!planId}>🔍 상태 평가</Btn>
          {user.role==='trustee' && (
            <Btn v="amber" onClick={handleApprove} disabled={!planId||state?.current_state!=='escalated'}>⚡ 상속 승인 (Trustee)</Btn>
          )}
        </div>
        {user.role!=='owner' && <div style={{ fontSize:11, color:'var(--text3)', fontFamily:'var(--mono)', marginTop:8 }}>* 체크인은 owner 계정만 가능합니다</div>}
      </Card>

      {/* 상태머신 타임라인 */}
      <Card>
        <CardTitle>상태 머신</CardTitle>
        <div style={{ display:'flex', flexDirection:'column', gap:0 }}>
          {TIMELINE.map((s, i) => {
            const done = i < curIdx, cur = i === curIdx, locked = i > curIdx
            const col = cur ? COL[s.key] : done ? 'var(--green)' : 'var(--text3)'
            return (
              <div key={s.key} style={{ display:'flex', gap:14, paddingBottom:i<3?20:0, position:'relative', opacity:locked?.4:1 }}>
                {i < 3 && <div style={{ position:'absolute', left:4, top:16, width:2, height:'calc(100% - 10px)', background:done?'var(--green)':'var(--border)' }}/>}
                <div style={{ width:10, height:10, borderRadius:'50%', flexShrink:0, marginTop:5, background:col, boxShadow:cur?`0 0 8px ${col}`:'none', zIndex:1, transition:'all .3s' }}/>
                <div>
                  <div style={{ fontSize:13, fontWeight:700, color:cur?'var(--text)':'var(--text2)', marginBottom:2 }}>
                    {s.label} {cur && <span style={{ fontSize:11, color:'var(--accent)', fontFamily:'var(--mono)' }}>← 현재</span>}
                  </div>
                  <div style={{ fontSize:12, color:'var(--text3)', fontFamily:'var(--mono)' }}>{s.desc}</div>
                </div>
              </div>
            )
          })}
        </div>
      </Card>

      <Card>
        <CardTitle>API 응답 로그</CardTitle>
        <LogBox lines={lines}/>
      </Card>
    </div>
  )
}

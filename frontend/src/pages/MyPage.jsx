import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { useToast, Card, CardTitle, PageHeader, Btn, RoleBadge, Empty } from '../components/UI'
import { getMyShares, getMyPackages, getMyPlans } from '../api'

function CopyRow({ label, value, mono = true }) {
  const toast = useToast()
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true)
      toast(`${label} 복사됨`, 'ok')
      setTimeout(() => setCopied(false), 1500)
    })
  }
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      gap: 12, padding: '10px 13px',
      background: 'var(--surface2)', border: '1px solid var(--border)',
      borderRadius: 'var(--r-sm)', marginBottom: 8,
    }}>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text3)', marginBottom: 3 }}>{label}</div>
        <div style={{
          fontSize: 12, color: 'var(--text)',
          fontFamily: mono ? 'var(--mono)' : 'var(--sans)',
          wordBreak: 'break-all',
        }}>{value || '—'}</div>
      </div>
      <button onClick={copy} style={{
        flexShrink: 0, padding: '5px 12px',
        background: copied ? 'var(--green-d)' : 'transparent',
        border: `1px solid ${copied ? 'var(--green)' : 'var(--border2)'}`,
        borderRadius: 'var(--r-sm)', color: copied ? 'var(--green)' : 'var(--text2)',
        fontSize: 11, fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--sans)',
        transition: 'all .15s',
      }}>
        {copied ? '✓ 복사됨' : '복사'}
      </button>
    </div>
  )
}

const ROLE_KO = { owner: '자산 소유자', legal_advisor: '법률 자문인', trustee: '신탁인', beneficiary: '수혜자' }
const SCOPE_COLOR = { operational: 'var(--cyan)', inheritance: 'var(--green)' }

export default function MyPage() {
  const { user } = useAuth()
  const [shares, setShares]   = useState([])
  const [packages, setPackages] = useState([])
  const [plans, setPlans]     = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getMyShares(user.user_id).then(r => setShares(r.data.shares || [])).catch(() => {}),
      getMyPackages(user.user_id).then(r => setPackages(r.data.packages || [])).catch(() => {}),
      getMyPlans(user.user_id).then(r => setPlans(r.data.plans || r.data || [])).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [])

  return (
    <div style={{ padding: 28, animation: 'fadeUp .3s ease' }}>
      <PageHeader title="마이페이지" sub="계정 정보 · 할당된 Share · 패키지 확인" />

      {/* 계정 정보 */}
      <Card>
        <CardTitle>계정 정보</CardTitle>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
          <div style={{
            width: 52, height: 52, borderRadius: '50%',
            background: 'var(--accent)', display: 'flex', alignItems: 'center',
            justifyContent: 'center', fontSize: 20, fontWeight: 700, color: '#fff', flexShrink: 0,
          }}>
            {(user?.display_name || user?.username || '?')[0].toUpperCase()}
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, marginBottom: 4 }}>{user?.display_name || user?.username}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <RoleBadge role={user?.role} />
              <span style={{ fontSize: 12, color: 'var(--text3)', fontFamily: 'var(--mono)' }}>
                {ROLE_KO[user?.role] || user?.role}
              </span>
            </div>
          </div>
        </div>

        <CopyRow label="내 User ID (시스템 식별자)" value={user?.user_id} />
        <CopyRow label="사용자명 (로그인 ID)" value={user?.username} />
        <CopyRow label="표시 이름" value={user?.display_name} mono={false} />

        <div style={{
          marginTop: 10, padding: '10px 13px',
          background: 'var(--accent-d)', border: '1px solid rgba(124,111,247,.2)',
          borderRadius: 'var(--r-sm)', fontSize: 12, color: 'var(--text2)', lineHeight: 1.7,
        }}>
          💡 <strong style={{ color: 'var(--accent)' }}>User ID</strong>를 다른 참가자에게 공유하면,
          플랜 참가자 추가나 자산 수정 협력 시 사용할 수 있습니다.
        </div>
      </Card>

      {/* 참여 플랜 */}
      <Card>
        <CardTitle>참여 중인 플랜</CardTitle>
        {loading ? (
          <div style={{ color: 'var(--text3)', fontSize: 13, fontFamily: 'var(--mono)' }}>불러오는 중...</div>
        ) : plans.length === 0 ? (
          <Empty msg="참여 중인 플랜이 없습니다" />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {plans.map(p => (
              <div key={p.plan_id} style={{
                padding: '12px 14px', background: 'var(--surface2)',
                border: '1px solid var(--border)', borderRadius: 'var(--r-sm)',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 700 }}>{p.title}</span>
                  <span style={{
                    fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20,
                    background: p.status === 'active' ? 'var(--green-d)' : 'var(--surface3)',
                    color: p.status === 'active' ? 'var(--green)' : 'var(--text2)',
                    textTransform: 'uppercase',
                  }}>{p.status}</span>
                </div>
                <CopyRow label="Plan ID" value={p.plan_id} />
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* 할당된 Shares */}
      {(user?.role === 'owner' || user?.role === 'legal_advisor' || user?.role === 'trustee' || user?.role === 'beneficiary') && (
        <Card>
          <CardTitle>할당된 Share 목록</CardTitle>
          {loading ? (
            <div style={{ color: 'var(--text3)', fontSize: 13, fontFamily: 'var(--mono)' }}>불러오는 중...</div>
          ) : shares.length === 0 ? (
            <Empty msg="할당된 Share가 없습니다" />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {shares.map((s, i) => {
                const sid = s.share_id || s.assigned_share_id || ''
                const scope = s.share_scope || 'inheritance'
                return (
                  <div key={i} style={{
                    padding: '13px 14px', background: 'var(--surface2)',
                    border: '1px solid var(--border)', borderRadius: 'var(--r-sm)',
                    borderLeft: `2px solid ${SCOPE_COLOR[scope] || 'var(--border)'}`,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                      <span style={{ fontSize: 12, fontWeight: 700, fontFamily: 'var(--mono)', color: SCOPE_COLOR[scope] }}>
                        SHARE #{s.share_index ?? (i + 1)}
                      </span>
                      <span style={{
                        fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20,
                        background: scope === 'operational' ? 'var(--cyan-d)' : 'var(--green-d)',
                        color: SCOPE_COLOR[scope], textTransform: 'uppercase',
                      }}>{scope}</span>
                    </div>
                    <CopyRow label="Share ID" value={sid} />
                    {s.plan_id && <CopyRow label="Plan ID" value={s.plan_id} />}
                  </div>
                )
              })}
            </div>
          )}
        </Card>
      )}

      {/* 수혜자 패키지 */}
      {user?.role === 'beneficiary' && (
        <Card>
          <CardTitle>수신된 패키지</CardTitle>
          {loading ? (
            <div style={{ color: 'var(--text3)', fontSize: 13, fontFamily: 'var(--mono)' }}>불러오는 중...</div>
          ) : packages.length === 0 ? (
            <Empty msg="수신된 패키지가 없습니다 (상속 활성화 후 생성됩니다)" />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {packages.map((pkg, i) => (
                <div key={i} style={{
                  padding: '13px 14px', background: 'var(--surface2)',
                  border: '1px solid var(--border)', borderRadius: 'var(--r-sm)',
                  borderLeft: '2px solid var(--accent)',
                }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--accent)', fontFamily: 'var(--mono)', marginBottom: 10 }}>
                    PACKAGE #{i + 1}
                  </div>
                  <CopyRow label="Package ID" value={pkg.package_id} />
                  {pkg.plan_id && <CopyRow label="Plan ID" value={pkg.plan_id} />}
                  {pkg.recovery_id && <CopyRow label="Recovery ID" value={pkg.recovery_id} />}
                  <div style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--mono)', marginTop: 6 }}>
                    생성: {pkg.created_at ? new Date(pkg.created_at).toLocaleString('ko-KR') : '—'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  )
}

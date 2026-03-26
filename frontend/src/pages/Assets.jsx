import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { useToast, Card, CardTitle, Btn, Field, Input, Select, Textarea, LogBox, useLog, PageHeader, Empty } from '../components/UI'
import { getMyPlans, getPlanAssets, updateAsset, getUserByUsername } from '../api'
import http from '../api'

const toBase64Text = (t) => btoa(unescape(encodeURIComponent(t)))
const toBase64File = (f) => new Promise((res, rej) => {
  const r = new FileReader()
  r.onload = () => res(r.result.split(',')[1])
  r.onerror = rej
  r.readAsDataURL(f)
})

export default function Assets() {
  const { user } = useAuth()
  const toast = useToast()
  const { lines, add } = useLog()

  const [plans, setPlans]       = useState([])
  const [planId, setPlanId]     = useState('')
  const [assetList, setAssets]  = useState([])
  const [tab, setTab]           = useState('register')
  const [loading, setLoading]   = useState(false)
  const [file, setFile]         = useState(null)

  const [reg, setReg] = useState({ asset_name: '', asset_type: 'credential', mime_type: '', content: '' })
  const [edit, setEdit] = useState({
    asset_id: '', asset_name_display: '',
    owner_share_id: '', advisor_id: '', advisor_username: '', advisor_share_id: '',
    owner_x: '', owner_y: '', advisor_x: '', advisor_y: '',
    new_asset_name: '', new_content: ''
  })

  useEffect(() => {
    getMyPlans(user.user_id).then(r => setPlans(r.data.plans || r.data || [])).catch(() => {})
  }, [])

  const loadAssets = async (pid = planId) => {
    if (!pid) return
    try { const r = await getPlanAssets(pid); setAssets(r.data.assets || []) } catch {}
  }
  useEffect(() => { loadAssets() }, [planId])

  // 자산 등록
  const handleRegister = async () => {
    if (!planId) { toast('플랜을 선택하세요', 'err'); return }
    if (!reg.asset_name) { toast('자산 이름을 입력하세요', 'err'); return }
    setLoading(true)
    add(`자산 암호화 중: ${reg.asset_type}`, 'info')
    try {
      let content = '', mime = reg.mime_type
      if (reg.asset_type === 'credential') {
        content = toBase64Text(reg.content); mime = 'text/plain'
      } else {
        if (!file) { toast('파일을 선택하세요', 'err'); setLoading(false); return }
        content = await toBase64File(file); mime = file.type
      }
      const r = await http.post('/assets', {
        plan_id: planId, owner_id: user.user_id,
        asset_name: reg.asset_name, asset_type: reg.asset_type,
        mime_type: mime, content
      })
      toast('자산 등록 완료!', 'ok')
      add(`asset_id: ${r.data.asset_id} | 암호화 크기: ${r.data.encrypted_size}B`, 'ok')
      setReg({ asset_name: '', asset_type: 'credential', mime_type: '', content: '' })
      setFile(null)
      loadAssets()
    } catch (e) {
      toast(e.response?.data?.detail || '등록 실패', 'err')
      add(`오류: ${e.response?.data?.detail || e.message}`, 'err')
    } finally { setLoading(false) }
  }

  // 자산 수정 (OK 2-of-2) — 목록에서 선택된 asset 기준
  const handleEdit = async () => {
    if (!edit.asset_id) { toast('수정할 자산을 목록에서 선택하세요', 'err'); return }
    setLoading(true)
    add('PUT /assets (OK 2-of-2) 요청...', 'info')
    try {
      const content = toBase64Text(edit.new_content)
      const r = await updateAsset(edit.asset_id, {
        owner_id: user.user_id,
        advisor_id: edit.advisor_id,
        owner_share_id: edit.owner_share_id,
        advisor_share_id: edit.advisor_share_id,
        owner_decrypted_share_payload: { x: Number(edit.owner_x), y: edit.owner_y },
        advisor_decrypted_share_payload: { x: Number(edit.advisor_x), y: edit.advisor_y },
        new_asset_name: edit.new_asset_name,
        new_content: content,
      })
      toast('자산 수정 완료!', 'ok')
      add(`수정 완료: ${r.data.updated_asset_name}`, 'ok')
      loadAssets()
    } catch (e) {
      toast(e.response?.data?.detail || '수정 실패', 'err')
      add(`오류: ${e.response?.data?.detail || e.message}`, 'err')
    } finally { setLoading(false) }
  }

  // 목록에서 자산 선택 → 수정 탭으로 자동 전환
  const handleSelectForEdit = (a) => {
    setEdit(f => ({
      ...f,
      asset_id: a.asset_id,
      asset_name_display: a.asset_name,
      new_asset_name: a.asset_name,
    }))
    setTab('edit')
  }

  const ASSET_COLOR = { credential: 'var(--accent)', document: 'var(--cyan)', media: 'var(--amber)' }

  return (
    <div style={{ padding: 28, animation: 'fadeUp .3s ease' }}>
      <PageHeader title="자산 관리" sub="AES-256-GCM 암호화 · 등록 및 수정" />

      {/* 플랜 선택 */}
      <Card>
        <CardTitle>플랜 선택</CardTitle>
        <div style={{ display: 'flex', gap: 10 }}>
          <Select value={planId} onChange={e => { setPlanId(e.target.value); setEdit(f => ({ ...f, asset_id: '', asset_name_display: '' })) }} style={{ flex: 1 }}>
            <option value="">— 플랜을 선택하세요 —</option>
            {plans.map(p => <option key={p.plan_id} value={p.plan_id}>{p.title} ({p.status})</option>)}
          </Select>
          <Btn v="ghost" sm onClick={() => loadAssets()}>새로고침</Btn>
        </div>
        {planId && (
          <div style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--mono)', marginTop: 6 }}>
            plan_id: {planId}
          </div>
        )}
      </Card>

      {/* 탭 */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16 }}>
        {[['register', '자산 등록'], ['edit', '자산 수정 (OK 2-of-2)']].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)} style={{
            padding: '8px 18px', borderRadius: 'var(--r-sm)',
            border: tab === k ? 'none' : '1px solid var(--border)',
            background: tab === k ? 'var(--accent)' : 'transparent',
            color: tab === k ? '#fff' : 'var(--text2)',
            fontSize: 13, fontWeight: 700, cursor: 'pointer',
            fontFamily: 'var(--sans)', transition: 'all .15s',
          }}>{l}</button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div>
          {tab === 'register' ? (
            <Card>
              <CardTitle>자산 등록</CardTitle>
              <Field label="자산 이름">
                <Input placeholder="예: GitHub 계정" value={reg.asset_name}
                  onChange={e => setReg(f => ({ ...f, asset_name: e.target.value }))} />
              </Field>
              <Field label="자산 유형">
                <Select value={reg.asset_type}
                  onChange={e => setReg(f => ({ ...f, asset_type: e.target.value, content: '', mime_type: '' }))}>
                  <option value="credential">Credential (텍스트)</option>
                  <option value="document">Document (PDF, DOCX 등)</option>
                  <option value="media">Media (이미지, 영상 등)</option>
                </Select>
              </Field>
              {reg.asset_type === 'credential' ? (
                <Field label="내용">
                  <Textarea placeholder="계정 정보, 비밀번호 등..."
                    value={reg.content} onChange={e => setReg(f => ({ ...f, content: e.target.value }))}
                    style={{ minHeight: 100 }} />
                </Field>
              ) : (
                <Field label={reg.asset_type === 'document' ? '문서 파일' : '미디어 파일'}>
                  <label style={{
                    display: 'flex', alignItems: 'center', gap: 9,
                    background: 'var(--surface2)', border: '1px solid var(--border)',
                    borderRadius: 'var(--r-sm)', padding: '10px 13px',
                    cursor: 'pointer', fontSize: 13,
                    color: file ? 'var(--green)' : 'var(--text2)',
                  }}>
                    📎 {file ? `${file.name} (${(file.size / 1024).toFixed(1)}KB)` : '파일 선택'}
                    <input type="file" style={{ display: 'none' }}
                      accept={reg.asset_type === 'document' ? '.pdf,.doc,.docx,.txt' : '.jpg,.jpeg,.png,.mp4,.mov,.mp3'}
                      onChange={e => { const f = e.target.files[0]; if (f) setFile(f) }} />
                  </label>
                  {file && <div style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--mono)', marginTop: 4 }}>MIME: {file.type}</div>}
                </Field>
              )}
              <Btn v="success" onClick={handleRegister} loading={loading}
                disabled={!planId} style={{ width: '100%', justifyContent: 'center' }}>
                ⬆ 암호화 후 등록
              </Btn>
            </Card>
          ) : (
            <Card>
              <CardTitle>자산 수정 (OK 2-of-2)</CardTitle>
              <div style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 14, lineHeight: 1.7 }}>
                owner + legal_advisor 각자의 OK share를 제출해서 MK를 복구한 후 자산을 수정합니다.
              </div>

              {/* 선택된 자산 표시 */}
              {edit.asset_id ? (
                <div style={{
                  padding: '10px 13px', marginBottom: 14,
                  background: 'var(--accent-d)', border: '1px solid rgba(124,111,247,.3)',
                  borderRadius: 'var(--r-sm)',
                }}>
                  <div style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--mono)', marginBottom: 3 }}>선택된 자산</div>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 3 }}>{edit.asset_name_display}</div>
                  <div style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--mono)', wordBreak: 'break-all' }}>{edit.asset_id}</div>
                  <button onClick={() => setEdit(f => ({ ...f, asset_id: '', asset_name_display: '' }))}
                    style={{ marginTop: 6, fontSize: 11, color: 'var(--red)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'var(--sans)' }}>
                    ✕ 선택 해제
                  </button>
                </div>
              ) : (
                <div style={{
                  padding: '12px', marginBottom: 14,
                  background: 'var(--surface2)', border: '1px dashed var(--border)',
                  borderRadius: 'var(--r-sm)', textAlign: 'center',
                  fontSize: 12, color: 'var(--text3)', fontFamily: 'var(--mono)',
                }}>
                  ← 오른쪽 목록에서 수정할 자산을 선택하세요
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <Field label="Owner Share ID">
                  <Input placeholder="owner share_id" value={edit.owner_share_id}
                    onChange={e => setEdit(f => ({ ...f, owner_share_id: e.target.value }))} />
                </Field>
                <Field label="Owner Share X / Y">
                  <div style={{ display: 'flex', gap: 6 }}>
                    <Input placeholder="x" value={edit.owner_x}
                      onChange={e => setEdit(f => ({ ...f, owner_x: e.target.value }))} style={{ width: '40%' }} />
                    <Input placeholder="y값" value={edit.owner_y}
                      onChange={e => setEdit(f => ({ ...f, owner_y: e.target.value }))} />
                  </div>
                </Field>
                <Field label="Advisor Username">
                  <div style={{ display: 'flex', gap: 8 }}>
                    <Input placeholder="advisor username"
                      value={edit.advisor_username}
                      onChange={e => setEdit(f => ({ ...f, advisor_username: e.target.value }))}
                      style={{ flex: 1 }} />
                    <Btn v="ghost" sm onClick={async () => {
                      try {
                        const r = await getUserByUsername(edit.advisor_username)
                        setEdit(f => ({ ...f, advisor_id: r.data.user_id }))
                        toast('Advisor ID 조회 완료: ' + r.data.user_id, 'ok')
                      } catch { toast('사용자를 찾을 수 없습니다', 'err') }
                    }}>조회</Btn>
                  </div>
                  {edit.advisor_id && (
                    <div style={{ fontSize: 11, color: 'var(--green)', fontFamily: 'var(--mono)', marginTop: 4 }}>
                      ✅ user_id: {edit.advisor_id}
                    </div>
                  )}
                </Field>
                <Field label="Advisor Share ID">
                  <Input placeholder="advisor share_id" value={edit.advisor_share_id}
                    onChange={e => setEdit(f => ({ ...f, advisor_share_id: e.target.value }))} />
                </Field>
                <Field label="Advisor Share X / Y">
                  <div style={{ display: 'flex', gap: 6 }}>
                    <Input placeholder="x" value={edit.advisor_x}
                      onChange={e => setEdit(f => ({ ...f, advisor_x: e.target.value }))} style={{ width: '40%' }} />
                    <Input placeholder="y값" value={edit.advisor_y}
                      onChange={e => setEdit(f => ({ ...f, advisor_y: e.target.value }))} />
                  </div>
                </Field>
                <Field label="새 자산 이름">
                  <Input placeholder="새 이름" value={edit.new_asset_name}
                    onChange={e => setEdit(f => ({ ...f, new_asset_name: e.target.value }))} />
                </Field>
              </div>
              <Field label="새 내용">
                <Textarea placeholder="새 자산 내용..." value={edit.new_content}
                  onChange={e => setEdit(f => ({ ...f, new_content: e.target.value }))} />
              </Field>
              <Btn v="amber" onClick={handleEdit} loading={loading}
                disabled={!edit.asset_id}
                style={{ width: '100%', justifyContent: 'center' }}>
                ✏ 자산 수정 (OK 2-of-2)
              </Btn>
            </Card>
          )}
        </div>

        {/* 자산 목록 */}
        <Card>
          <CardTitle>등록된 자산 목록</CardTitle>
          {!planId ? (
            <div style={{ fontSize: 12, color: 'var(--text3)', fontFamily: 'var(--mono)', padding: '12px 0' }}>
              플랜을 먼저 선택하세요
            </div>
          ) : assetList.length === 0 ? (
            <Empty msg="등록된 자산이 없습니다" />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {assetList.map((a) => {
                const isSelected = edit.asset_id === a.asset_id && tab === 'edit'
                return (
                  <div key={a.asset_id} style={{
                    background: isSelected ? 'var(--accent-d)' : 'var(--surface2)',
                    border: `1px solid ${isSelected ? 'rgba(124,111,247,.4)' : 'var(--border)'}`,
                    borderRadius: 'var(--r-sm)', padding: 13,
                    borderLeft: `2px solid ${ASSET_COLOR[a.asset_type] || 'var(--border)'}`,
                    transition: 'all .15s',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                      <span style={{ fontSize: 13, fontWeight: 700 }}>{a.asset_name}</span>
                      <span style={{ fontSize: 11, fontWeight: 700, color: ASSET_COLOR[a.asset_type], textTransform: 'uppercase' }}>
                        {a.asset_type}
                      </span>
                    </div>
                    <div style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text3)', lineHeight: 1.8 }}>
                      <div>ID: {a.asset_id}</div>
                      <div>크기: {a.encrypted_size || '?'}B 암호화 / {a.original_size || '?'}B 원본</div>
                      {a.mime_type && <div>MIME: {a.mime_type}</div>}
                    </div>
                    <button
                      onClick={() => handleSelectForEdit(a)}
                      style={{
                        marginTop: 7, padding: '5px 12px',
                        background: isSelected ? 'var(--accent)' : 'transparent',
                        border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                        borderRadius: 'var(--r-sm)',
                        color: isSelected ? '#fff' : 'var(--text2)',
                        fontSize: 11, cursor: 'pointer',
                        fontFamily: 'var(--sans)', transition: 'all .15s',
                      }}>
                      {isSelected ? '✓ 선택됨' : '수정하기'}
                    </button>
                  </div>
                )
              })}
            </div>
          )}
        </Card>
      </div>

      <Card>
        <CardTitle>API 응답 로그</CardTitle>
        <LogBox lines={lines} />
      </Card>
    </div>
  )
}

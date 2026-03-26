import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Btn, Field, Input, Select } from '../components/UI'
import http from '../api'

const ROLE_DESC = {
  owner:         '자산 소유자 — 자산 등록/수정, check-in 관리',
  legal_advisor: '법적 조언자 — OK(2-of-2) 운영키 공동 보유',
  trustee:       '신탁인 — 상속 발동 승인 권한 보유',
  beneficiary:   '수혜자 — IK share 보유, 자산 복구 가능',
}

export default function Register() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ username:'', password:'', confirm:'', display_name:'', role:'owner', public_key:'' })
  const [keyFile, setKeyFile] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)

  const handleKeyFile = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setKeyFile(file.name)
    const reader = new FileReader()
    reader.onload = ev => setForm(f => ({ ...f, public_key: ev.target.result }))
    reader.readAsText(file)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.username || !form.password || !form.display_name) { setError('모든 필드를 입력하세요'); return }
    if (form.password !== form.confirm) { setError('비밀번호가 일치하지 않습니다'); return }
    if (form.password.length < 4) { setError('비밀번호는 4자 이상이어야 합니다'); return }
    if (!form.public_key.trim()) { setError('공개키를 등록해주세요'); return }
    setLoading(true)
    try {
      await http.post('/register', { username:form.username, password:form.password, display_name:form.display_name, role:form.role, public_key:form.public_key.trim() })
      setDone(true)
      setTimeout(() => navigate('/login'), 2000)
    } catch (err) {
      setError(err.response?.data?.detail || '회원가입 실패')
    } finally { setLoading(false) }
  }

  return (
    <div style={{ minHeight:'100vh', display:'flex', alignItems:'center', justifyContent:'center', background:'var(--bg)', padding:'24px 0' }}>
      <div style={{ width:480, animation:'fadeUp .4s ease', position:'relative', zIndex:1 }}>
        <div style={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:'var(--r)', padding:'34px 32px' }}>
          <div style={{ marginBottom:24 }}>
            <div style={{ fontSize:20, fontWeight:800, marginBottom:4 }}>계정 생성</div>
            <div style={{ fontSize:12, color:'var(--text2)', fontFamily:'var(--mono)' }}>Digital Legacy System — User Registration</div>
          </div>

          {done ? (
            <div style={{ padding:'32px 0', textAlign:'center' }}>
              <div style={{ fontSize:32, marginBottom:12 }}>✅</div>
              <div style={{ fontSize:16, fontWeight:700, color:'var(--green)', marginBottom:6 }}>가입 완료!</div>
              <div style={{ fontSize:13, color:'var(--text2)' }}>로그인 페이지로 이동합니다...</div>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12 }}>
                <Field label="아이디">
                  <Input placeholder="username" value={form.username} onChange={e=>setForm(f=>({...f,username:e.target.value}))} autoFocus/>
                </Field>
                <Field label="이름">
                  <Input placeholder="홍길동" value={form.display_name} onChange={e=>setForm(f=>({...f,display_name:e.target.value}))}/>
                </Field>
                <Field label="비밀번호">
                  <Input type="password" placeholder="password" value={form.password} onChange={e=>setForm(f=>({...f,password:e.target.value}))}/>
                </Field>
                <Field label="비밀번호 확인">
                  <Input type="password" placeholder="confirm" value={form.confirm} onChange={e=>setForm(f=>({...f,confirm:e.target.value}))}/>
                </Field>
              </div>

              <Field label="역할">
                <Select value={form.role} onChange={e=>setForm(f=>({...f,role:e.target.value}))}>
                  <option value="owner">Owner (소유자)</option>
                  <option value="legal_advisor">Legal Advisor (법적 조언자)</option>
                  <option value="trustee">Trustee (신탁인)</option>
                  <option value="beneficiary">Beneficiary (수혜자)</option>
                </Select>
                <div style={{ fontSize:11, color:'var(--text3)', fontFamily:'var(--mono)', marginTop:5 }}>
                  ℹ {ROLE_DESC[form.role]}
                </div>
              </Field>

              <Field label="공개키 (.pem)">
                <label style={{ display:'flex', alignItems:'center', gap:9, background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:'var(--r-sm)', padding:'9px 13px', cursor:'pointer', fontSize:13, color:keyFile?'var(--green)':'var(--text2)', marginBottom:7 }}>
                  🔑 {keyFile || 'PEM 파일 선택'}
                  <input type="file" accept=".pem,.pub,.txt" style={{ display:'none' }} onChange={handleKeyFile}/>
                </label>
                <textarea
                  placeholder="-----BEGIN PUBLIC KEY-----&#10;...&#10;-----END PUBLIC KEY-----"
                  value={form.public_key}
                  onChange={e=>setForm(f=>({...f,public_key:e.target.value}))}
                  style={{ background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:'var(--r-sm)', color:'var(--amber)', fontFamily:'var(--mono)', fontSize:11, padding:'9px 13px', width:'100%', outline:'none', resize:'vertical', minHeight:64, lineHeight:1.5 }}
                />
                <div style={{ fontSize:11, color:'var(--text3)', fontFamily:'var(--mono)', marginTop:4 }}>
                  test_keys 폴더 → {form.role==='owner'?'owner1':form.role==='legal_advisor'?'advisor1':form.role==='trustee'?'trustee1':'beneficiary1'}_public.pem 사용 가능
                </div>
              </Field>

              {error && <div style={{ fontSize:12, color:'var(--red)', fontFamily:'var(--mono)', marginBottom:12, padding:'8px 11px', background:'var(--red-d)', borderRadius:'var(--r-sm)' }}>❌ {error}</div>}

              <div style={{ display:'flex', gap:10 }}>
                <Btn type="submit" loading={loading} style={{ flex:1, justifyContent:'center' }}>가입하기</Btn>
                <Link to="/login" style={{ display:'inline-flex', alignItems:'center', padding:'10px 18px', borderRadius:'var(--r-sm)', border:'1px solid var(--border)', color:'var(--text2)', fontSize:13, fontWeight:600, textDecoration:'none' }}>로그인</Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}

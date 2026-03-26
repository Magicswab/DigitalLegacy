import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { login as apiLogin, getMe } from '../api'
import { Btn, Field, Input } from '../components/UI'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username:'', password:'' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.username || !form.password) { setError('아이디와 비밀번호를 입력하세요'); return }
    setLoading(true); setError('')
    try {
      const { data } = await apiLogin(form.username, form.password)
      const meRes = await getMe(form.username)
      login({ ...data, ...meRes.data })
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || '로그인 실패 — 백엔드가 실행 중인지 확인하세요')
    } finally { setLoading(false) }
  }

  return (
    <div style={{ minHeight:'100vh', display:'flex', alignItems:'center', justifyContent:'center', background:'var(--bg)' }}>
      <div style={{ position:'fixed', top:'25%', left:'50%', transform:'translateX(-50%)', width:500, height:500, background:'radial-gradient(circle, rgba(124,111,247,0.06) 0%, transparent 70%)', pointerEvents:'none' }}/>
      <div style={{ width:400, animation:'fadeUp .4s ease', position:'relative', zIndex:1 }}>
        <div style={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:'var(--r)', padding:'38px 34px' }}>
          <div style={{ marginBottom:28 }}>
            <div style={{ fontSize:22, fontWeight:800, color:'var(--accent)', marginBottom:6 }}>🔐 Digital Legacy</div>
            <div style={{ fontSize:13, color:'var(--text2)' }}>디지털 자산 상속 관리 시스템</div>
            <div style={{ fontSize:11, color:'var(--text3)', fontFamily:'var(--mono)', marginTop:4 }}>AES-256-GCM · Shamir Secret Sharing · PKI</div>
          </div>

          <form onSubmit={handleSubmit}>
            <Field label="아이디">
              <Input placeholder="username" value={form.username} onChange={e=>setForm(f=>({...f,username:e.target.value}))} autoFocus/>
            </Field>
            <Field label="비밀번호">
              <Input type="password" placeholder="password" value={form.password} onChange={e=>setForm(f=>({...f,password:e.target.value}))}/>
            </Field>
            {error && <div style={{ fontSize:12, color:'var(--red)', fontFamily:'var(--mono)', marginBottom:12, padding:'8px 11px', background:'var(--red-d)', borderRadius:'var(--r-sm)' }}>❌ {error}</div>}
            <Btn type="submit" loading={loading} style={{ width:'100%', justifyContent:'center', marginTop:4 }}>로그인</Btn>
          </form>

          <div style={{ marginTop:16, paddingTop:16, borderTop:'1px solid var(--border)', textAlign:'center', fontSize:13, color:'var(--text2)' }}>
            계정이 없으신가요?{' '}
            <Link to="/register" style={{ color:'var(--accent)', fontWeight:700, textDecoration:'none' }}>회원가입</Link>
          </div>

        </div>
      </div>
    </div>
  )
}

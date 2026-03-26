import { useState, useCallback, createContext, useContext } from 'react'

/* ── Button ── */
export function Btn({ children, v='primary', sm, loading, style={}, ...p }) {
  const base = {
    display:'inline-flex', alignItems:'center', gap:7,
    fontFamily:'var(--sans)', fontWeight:700,
    fontSize: sm ? 12 : 13,
    padding: sm ? '6px 14px' : '10px 20px',
    borderRadius:'var(--r-sm)', border:'none',
    cursor:'pointer', transition:'all .15s',
    opacity: p.disabled||loading ? .4 : 1,
    pointerEvents: p.disabled||loading ? 'none' : 'auto',
  }
  const vs = {
    primary: { background:'var(--accent)', color:'#fff' },
    success: { background:'var(--green)',  color:'#071a14' },
    danger:  { background:'var(--red)',    color:'#fff' },
    amber:   { background:'var(--amber)',  color:'#1a0f00' },
    ghost:   { background:'transparent', border:'1px solid var(--border2)', color:'var(--text2)' },
    surface: { background:'var(--surface2)', border:'1px solid var(--border)', color:'var(--text)' },
  }
  return (
    <button style={{...base, ...vs[v], ...style}} {...p}>
      {loading && <span style={{width:13,height:13,border:'2px solid rgba(255,255,255,.25)',borderTopColor:'#fff',borderRadius:'50%',animation:'spin .6s linear infinite',display:'inline-block',flexShrink:0}}/>}
      {children}
    </button>
  )
}

/* ── Card ── */
export function Card({ children, style={} }) {
  return <div style={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:'var(--r)', padding:22, marginBottom:16, ...style }}>{children}</div>
}

export function CardTitle({ children, action }) {
  return (
    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16 }}>
      <div style={{ fontSize:11, fontWeight:700, letterSpacing:'.1em', textTransform:'uppercase', color:'var(--text2)' }}>{children}</div>
      {action}
    </div>
  )
}

/* ── 상태 배지 ── */
const SM = {
  active:                { bg:'var(--green-d)',  color:'var(--green)',  dot:true,  label:'Active' },
  pending_confirmation:  { bg:'var(--amber-d)',  color:'var(--amber)',  dot:true,  label:'Pending' },
  escalated:             { bg:'var(--red-d)',    color:'var(--red)',    dot:true,  label:'Escalated' },
  inheritance_activated: { bg:'var(--accent-d)', color:'var(--accent)', dot:true,  label:'Inheritance' },
  recovered:             { bg:'var(--green-d)',  color:'var(--green)',  dot:false, label:'Recovered' },
}
export function StateBadge({ state }) {
  const s = SM[state] || { bg:'rgba(136,136,168,.1)', color:'var(--text2)', dot:false, label: state||'—' }
  return (
    <span style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'3px 10px', borderRadius:20, background:s.bg, color:s.color, fontSize:12, fontWeight:600, fontFamily:'var(--mono)' }}>
      {s.dot && <span style={{ width:6, height:6, borderRadius:'50%', background:s.color, flexShrink:0, animation:'pulse 2s ease-in-out infinite' }}/>}
      {s.label}
    </span>
  )
}

export function RoleBadge({ role }) {
  const c = { owner:'var(--accent)', legal_advisor:'var(--green)', trustee:'var(--amber)', beneficiary:'var(--text2)' }
  const b = { owner:'var(--accent-d)', legal_advisor:'var(--green-d)', trustee:'var(--amber-d)', beneficiary:'rgba(136,136,168,.1)' }
  return <span style={{ fontSize:11, fontWeight:700, padding:'2px 8px', borderRadius:20, background:b[role]||b.beneficiary, color:c[role]||c.beneficiary, textTransform:'uppercase', letterSpacing:'.05em' }}>{role}</span>
}

/* ── Field / Input ── */
export function Field({ label, children, style={} }) {
  return (
    <div style={{ marginBottom:14, ...style }}>
      {label && <label style={{ display:'block', fontSize:11, fontWeight:700, letterSpacing:'.08em', textTransform:'uppercase', color:'var(--text2)', marginBottom:5 }}>{label}</label>}
      {children}
    </div>
  )
}

const iBase = { background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:'var(--r-sm)', color:'var(--text)', fontFamily:'var(--mono)', fontSize:13, padding:'10px 13px', width:'100%', outline:'none', transition:'border .15s' }

export function Input({ style={}, ...p }) {
  return <input style={{...iBase,...style}} onFocus={e=>e.target.style.borderColor='var(--accent)'} onBlur={e=>e.target.style.borderColor='var(--border)'} {...p}/>
}
export function Textarea({ style={}, ...p }) {
  return <textarea style={{...iBase,resize:'vertical',minHeight:80,lineHeight:1.6,...style}} onFocus={e=>e.target.style.borderColor='var(--accent)'} onBlur={e=>e.target.style.borderColor='var(--border)'} {...p}/>
}
export function Select({ children, style={}, ...p }) {
  return <select style={{...iBase,cursor:'pointer',...style}} onFocus={e=>e.target.style.borderColor='var(--accent)'} onBlur={e=>e.target.style.borderColor='var(--border)'} {...p}>{children}</select>
}

/* ── LogBox ── */
export function LogBox({ lines=[] }) {
  return (
    <div style={{ background:'#070710', border:'1px solid var(--border)', borderRadius:'var(--r-sm)', padding:13, fontFamily:'var(--mono)', fontSize:12, lineHeight:1.7, maxHeight:180, overflowY:'auto', color:'var(--text2)' }}>
      {lines.length===0 ? <span style={{color:'var(--text3)'}}>API 응답 대기중...</span>
        : lines.map((l,i) => <div key={i} style={{ color:l.type==='ok'?'var(--green)':l.type==='err'?'var(--red)':l.type==='info'?'var(--accent)':'var(--text2)' }}>{l.text}</div>)}
    </div>
  )
}

/* ── Spinner / Divider ── */
export function Spinner({ size=20 }) {
  return <div style={{ width:size, height:size, border:'2px solid var(--border2)', borderTopColor:'var(--accent)', borderRadius:'50%', animation:'spin .6s linear infinite' }}/>
}
export function Divider() {
  return <div style={{ borderTop:'1px solid var(--border)', margin:'18px 0' }}/>
}

/* ── Toast ── */
const TC = createContext(null)
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const push = useCallback((msg, type='info') => {
    const id = Date.now()
    setToasts(t => [...t, { id, msg, type }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3500)
  }, [])
  const cc = { ok:'var(--green)', err:'var(--red)', info:'var(--accent)', warn:'var(--amber)' }
  return (
    <TC.Provider value={push}>
      {children}
      <div style={{ position:'fixed', bottom:22, right:22, display:'flex', flexDirection:'column', gap:7, zIndex:9999 }}>
        {toasts.map(t => (
          <div key={t.id} style={{ background:'var(--surface2)', border:`1px solid ${cc[t.type]}`, borderRadius:'var(--r-sm)', padding:'11px 15px', fontSize:13, fontFamily:'var(--mono)', color:cc[t.type], display:'flex', gap:8, maxWidth:320, animation:'fadeUp .2s ease' }}>
            {t.type==='ok'?'✅':t.type==='err'?'❌':t.type==='warn'?'⚠️':'ℹ️'} {t.msg}
          </div>
        ))}
      </div>
    </TC.Provider>
  )
}
export const useToast = () => useContext(TC)

/* ── useLog ── */
export function useLog() {
  const [lines, setLines] = useState([])
  const add = useCallback((text, type='default') => {
    const t = new Date().toLocaleTimeString('ko-KR', { hour12:false })
    setLines(l => [...l.slice(-60), { text:`[${t}] ${text}`, type }])
  }, [])
  return { lines, add }
}

/* ── Stat Card ── */
export function StatCard({ label, value, sub, color }) {
  return (
    <div style={{ background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:'var(--r)', padding:18 }}>
      <div style={{ fontSize:11, fontWeight:700, letterSpacing:'.08em', textTransform:'uppercase', color:'var(--text2)', marginBottom:8 }}>{label}</div>
      <div style={{ fontSize:22, fontWeight:800, fontFamily:'var(--mono)', color:color||'var(--text)' }}>{value}</div>
      {sub && <div style={{ fontSize:11, color:'var(--text3)', marginTop:4, fontFamily:'var(--mono)' }}>{sub}</div>}
    </div>
  )
}

/* ── PageHeader ── */
export function PageHeader({ title, sub }) {
  return (
    <div style={{ marginBottom:22 }}>
      <div style={{ fontSize:20, fontWeight:800 }}>{title}</div>
      {sub && <div style={{ fontSize:12, color:'var(--text2)', fontFamily:'var(--mono)', marginTop:3 }}>{sub}</div>}
    </div>
  )
}

/* ── Empty State ── */
export function Empty({ msg='데이터가 없습니다' }) {
  return <div style={{ padding:'32px 0', textAlign:'center', fontSize:13, color:'var(--text3)', fontFamily:'var(--mono)' }}>{msg}</div>
}

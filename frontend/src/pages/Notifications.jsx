import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { useToast, Card, CardTitle, PageHeader, Empty, Btn, Spinner } from '../components/UI'
import { getNotifications, markNotificationRead } from '../api'

const NOTIF_CFG = {
  deadman_pending_confirmation: { icon:'⚠', color:'var(--amber)', label:'DEADMAN TRIGGER' },
  inheritance_approval_request: { icon:'⚡', color:'var(--cyan)',  label:'APPROVAL REQUEST' },
  inheritance_activated:        { icon:'◈', color:'var(--green)', label:'INHERITANCE ACTIVE' },
  checkin_reminder:             { icon:'◎', color:'var(--text2)', label:'CHECKIN REMINDER' },
}

export default function Notifications() {
  const { user } = useAuth()
  const toast = useToast()
  const [notifs, setNotifs]   = useState([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter]   = useState('all')

  const load = async () => {
    setLoading(true)
    try {
      const r = await getNotifications(user.user_id)
      setNotifs(r.data.notifications||[])
    } catch { toast('failed to load', 'err') }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const handleRead = async (id) => {
    try {
      await markNotificationRead(id, user.user_id)
      setNotifs(n => n.map(x => x.notification_id===id ? {...x,is_read:true} : x))
    } catch {}
  }

  const handleReadAll = async () => {
    const unread = notifs.filter(n=>!n.is_read)
    await Promise.all(unread.map(n=>markNotificationRead(n.notification_id, user.user_id)))
    setNotifs(n=>n.map(x=>({...x,is_read:true})))
    toast(`${unread.length} marked as read`, 'ok')
  }

  const filtered = filter==='unread' ? notifs.filter(n=>!n.is_read) : notifs
  const unreadCount = notifs.filter(n=>!n.is_read).length

  return (
    <div style={{ padding:'24px 28px', overflowY:'auto', flex:1, animation:'fadeUp 0.3s ease' }}>

      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-end', marginBottom:20 }}>
        <div>
          <div style={{ fontFamily:'var(--title)', fontSize:14, color:'var(--green)', letterSpacing:'0.15em', textShadow:'0 0 10px rgba(0,255,136,0.3)', marginBottom:4 }}>
            NOTIFICATIONS
          </div>
          <div style={{ fontFamily:'var(--mono)', fontSize:10, color:'var(--text2)', letterSpacing:'0.08em' }}>
            STATE ALERTS // APPROVAL REQUESTS // SYSTEM EVENTS
          </div>
        </div>
        <div style={{ display:'flex', gap:8 }}>
          {unreadCount>0 && <Btn v="ghost" size="sm" onClick={handleReadAll}>MARK ALL READ</Btn>}
          <Btn v="ghost" size="sm" onClick={load} loading={loading}>REFRESH</Btn>
        </div>
      </div>

      {/* 필터 */}
      <div style={{ display:'flex', gap:6, marginBottom:14 }}>
        {[['all','ALL'],['unread','UNREAD']].map(([val,label]) => (
          <button key={val} onClick={()=>setFilter(val)} style={{
            padding:'5px 14px', border:'1px solid',
            borderColor: filter===val ? 'var(--green)' : 'var(--border)',
            background: filter===val ? 'rgba(0,255,136,0.08)' : 'transparent',
            color: filter===val ? 'var(--green)' : 'var(--text2)',
            fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.1em',
            cursor:'pointer', borderRadius:'var(--radius)', transition:'all 0.15s',
            textShadow: filter===val ? '0 0 6px rgba(0,255,136,0.3)' : 'none'
          }}>
            {label}
            {val==='unread' && unreadCount>0 && (
              <span style={{ marginLeft:6, color:'var(--red)', fontSize:9 }}>[{unreadCount}]</span>
            )}
          </button>
        ))}
      </div>

      <Card>
        {loading ? (
          <div style={{ display:'flex', justifyContent:'center', padding:32 }}><Spinner/></div>
        ) : filtered.length===0 ? (
          <div style={{ padding:32, textAlign:'center', fontFamily:'var(--mono)', fontSize:10, color:'var(--text3)' }}>
            no notifications_
          </div>
        ) : (
          filtered.map((n,i) => {
            const cfg = NOTIF_CFG[n.notification_type] || { icon:'◎', color:'var(--text2)', label:n.notification_type?.toUpperCase()||'EVENT' }
            return (
              <div key={n.notification_id} style={{
                display:'flex', alignItems:'flex-start', gap:14,
                padding:'14px 0',
                borderBottom: i<filtered.length-1 ? '1px solid var(--border)' : 'none',
                opacity: n.is_read ? 0.45 : 1,
                transition:'opacity 0.2s'
              }}>
                {/* 아이콘 */}
                <div style={{
                  fontFamily:'var(--mono)', fontSize:16, flexShrink:0, marginTop:2,
                  color: cfg.color, textShadow:`0 0 8px ${cfg.color}66`
                }}>
                  {cfg.icon}
                </div>

                <div style={{ flex:1 }}>
                  <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:4 }}>
                    <span style={{
                      fontFamily:'var(--mono)', fontSize:9, color:cfg.color,
                      letterSpacing:'0.15em',
                      textShadow: !n.is_read ? `0 0 6px ${cfg.color}66` : 'none'
                    }}>
                      {cfg.label}
                    </span>
                    {!n.is_read && (
                      <span style={{ width:5, height:5, borderRadius:'50%', background:'var(--green)',
                        display:'inline-block', boxShadow:'0 0 4px var(--green)',
                        animation:'glowPulse 2s ease-in-out infinite' }}/>
                    )}
                  </div>
                  <div style={{ fontFamily:'var(--body)', fontSize:13, marginBottom:4, lineHeight:1.5, color:'var(--text)' }}>
                    {n.message}
                  </div>
                  <div style={{ fontFamily:'var(--mono)', fontSize:9, color:'var(--text3)' }}>
                    {n.created_at ? new Date(n.created_at).toLocaleString('ko-KR') : '—'}
                    {n.plan_id && <span style={{marginLeft:12}}>PLAN: {n.plan_id.slice(0,16)}...</span>}
                  </div>
                </div>

                {!n.is_read && (
                  <Btn v="ghost" size="sm" onClick={()=>handleRead(n.notification_id)}>
                    READ
                  </Btn>
                )}
              </div>
            )
          })
        )}
      </Card>
    </div>
  )
}

import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useEffect, useState } from 'react'
import { getNotifications } from '../api'
import { RoleBadge } from './UI'

// roles: null = 전체 허용, 배열 = 해당 role만 허용
const ALL_NAV = [
  { to: '/dashboard',     icon: '▦',  label: '대시보드',   roles: null },
  { to: '/plan-setup',    icon: '◎',  label: '플랜 설정',  roles: ['owner'] },
  { to: '/assets',        icon: '◇',  label: '자산 관리',  roles: ['owner'] },
  { to: '/shares',        icon: '⬡',  label: 'Share 제출', roles: ['legal_advisor', 'trustee', 'beneficiary'] },
  { to: '/recovery',      icon: '↺',  label: '자산 복구',  roles: ['beneficiary'] },
  { to: '/notifications', icon: '◉',  label: '알림',       roles: null },
  { to: '/mypage',        icon: '◈',  label: '마이페이지', roles: null },
]

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [unread, setUnread] = useState(0)

  const navItems = ALL_NAV.filter(item =>
    item.roles === null || item.roles.includes(user?.role)
  )

  useEffect(() => {
    if (!user) return
    const load = async () => {
      try {
        const r = await getNotifications(user.user_id)
        setUnread((r.data.notifications || []).filter(n => !n.is_read).length)
      } catch {}
    }
    load()
    const id = setInterval(load, 15000)
    return () => clearInterval(id)
  }, [user])

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* 사이드바 */}
      <aside style={{
        width: 220, flexShrink: 0, minHeight: '100vh',
        background: 'var(--surface)', borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', padding: '24px 14px',
      }}>
        {/* 로고 */}
        <div style={{ padding: '0 6px 22px', borderBottom: '1px solid var(--border)', marginBottom: 18 }}>
          <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--accent)', letterSpacing: '.05em' }}>🔐 Digital Legacy</div>
          <div style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--mono)', marginTop: 3 }}>상속 키 관리 시스템</div>
        </div>

        {/* 네비 */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 3, flex: 1 }}>
          {navItems.map(item => (
            <NavLink key={item.to} to={item.to} style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: 9,
              padding: '9px 11px', borderRadius: 'var(--r-sm)',
              fontSize: 13, fontWeight: 600, textDecoration: 'none',
              color: isActive ? '#fff' : 'var(--text2)',
              background: isActive ? 'var(--accent)' : 'transparent',
              transition: 'all .15s', position: 'relative',
            })}>
              <span style={{ fontSize: 14, flexShrink: 0 }}>{item.icon}</span>
              {item.label}
              {item.to === '/notifications' && unread > 0 && (
                <span style={{
                  marginLeft: 'auto', background: 'var(--red)', color: '#fff',
                  fontSize: 10, fontWeight: 700, width: 17, height: 17,
                  borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>{unread}</span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* 유저 */}
        <div style={{ borderTop: '1px solid var(--border)', paddingTop: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 11 }}>
            <div style={{
              width: 32, height: 32, borderRadius: '50%',
              background: 'var(--accent)', display: 'flex', alignItems: 'center',
              justifyContent: 'center', fontSize: 13, fontWeight: 700, color: '#fff', flexShrink: 0,
            }}>
              {(user?.display_name || user?.username || '?')[0].toUpperCase()}
            </div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700 }}>{user?.display_name || user?.username}</div>
              <RoleBadge role={user?.role} />
            </div>
          </div>
          <button
            onClick={() => { logout(); navigate('/login') }}
            style={{
              width: '100%', padding: '8px', borderRadius: 'var(--r-sm)',
              background: 'transparent', border: '1px solid var(--border)',
              color: 'var(--text2)', fontSize: 12, fontWeight: 600,
              cursor: 'pointer', fontFamily: 'var(--sans)', transition: 'all .15s',
            }}
            onMouseEnter={e => { e.target.style.borderColor = 'var(--red)'; e.target.style.color = 'var(--red)' }}
            onMouseLeave={e => { e.target.style.borderColor = 'var(--border)'; e.target.style.color = 'var(--text2)' }}
          >
            로그아웃
          </button>
        </div>
      </aside>

      {/* 메인 */}
      <main style={{ flex: 1, overflowY: 'auto' }}>{children}</main>
    </div>
  )
}

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ToastProvider } from './components/UI'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import PlanSetup from './pages/PlanSetup'
import Assets from './pages/Assets'
import Shares from './pages/Shares'
import Recovery from './pages/Recovery'
import Notifications from './pages/Notifications'
import MyPage from './pages/MyPage'

function PrivateRoute({ children }) {
  const { user } = useAuth()
  return user ? children : <Navigate to="/login" replace />
}

// role 제한 라우트: 허용 roles 목록에 없으면 dashboard로
function RoleRoute({ children, roles }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) return <Navigate to="/dashboard" replace />
  return children
}

function AppRoutes() {
  const { user } = useAuth()
  const wrap = (Page) => <PrivateRoute><Layout><Page/></Layout></PrivateRoute>
  const wrapRole = (Page, roles) => (
    <RoleRoute roles={roles}><Layout><Page/></Layout></RoleRoute>
  )
  return (
    <Routes>
      <Route path="/login"    element={user ? <Navigate to="/dashboard"/> : <Login/>}/>
      <Route path="/register" element={user ? <Navigate to="/dashboard"/> : <Register/>}/>
      <Route path="/"              element={<Navigate to="/dashboard"/>}/>
      <Route path="/dashboard"     element={wrap(Dashboard)}/>
      <Route path="/plan-setup"    element={wrapRole(PlanSetup, ['owner'])}/>
      <Route path="/assets"        element={wrapRole(Assets, ['owner'])}/>
      <Route path="/shares"        element={wrapRole(Shares, ['legal_advisor', 'trustee', 'beneficiary'])}/>
      <Route path="/recovery"      element={wrapRole(Recovery, ['beneficiary'])}/>
      <Route path="/notifications" element={wrap(Notifications)}/>
      <Route path="/mypage"        element={wrap(MyPage)}/>
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <AppRoutes/>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

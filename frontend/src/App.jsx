import React, { useEffect, useState } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { api } from './lib/api'
import { AppBg, Spinner, ToastProvider } from './components/ui'
import Login from './pages/Login'
import Clienti from './pages/Clienti'
import Cliente from './pages/Cliente'

function Splash() {
  return (
    <div style={{ height: '100vh', display: 'grid', placeItems: 'center' }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
        <div style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.02em' }}>
          PED <span style={{ color: 'var(--brand)' }}>Manager</span>
        </div>
        <Spinner size={22} />
      </div>
    </div>
  )
}

export default function App() {
  const [auth, setAuth] = useState(null) // null=loading | false | {username}
  const navigate = useNavigate()

  useEffect(() => {
    api.me().then((d) => setAuth(d && d.auth ? d : false)).catch(() => setAuth(false))
  }, [])

  const onLogin = (me) => { setAuth(me); navigate('/') }
  const onLogout = async () => { try { await api.logout() } catch {} setAuth(false); navigate('/login') }

  return (
    <ToastProvider>
      <AppBg />
      {auth === null ? (
        <Splash />
      ) : (
        <Routes>
          <Route path="/login" element={auth ? <Navigate to="/" /> : <Login onLogin={onLogin} />} />
          <Route path="/" element={auth ? <Clienti onLogout={onLogout} /> : <Navigate to="/login" />} />
          <Route path="/cliente/:id" element={auth ? <Cliente onLogout={onLogout} /> : <Navigate to="/login" />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      )}
    </ToastProvider>
  )
}

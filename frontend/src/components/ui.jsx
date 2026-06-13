import React, { useEffect, useState, createContext, useContext, useCallback } from 'react'
import { getTheme, applyTheme } from '../theme/clients'

/* sfondo aurora a tutta pagina */
export function AppBg() {
  return <div className="app-bg" />
}

/* toggle tema: auto → light → dark */
export function ThemeToggle() {
  const [mode, setMode] = useState(getTheme())
  const cycle = () => {
    const next = mode === 'auto' ? 'light' : mode === 'light' ? 'dark' : 'auto'
    setMode(next); applyTheme(next)
  }
  const icon = mode === 'auto' ? '🌗' : mode === 'light' ? '☀️' : '🌙'
  const label = mode === 'auto' ? 'Auto' : mode === 'light' ? 'Chiaro' : 'Scuro'
  return (
    <button onClick={cycle} className="btn btn-ghost" style={{ padding: '9px 13px', fontSize: 13 }} title={`Tema: ${label}`}>
      <span style={{ fontSize: 15 }}>{icon}</span><span className="hide-sm">{label}</span>
    </button>
  )
}

/* card glass */
export function Card({ className = '', hover = false, style, children, ...p }) {
  return (
    <div className={`glass ${hover ? 'glass-hover' : ''} ${className}`}
      style={{ borderRadius: 20, ...style }} {...p}>
      {children}
    </div>
  )
}

/* spinner */
export function Spinner({ size = 16 }) {
  return (
    <span style={{
      display: 'inline-block', width: size, height: size,
      border: '2px solid color-mix(in srgb, var(--text) 18%, transparent)',
      borderTopColor: 'var(--brand)', borderRadius: '50%',
      animation: 'spin .6s linear infinite', verticalAlign: 'middle',
    }} />
  )
}

/* ─────────── TOAST ─────────── */
const ToastCtx = createContext(() => {})
export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }) {
  const [items, setItems] = useState([])
  const toast = useCallback((msg, tipo = 'ok') => {
    const id = Math.random().toString(36).slice(2)
    setItems((x) => [...x, { id, msg, tipo }])
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 3400)
  }, [])
  const color = { ok: 'var(--brand)', err: '#f87171', info: '#60a5fa' }
  return (
    <ToastCtx.Provider value={toast}>
      {children}
      <div style={{ position: 'fixed', left: 22, bottom: 22, zIndex: 9999, display: 'flex', flexDirection: 'column', gap: 10 }}>
        {items.map((i) => (
          <div key={i.id} className="glass-2 pop" style={{
            borderRadius: 14, padding: '12px 16px', fontSize: 13.5, fontWeight: 600, maxWidth: 360,
            borderLeft: `3px solid ${color[i.tipo]}`, color: 'var(--text)',
          }}>{i.msg}</div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

/* hook: chiude su ESC */
export function useEsc(onEsc, active = true) {
  useEffect(() => {
    if (!active) return
    const h = (e) => { if (e.key === 'Escape') onEsc() }
    document.addEventListener('keydown', h)
    return () => document.removeEventListener('keydown', h)
  }, [onEsc, active])
}

const spinKeyframes = document.createElement('style')
spinKeyframes.textContent = '@keyframes spin{to{transform:rotate(360deg)}} .hide-sm{}@media(max-width:680px){.hide-sm{display:none}}'
document.head.appendChild(spinKeyframes)

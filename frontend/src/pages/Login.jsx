import React, { useState } from 'react'
import { api } from '../lib/api'
import { Card, ThemeToggle, Spinner } from '../components/ui'

export default function Login({ onLogin }) {
  const [u, setU] = useState('')
  const [p, setP] = useState('')
  const [ricordami, setRicordami] = useState(true)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [hp, setHp] = useState('') // honeypot

  const submit = async (e) => {
    e.preventDefault()
    if (busy) return
    setErr(''); setBusy(true)
    try {
      const d = await api.login(u, p, ricordami)
      if (d && d.ok) onLogin(d)
      else { setErr(d?.errore || 'Credenziali non valide.'); setBusy(false) }
    } catch (e) { setErr('Errore di connessione.'); setBusy(false) }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 20 }}>
      <div style={{ position: 'fixed', top: 18, right: 18 }}><ThemeToggle /></div>

      <Card className="rise" style={{ width: 410, maxWidth: '95vw', padding: '40px 36px' }}>
        <div style={{ fontSize: 13, fontWeight: 800, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--brand-strong)' }}>
          Agency
        </div>
        <h1 style={{ fontSize: 30, fontWeight: 800, letterSpacing: '-0.03em', margin: '6px 0 4px' }}>
          PED <span style={{
            background: 'linear-gradient(135deg, var(--brand-bright), var(--brand))',
            WebkitBackgroundClip: 'text', backgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>Manager</span>
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 26 }}>Accesso riservato alla piattaforma</p>

        {err && (
          <div className="pop" style={{
            background: 'color-mix(in srgb, #f87171 14%, transparent)', border: '1px solid color-mix(in srgb,#f87171 35%,transparent)',
            color: '#fca5a5', borderRadius: 12, padding: '11px 14px', fontSize: 13, marginBottom: 16,
          }}>⚠ {err}</div>
        )}

        <form onSubmit={submit} autoComplete="off">
          <label style={lbl}>Username</label>
          <input className="field" value={u} onChange={(e) => setU(e.target.value)} autoFocus required style={{ marginBottom: 16 }} />
          <label style={lbl}>Password</label>
          <input className="field" type="password" value={p} onChange={(e) => setP(e.target.value)} required style={{ marginBottom: 18 }} />
          <input type="text" value={hp} onChange={(e) => setHp(e.target.value)} tabIndex={-1} autoComplete="off"
            style={{ position: 'absolute', left: -9999, opacity: 0, height: 0, width: 0 }} />

          <label style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13.5, color: 'var(--text-muted)', marginBottom: 22, cursor: 'pointer' }}>
            <input type="checkbox" checked={ricordami} onChange={(e) => setRicordami(e.target.checked)}
              style={{ width: 17, height: 17, accentColor: 'var(--brand)' }} />
            Resta connesso su questo dispositivo
          </label>

          <button className="btn btn-brand" type="submit" disabled={busy} style={{ width: '100%', justifyContent: 'center', padding: 14, fontSize: 15 }}>
            {busy ? <Spinner /> : 'Accedi →'}
          </button>
        </form>
      </Card>
    </div>
  )
}

const lbl = { display: 'block', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-faint)', margin: '0 0 7px 3px', fontWeight: 700 }

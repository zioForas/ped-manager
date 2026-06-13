import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { Card, ThemeToggle, Spinner, useToast, useEsc } from '../components/ui'

const STATI = {
  approvato: { t: 'Approvato', c: 'var(--brand)' },
  in_attesa: { t: 'In attesa', c: '#60a5fa' },
  modifiche_richieste: { t: 'Modifiche', c: '#fb923c' },
  schedulato: { t: 'Programmato', c: '#a78bfa' },
  non_inviato: { t: 'Non inviato', c: 'var(--text-faint)' },
}

export default function Clienti({ onLogout }) {
  const [clienti, setClienti] = useState(null)
  const [showNew, setShowNew] = useState(false)
  const navigate = useNavigate()
  const toast = useToast()

  const carica = () => api.clienti().then((d) => setClienti(d.clienti || [])).catch(() => setClienti([]))
  useEffect(() => { carica() }, [])

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '0 22px' }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '20px 0 8px', position: 'sticky', top: 0, zIndex: 20 }}>
        <div className="glass-2" style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '12px 18px', borderRadius: 16, width: '100%' }}>
          <div style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em' }}>
            PED <span style={{ color: 'var(--brand)' }}>Manager</span>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 10 }}>
            <button className="btn btn-brand" onClick={() => setShowNew(true)}>+ Nuovo cliente</button>
            <ThemeToggle />
            <button className="btn btn-ghost" onClick={onLogout}>Esci</button>
          </div>
        </div>
      </header>

      <div style={{ padding: '26px 0 14px' }}>
        <h1 style={{ fontSize: 30, fontWeight: 800, letterSpacing: '-0.03em' }}>Clienti</h1>
        <p style={{ color: 'var(--text-muted)', marginTop: 4 }}>Seleziona un cliente per gestire il suo piano editoriale.</p>
      </div>

      {clienti === null ? (
        <div style={{ padding: 60, textAlign: 'center' }}><Spinner size={24} /></div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(300px,1fr))', gap: 16, paddingBottom: 50 }}>
          {clienti.map((c, i) => {
            const st = STATI[c.stato] || STATI.non_inviato
            return (
              <Card key={c.id} hover className="rise" style={{ padding: 22, cursor: 'pointer', animationDelay: `${i * 40}ms` }}
                onClick={() => navigate(`/cliente/${c.id}`)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{
                    width: 46, height: 46, borderRadius: 14, display: 'grid', placeItems: 'center', fontWeight: 800, fontSize: 16,
                    background: 'var(--brand-soft)', color: 'var(--brand-strong)', border: '1px solid var(--brand-border)',
                  }}>{(c.nome || c.id).slice(0, 2).toUpperCase()}</div>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, fontWeight: 700, color: st.c }}>
                    <span style={{ width: 8, height: 8, borderRadius: 99, background: st.c }} />{st.t}
                  </span>
                </div>
                <div style={{ fontSize: 17, fontWeight: 700, marginTop: 16, letterSpacing: '-0.01em' }}>{c.nome}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 3 }}>{c.periodo}</div>
                <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
                  {c.ped_exists && <span className="chip" style={{ textTransform: 'none' }}>PED</span>}
                  {c.pdf_exists && <span className="chip" style={{ textTransform: 'none' }}>PDF</span>}
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {showNew && <ModalNuovo onClose={() => setShowNew(false)} onCreated={(id) => { setShowNew(false); toast('Cliente creato'); navigate(`/cliente/${id}`) }} />}
    </div>
  )
}

function ModalNuovo({ onClose, onCreated }) {
  const [f, setF] = useState({ id: '', nome: '', email: '', sito: '' })
  const [busy, setBusy] = useState(false)
  const toast = useToast()
  useEsc(onClose)
  const crea = async () => {
    if (!f.nome) return toast('Inserisci il nome', 'err')
    setBusy(true)
    const d = await api.nuovoCliente({ ...f, id: f.id || f.nome.toLowerCase().replace(/\s+/g, '_') })
    setBusy(false)
    if (d.ok) onCreated(d.id); else toast(d.errore || 'Errore', 'err')
  }
  return (
    <div onClick={onClose} style={overlay}>
      <Card className="pop" onClick={(e) => e.stopPropagation()} style={{ width: 460, maxWidth: '95vw', padding: 28 }}>
        <h2 style={{ fontSize: 19, fontWeight: 800, marginBottom: 18 }}>Nuovo cliente</h2>
        {['nome', 'email', 'sito'].map((k) => (
          <div key={k} style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 11, textTransform: 'uppercase', color: 'var(--text-faint)', letterSpacing: '0.06em', fontWeight: 700 }}>{k}</label>
            <input className="field" style={{ marginTop: 5 }} value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} />
          </div>
        ))}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 18 }}>
          <button className="btn btn-ghost" onClick={onClose}>Annulla</button>
          <button className="btn btn-brand" onClick={crea} disabled={busy}>{busy ? <Spinner /> : 'Crea'}</button>
        </div>
      </Card>
    </div>
  )
}

const overlay = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)', backdropFilter: 'blur(6px)', zIndex: 1000, display: 'grid', placeItems: 'center', padding: 20 }

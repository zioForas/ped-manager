import React, { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import { useEsc } from './ui'

const MODI = [
  { id: 'assistente', t: 'Assistente', sub: 'solo guida' },
  { id: 'sicure', t: 'Azioni sicure', sub: 'genera/modifica' },
  { id: 'tutto', t: 'Esegui tutto', sub: 'con conferma' },
]
const SUGG = {
  assistente: ['Cosa fa questa app?', 'Quanti post ci sono?'],
  sicure: ['Rigenera il post 3', 'Genera il PDF'],
  tutto: ['Invia il piano al cliente', 'Rigenera tutti i post'],
}

export default function Chat({ cliente, open, onClose }) {
  const [mode, setMode] = useState('sicure')
  const [storia, setStoria] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [pending, setPending] = useState(null)
  const bodyRef = useRef(null)
  useEsc(onClose, open)

  useEffect(() => {
    if (open && storia.length === 0)
      setStoria([{ role: 'assistant', content: "Ciao! Sono l'assistente del PED Manager. Dimmi cosa vuoi fare — genero, rigenero e modifico contenuti, creo il PDF e altro. Scegli la modalità qui sopra." }])
  }, [open])
  useEffect(() => { if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight }, [storia, busy, pending])

  const call = async (extra = {}, nuovaStoria) => {
    setBusy(true); setPending(null)
    const base = nuovaStoria || storia
    try {
      const d = await api.chat(cliente, { messaggi: base.filter((m) => m.role !== 'sys'), modalita: mode, ...extra })
      if (d.errore) setStoria((s) => [...s, { role: 'sys', content: '⚠ ' + d.errore }])
      else {
        if (d.risposta) setStoria((s) => [...s, { role: 'assistant', content: d.risposta }])
        if (d.pending) setPending(d.pending)
      }
    } catch { setStoria((s) => [...s, { role: 'sys', content: '⚠ Errore di connessione' }]) }
    setBusy(false)
  }

  const invia = (testo) => {
    const t = (testo ?? input).trim(); if (!t || busy) return
    const ns = [...storia, { role: 'user', content: t }]
    setStoria(ns); setInput('')
    call({}, ns)
  }
  const conferma = () => { setStoria((s) => [...s, { role: 'sys', content: 'Confermato.' }]); call({ conferma: pending.azione }) }

  if (!open) return null
  return (
    <div className="glass-2 pop" style={{
      position: 'fixed', bottom: 22, right: 22, zIndex: 900, width: 410, maxWidth: '95vw', height: 620, maxHeight: '86vh',
      borderRadius: 20, display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: 'var(--shadow-lg)',
    }}>
      <div style={{ padding: 14, borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontWeight: 800, fontSize: 15 }}>💬 Assistente AI</div>
          <button onClick={onClose} style={iconBtn}>✕</button>
        </div>
        <div style={{ display: 'flex', gap: 4, marginTop: 12, background: 'var(--surface)', padding: 4, borderRadius: 11 }}>
          {MODI.map((m) => (
            <button key={m.id} onClick={() => setMode(m.id)} style={{
              flex: 1, border: 'none', borderRadius: 8, padding: '7px 4px', cursor: 'pointer', fontSize: 11, fontWeight: 700,
              background: mode === m.id ? 'var(--brand)' : 'transparent', color: mode === m.id ? '#fff' : 'var(--text-muted)',
            }}>{m.t}<br /><span style={{ fontWeight: 500, fontSize: 9, opacity: .85 }}>{m.sub}</span></button>
          ))}
        </div>
      </div>

      <div ref={bodyRef} style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 11 }}>
        {storia.map((m, i) => (
          <Msg key={i} m={m} />
        ))}
        {busy && <div style={{ ...bubble('assistant'), opacity: .6 }}>…</div>}
        {pending && (
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-brand" style={{ padding: '8px 14px', fontSize: 13 }} onClick={conferma}>✓ Conferma</button>
            <button className="btn btn-ghost" style={{ padding: '8px 14px', fontSize: 13 }} onClick={() => { setPending(null); setStoria((s) => [...s, { role: 'assistant', content: 'Ok, annullato.' }]) }}>✕ Annulla</button>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, padding: '0 12px 8px' }}>
        {(SUGG[mode] || []).map((s) => (
          <button key={s} onClick={() => invia(s)} style={{
            background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-muted)',
            fontSize: 11, padding: '6px 10px', borderRadius: 99, cursor: 'pointer',
          }}>{s}</button>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8, padding: 12, borderTop: '1px solid var(--border)' }}>
        <textarea className="field" value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); invia() } }}
          placeholder="Scrivi un comando…" style={{ resize: 'none', height: 44, padding: '11px 13px' }} />
        <button className="btn btn-brand" onClick={() => invia()} style={{ padding: '0 16px' }}>➤</button>
      </div>
    </div>
  )
}

function Msg({ m }) {
  if (m.role === 'sys') return <div style={{ alignSelf: 'center', color: 'var(--text-faint)', fontSize: 12, fontStyle: 'italic' }}>{m.content}</div>
  return <div style={bubble(m.role)}>{m.content}</div>
}
const bubble = (role) => ({
  maxWidth: '85%', padding: '10px 13px', borderRadius: 14, fontSize: 13.5, lineHeight: 1.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
  alignSelf: role === 'user' ? 'flex-end' : 'flex-start',
  background: role === 'user' ? 'var(--brand)' : 'var(--surface)',
  color: role === 'user' ? '#fff' : 'var(--text)',
  border: role === 'user' ? 'none' : '1px solid var(--border)',
})
const iconBtn = { background: 'none', border: 'none', color: 'var(--text-faint)', fontSize: 18, cursor: 'pointer' }

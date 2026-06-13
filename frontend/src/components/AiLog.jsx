import React, { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'

const COLOR = { ok: 'var(--brand)', warn: '#fbbf24', err: '#f87171', info: 'var(--text-muted)' }

/* Console live dei processi AI: modello usato, fallback, errori. */
export default function AiLog() {
  const [log, setLog] = useState([])
  const [last, setLast] = useState(null)
  const [open, setOpen] = useState(true)
  const boxRef = useRef(null)

  useEffect(() => {
    let alive = true
    const tick = async () => {
      try { const d = await api.aiLog(); if (alive) { setLog(d.log || []); setLast(d.last_model) } } catch {}
    }
    tick()
    const iv = setInterval(tick, 2500)
    return () => { alive = false; clearInterval(iv) }
  }, [])
  useEffect(() => { if (boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight }, [log])

  return (
    <div>
      <div onClick={() => setOpen(!open)} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 13.5, fontWeight: 600 }}>
          <span className="dot-live" style={{ width: 8, height: 8, borderRadius: 99, background: 'var(--brand)' }} />
          Attività AI
        </span>
        <span style={{ color: 'var(--text-faint)', fontSize: 12, transform: open ? 'rotate(180deg)' : 'none', transition: '.2s' }}>▾</span>
      </div>
      {last && <div style={{ fontSize: 10.5, color: 'var(--text-faint)', marginTop: 4 }}>modello attivo: <b style={{ color: 'var(--brand-strong)' }}>{last}</b></div>}
      {open && (
        <div ref={boxRef} style={{
          marginTop: 9, maxHeight: 150, overflowY: 'auto', fontFamily: 'ui-monospace,monospace', fontSize: 11,
          lineHeight: 1.65, background: 'var(--surface)', borderRadius: 10, padding: '9px 11px', border: '1px solid var(--border)',
        }}>
          {log.length === 0 ? <div style={{ color: 'var(--text-faint)' }}>Nessuna attività ancora.</div>
            : log.slice(-30).map((l, i) => (
              <div key={i} style={{ color: COLOR[l.k] || 'var(--text-muted)' }}>
                <span style={{ opacity: .5 }}>{l.t}</span> {l.m}
              </div>
            ))}
        </div>
      )}
    </div>
  )
}

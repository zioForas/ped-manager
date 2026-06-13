import React, { useEffect, useState } from 'react'
import { useEsc } from './ui'

const STEP = [
  { sel: null, t: 'Benvenuto nel PED Manager 👋', d: 'Questo è il pannello per gestire il piano editoriale social di un cliente. Ti mostro le funzioni in pochi passi — puoi uscire quando vuoi (✕ o ESC).' },
  { sel: '#tour-platform', t: 'Facebook / Instagram', d: 'Scegli su quale piattaforma lavorare. Ora testiamo Facebook (i Post); su Instagram compaiono anche le Storie.' },
  { sel: '#tour-tabs', t: 'Post e Storie', d: 'Qui vedi e modifichi i contenuti generati dall\'AI: testo, hashtag, orario. Ogni scheda si apre con un clic.' },
  { sel: '#tour-genera', t: 'Generazione e PDF', d: 'Rigeneri tutti i contenuti con l\'AI e crei il PDF del piano da inviare al cliente.' },
  { sel: '#tour-model', t: 'Modello AI', d: 'Scegli il modello AI. Più modelli gratuiti con indicatore di disponibilità: se uno esaurisce il limite, passa da solo al successivo.' },
  { sel: '#tour-invia', t: 'Invio al cliente', d: 'Invia l\'email con il PDF e i pulsanti Approva / Richiedi modifiche. La risposta torna nel pannello.' },
  { sel: '#tour-chat', t: 'Assistente AI 💬', d: 'Parli all\'app in italiano e lei esegue i comandi. Tre modalità: solo guida, azioni sicure, esegui tutto con conferma.' },
]

export default function Tutorial({ open, onClose }) {
  const [i, setI] = useState(0)
  const [box, setBox] = useState(null)
  useEsc(onClose, open)

  useEffect(() => { if (open) setI(0) }, [open])
  useEffect(() => {
    if (!open) return
    const step = STEP[i]
    const el = step.sel ? document.querySelector(step.sel) : null
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      const t = setTimeout(() => {
        const r = el.getBoundingClientRect()
        setBox({ top: r.top - 6, left: r.left - 6, width: r.width + 12, height: r.height + 12 })
      }, 220)
      return () => clearTimeout(t)
    } else setBox(null)
  }, [i, open])

  if (!open) return null
  const step = STEP[i]
  const next = () => (i >= STEP.length - 1 ? onClose() : setI(i + 1))
  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 9500, pointerEvents: 'none' }}>
      {/* velo pieno solo quando NON c'è un elemento da evidenziare (intro) */}
      {!box && <div onClick={onClose} style={{ position: 'absolute', inset: 0, background: 'rgba(3,8,6,.74)', pointerEvents: 'auto' }} />}
      {/* spotlight: il box-shadow oscura tutt'intorno, lasciando VISIBILE l'elemento nel "buco" */}
      {box && <div style={{
        position: 'absolute', ...box, border: '2px solid var(--brand)', borderRadius: 12,
        boxShadow: '0 0 0 4px var(--brand-soft), 0 0 0 9999px rgba(3,8,6,.72)', transition: 'all .3s', pointerEvents: 'none',
      }} />}
      <div className="glass-2 pop" style={{
        position: 'fixed', left: '50%', bottom: 40, transform: 'translateX(-50%)', width: 460, maxWidth: '92vw',
        borderRadius: 18, padding: '22px 24px', zIndex: 9600, pointerEvents: 'auto',
      }}>
        <button onClick={onClose} style={{ position: 'absolute', top: 12, right: 14, background: 'none', border: 'none', color: 'var(--text-faint)', fontSize: 19, cursor: 'pointer' }}>✕</button>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--brand-strong)' }}>Passo {i + 1} di {STEP.length}</div>
        <div style={{ fontSize: 19, fontWeight: 800, margin: '6px 0 8px' }}>{step.t}</div>
        <div style={{ fontSize: 14, color: 'var(--text-muted)', lineHeight: 1.55 }}>{step.d}</div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 18 }}>
          <div style={{ display: 'flex', gap: 5 }}>
            {STEP.map((_, k) => <span key={k} style={{ width: 7, height: 7, borderRadius: 99, background: k === i ? 'var(--brand)' : 'var(--border-strong)' }} />)}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {i > 0 && <button className="btn btn-ghost" style={{ padding: '9px 16px', fontSize: 13 }} onClick={() => setI(i - 1)}>Indietro</button>}
            <button className="btn btn-brand" style={{ padding: '9px 18px', fontSize: 13 }} onClick={next}>{i >= STEP.length - 1 ? 'Fine ✓' : 'Avanti →'}</button>
          </div>
        </div>
      </div>
    </div>
  )
}

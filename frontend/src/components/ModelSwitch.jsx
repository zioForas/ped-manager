import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { Spinner, useToast } from './ui'

const ICON = { ok: '✅', limited: '⏳', error: '❌', unknown: '•' }

export default function ModelSwitch() {
  const [data, setData] = useState(null)
  const [checking, setChecking] = useState(false)
  const toast = useToast()

  const carica = () => api.aiModels().then(setData).catch(() => {})
  useEffect(() => { carica() }, [])

  const cambia = async (id) => {
    const d = await api.setAiModel(id)
    if (d.ok) { toast('Modello AI: ' + id); carica() }
    else toast(d.errore || 'Errore', 'err')
  }
  const verifica = async () => {
    setChecking(true)
    try { const d = await api.aiModelsCheck(); setData((x) => ({ ...x, status: d.status }));
      toast(`${Object.values(d.status || {}).filter((s) => s.state === 'ok').length} modelli disponibili`, 'info') }
    catch { toast('Verifica fallita', 'err') }
    setChecking(false)
  }

  if (!data) return <div style={{ padding: 8 }}><Spinner /></div>
  const status = data.status || {}
  const free = data.models.filter((m) => m.tier === 'free')
  const prem = data.models.filter((m) => m.tier === 'premium')
  const fmt = (m) => {
    const s = status[m.id] || { state: 'unknown' }
    let tag = ''
    if (s.state === 'limited') tag = ` · limite ~${Math.max(1, Math.round((s.retry_in || 60) / 60))}m`
    else if (s.state === 'ok') tag = ' · ok'
    else if (s.state === 'error') tag = ' · ko'
    return `${ICON[s.state] || '•'} ${m.label}${tag}`
  }

  return (
    <div>
      <select className="field" value={data.selected} onChange={(e) => cambia(e.target.value)} style={{ fontSize: 12.5, padding: '9px 11px', cursor: 'pointer' }}>
        <optgroup label="Gratuiti">
          {free.map((m) => <option key={m.id} value={m.id}>{fmt(m)}</option>)}
        </optgroup>
        <optgroup label="Premium (presto)">
          {prem.map((m) => <option key={m.id} value={m.id} disabled>🔒 {m.label}</option>)}
        </optgroup>
      </select>
      <button className="btn btn-ghost" onClick={verifica} disabled={checking}
        style={{ width: '100%', marginTop: 7, fontSize: 11.5, padding: 7, justifyContent: 'center' }}>
        {checking ? <Spinner size={13} /> : '⟳ Verifica disponibilità'}
      </button>
      <div style={{ fontSize: 10.5, color: 'var(--text-faint)', marginTop: 7, lineHeight: 1.5 }}>
        Se un modello esaurisce il limite, passa automaticamente al successivo gratuito.
      </div>
    </div>
  )
}

import React, { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { Card, ThemeToggle, Spinner, useToast, useEsc } from '../components/ui'
import ModelSwitch from '../components/ModelSwitch'
import Chat from '../components/Chat'
import Tutorial from '../components/Tutorial'
import AiLog from '../components/AiLog'

const ARG_COLORS = {
  'Presentazione Studio': '#60a5fa', 'Igiene E Prevenzione': 'var(--brand)',
  'Team E Staff': '#fb923c', 'Implantologia': '#c084fc',
}

export default function Cliente({ onLogout }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [data, setData] = useState(null)
  const [platform, setPlatform] = useState('fb')
  const [tab, setTab] = useState('post')
  const [chat, setChat] = useState(false)
  const [tour, setTour] = useState(false)
  const [testOpen, setTestOpen] = useState(false)
  const [gen, setGen] = useState(null) // progress generazione
  const [pubblicati, setPubblicati] = useState([])

  const carica = () => api.cliente(id).then(setData).catch(() => setData(false))
  const caricaPubblicati = () => api.pubblicati(id).then((d) => setPubblicati(d.pubblicati || [])).catch(() => {})
  useEffect(() => { carica(); caricaPubblicati() }, [id])

  if (data === false) return <Center>Cliente non trovato. <button className="btn btn-ghost" onClick={() => navigate('/')}>Torna ai clienti</button></Center>
  if (!data) return <Center><Spinner size={24} /></Center>

  const { strategia, ped = [], stories = [], sessione, periodo, meta } = data
  const showStories = platform === 'ig'

  const generaTutto = async () => {
    if (!confirm('Rigenera TUTTI i contenuti con l\'AI? Richiede 2-4 minuti.')) return
    const r = await api.genera(id)
    if (r && r.ok === false) return toast(r.errore || 'Errore', 'err')
    setGen({ fatti: 0, totale: 0, fase: 'post' })
    const iv = setInterval(async () => {
      let st; try { st = await api.generaStato(id) } catch { return }
      setGen(st)
      if (!st.in_corso) {
        clearInterval(iv)
        if (st.errore) { toast(/limit|429|tpd|tokens per day/i.test(st.errore) ? 'Limite AI raggiunto' : 'Errore generazione', 'err'); setGen(null) }
        else { toast('Contenuti rigenerati!'); setGen(null); carica() }
      }
    }, 2000)
  }
  const generaPdf = async () => { toast('Genero il PDF…'); const d = await api.pdf(id); if (d.ok) toast('PDF pronto!'); else toast('Errore PDF', 'err') }
  const invia = async () => { if (!confirm('Inviare il piano al cliente via email?')) return; setTestOpen(true) }

  return (
    <div style={{ minHeight: '100vh' }}>
      {/* TOPBAR */}
      <div style={{ position: 'sticky', top: 0, zIndex: 30, padding: '14px 18px 0' }}>
        <div className="glass-2" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '11px 16px', borderRadius: 16 }}>
          <button className="btn btn-ghost" style={{ padding: '7px 12px', fontSize: 13 }} onClick={() => navigate('/')}>← Clienti</button>
          <span style={{ fontWeight: 800, color: 'var(--brand)' }}>PED</span>
          <span style={{ fontWeight: 700 }}>{strategia.cliente}</span>
          <span className="hide-sm" style={{ color: 'var(--text-faint)', fontSize: 13 }}>· {periodo}</span>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
            <ThemeToggle />
            <button className="btn btn-ghost" onClick={onLogout}>Esci</button>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '252px 1fr', gap: 18, padding: 18, maxWidth: 1280, margin: '0 auto' }} className="layout">
        {/* SIDEBAR */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Card id="tour-genera" style={{ padding: 14 }}>
            <SbLabel>Contenuti</SbLabel>
            <SbBtn onClick={generaTutto}>⚡ Rigenera con AI</SbBtn>
            <SbBtn onClick={generaPdf}>📄 Aggiorna PDF</SbBtn>
            <a className="sb-link" href={`/pdf/${id}`} target="_blank" rel="noreferrer"><SbBtn as="span">👁 Anteprima PDF</SbBtn></a>
          </Card>

          <Card id="tour-invia" style={{ padding: 14 }}>
            <SbLabel>Workflow</SbLabel>
            <SbBtn onClick={invia} accent>✉ Invia / Test al cliente</SbBtn>
          </Card>

          <Card id="tour-model" style={{ padding: 14 }}>
            <SbLabel>Modello AI</SbLabel>
            <ModelSwitch />
          </Card>

          <Card style={{ padding: 14 }}>
            <AiLog />
          </Card>

          <Card style={{ padding: 14 }}>
            <SbLabel>Aiuto</SbLabel>
            <SbBtn onClick={() => setTour(true)}>🎓 Tutorial guidato</SbBtn>
            <SbBtn onClick={() => setChat(true)}>💬 Assistente AI</SbBtn>
          </Card>

          <Card style={{ padding: 14 }}>
            <SbLabel>Statistiche</SbLabel>
            <Stat k="Post" v={ped.length} />
            <Stat k="Storie" v={stories.length} />
            <Stat k="Stato" v={sessione?.stato || 'non inviato'} />
          </Card>
        </div>

        {/* MAIN */}
        <div>
          {gen && (
            <Card style={{ padding: 16, marginBottom: 16 }}>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>
                Generazione {gen.fase === 'stories' ? 'storie' : 'post'}… {gen.fatti}/{gen.totale || '?'}
              </div>
              <Bar pct={gen.totale ? (gen.fatti / gen.totale) * 100 : 8} />
            </Card>
          )}

          {/* SWITCH PIATTAFORMA */}
          <div id="tour-platform" className="glass" style={{ display: 'inline-flex', gap: 4, padding: 4, borderRadius: 14, marginBottom: 18 }}>
            {[['fb', '📘 Facebook'], ['ig', '📷 Instagram']].map(([k, t]) => (
              <button key={k} onClick={() => { setPlatform(k); if (k === 'fb') setTab('post') }} style={{
                border: 'none', borderRadius: 10, padding: '9px 18px', fontWeight: 700, fontSize: 13.5, cursor: 'pointer',
                background: platform === k ? (k === 'fb' ? 'linear-gradient(135deg,#1877f2,#0a5fd0)' : 'linear-gradient(135deg,#e1306c,#c13584,#f56040)') : 'transparent',
                color: platform === k ? '#fff' : 'var(--text-muted)',
              }}>{t}</button>
            ))}
          </div>

          {/* TABS */}
          <div id="tour-tabs" style={{ display: 'flex', gap: 6, borderBottom: '1px solid var(--border)', marginBottom: 18 }}>
            <Tab on={tab === 'post'} onClick={() => setTab('post')}>Post ({ped.length})</Tab>
            {showStories && <Tab on={tab === 'stories'} onClick={() => setTab('stories')}>Storie ({stories.length})</Tab>}
            <Tab on={tab === 'pubblicati'} onClick={() => { setTab('pubblicati'); caricaPubblicati() }}>
              ✅ Pubblicati ({pubblicati.length})
            </Tab>
          </div>

          {tab === 'post' && ped.map((p) => <PostCard key={p.numero} cliente={id} post={p} onSaved={carica} />)}
          {tab === 'stories' && stories.map((s) => <StoryCard key={s.numero} story={s} />)}
          {tab === 'pubblicati' && <Pubblicati items={pubblicati} onRefresh={caricaPubblicati} />}
        </div>
      </div>

      {/* FLOATING CHAT BTN */}
      {!chat && (
        <button id="tour-chat" className="btn btn-brand pop" onClick={() => setChat(true)}
          style={{ position: 'fixed', bottom: 22, right: 22, zIndex: 800, borderRadius: 99, padding: '13px 20px', fontWeight: 700 }}>
          💬 Assistente AI
        </button>
      )}
      <Chat cliente={id} open={chat} onClose={() => setChat(false)} />
      <Tutorial open={tour} onClose={() => setTour(false)} />
      {testOpen && <TestModal cliente={id} email={strategia.email_cliente} onClose={() => setTestOpen(false)}
        onDone={() => { caricaPubblicati(); setTab('pubblicati') }} />}
    </div>
  )
}

/* ───────── POST CARD ───────── */
function PostCard({ cliente, post, onSaved }) {
  const [open, setOpen] = useState(false)
  const [p, setP] = useState(post)
  const [busy, setBusy] = useState(false)
  const toast = useToast()
  useEffect(() => setP(post), [post])

  const salva = async () => { setBusy(true); await api.salvaPost(cliente, p.numero, { caption: p.caption, hashtag: p.hashtag, orario: p.orario, nota_grafica: p.nota_grafica }); setBusy(false); toast('Salvato'); onSaved && onSaved() }
  const rigen = async () => {
    setBusy(true)
    const d = await api.rigeneraPost(cliente, p.numero); setBusy(false)
    if (d.ok && d.post) { setP(d.post); toast('Rigenerato con AI') } else toast(d.errore || 'Errore', 'err')
  }
  const argc = ARG_COLORS[p.argomento] || 'var(--brand)'

  return (
    <Card hover style={{ marginBottom: 10, overflow: 'hidden' }}>
      <div onClick={() => setOpen(!open)} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 16px', cursor: 'pointer' }}>
        <span style={{ fontWeight: 800, color: 'var(--brand)', fontSize: 12, minWidth: 34 }}>#{p.numero}</span>
        <span style={{ fontSize: 10.5, fontWeight: 700, padding: '3px 11px', borderRadius: 99, background: `color-mix(in srgb, ${argc} 16%, transparent)`, color: argc }}>{p.argomento}</span>
        <span style={{ flex: 1, fontSize: 12.5, color: 'var(--text-muted)', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{p.caption?.slice(0, 70)}…</span>
        <span className="hide-sm" style={{ fontSize: 11, color: 'var(--text-faint)' }}>{p.data} {p.orario}</span>
        <span style={{ color: 'var(--text-faint)', transform: open ? 'rotate(180deg)' : 'none', transition: '.2s' }}>▾</span>
      </div>
      {open && (
        <div style={{ padding: '0 16px 16px', borderTop: '1px solid var(--border)' }}>
          {p.design_url && <img src={p.design_url} alt="" style={{ maxWidth: 200, borderRadius: 10, marginTop: 12, border: '1px solid var(--border)' }} />}
          <FieldL>Caption</FieldL>
          <textarea className="field" value={p.caption || ''} onChange={(e) => setP({ ...p, caption: e.target.value })} style={{ minHeight: 120, resize: 'vertical' }} />
          <FieldL>Hashtag</FieldL>
          <textarea className="field" value={p.hashtag || ''} onChange={(e) => setP({ ...p, hashtag: e.target.value })} style={{ minHeight: 50, resize: 'vertical' }} />
          <div style={{ display: 'flex', gap: 10, marginTop: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <input className="field" value={p.orario || ''} onChange={(e) => setP({ ...p, orario: e.target.value })} style={{ width: 100 }} />
            <button className="btn btn-brand" onClick={salva} disabled={busy}>{busy ? <Spinner /> : 'Salva'}</button>
            <button className="btn btn-ghost" onClick={rigen} disabled={busy}>↺ Rigenera AI</button>
          </div>
        </div>
      )}
    </Card>
  )
}

/* ───────── STORY CARD ───────── */
function StoryCard({ story }) {
  const [open, setOpen] = useState(false)
  return (
    <Card hover style={{ marginBottom: 10, overflow: 'hidden' }}>
      <div onClick={() => setOpen(!open)} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 16px', cursor: 'pointer' }}>
        <span style={{ fontWeight: 800, color: 'var(--brand)', fontSize: 12, minWidth: 34 }}>#{story.numero}</span>
        <span style={{ fontSize: 10.5, fontWeight: 700, padding: '3px 11px', borderRadius: 99, background: 'var(--brand-soft)', color: 'var(--brand-strong)' }}>{story.tipo}</span>
        <span style={{ flex: 1, fontSize: 12.5, color: 'var(--text-muted)', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{story.testo?.slice(0, 70)}…</span>
        <span style={{ color: 'var(--text-faint)', transform: open ? 'rotate(180deg)' : 'none', transition: '.2s' }}>▾</span>
      </div>
      {open && (
        <div style={{ padding: '12px 16px 16px', borderTop: '1px solid var(--border)' }}>
          <div style={{ fontSize: 13.5, whiteSpace: 'pre-wrap', color: 'var(--text)' }}>{story.testo}</div>
          {story.musica_suggerita && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>🎵 {story.musica_suggerita}</div>}
        </div>
      )}
    </Card>
  )
}

/* ───────── POST PUBBLICATI ───────── */
function Pubblicati({ items, onRefresh }) {
  if (!items.length) return (
    <Card style={{ padding: 30, textAlign: 'center', color: 'var(--text-muted)' }}>
      <div style={{ fontSize: 30, marginBottom: 8 }}>📭</div>
      Nessun post pubblicato dai test, ancora.<br />
      <span style={{ fontSize: 13, color: 'var(--text-faint)' }}>Lancia un <b>Invio / Test al cliente</b>, approva dalla mail e il post pubblicato comparirà qui.</span>
    </Card>
  )
  const fmt = (iso) => { try { return new Date(iso).toLocaleString('it-IT', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) } catch { return iso } }
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10 }}>
        <button className="btn btn-ghost" style={{ padding: '7px 13px', fontSize: 12.5 }} onClick={onRefresh}>⟳ Aggiorna</button>
      </div>
      {items.map((x, i) => (
        <Card key={i} hover style={{ marginBottom: 10, padding: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 99, background: 'color-mix(in srgb,#1877f2 16%,transparent)', color: '#5b9bf3' }}>
              {x.piattaforma === 'facebook' ? '📘 Facebook' : x.piattaforma}
            </span>
            <span className="chip" style={{ textTransform: 'none', background: 'var(--surface)', color: 'var(--text-muted)', borderColor: 'var(--border)' }}>
              {x.origine === 'test' ? 'da test' : x.origine}
            </span>
            <span style={{ fontSize: 12, color: 'var(--text-faint)', marginLeft: 'auto' }}>{fmt(x.data)}</span>
          </div>
          <div style={{ display: 'flex', gap: 14 }}>
            {x.media_url && <img src={x.media_url} alt="" style={{ width: 96, height: 120, objectFit: 'cover', borderRadius: 10, border: '1px solid var(--border)', flex: 'none' }} />}
            <div style={{ fontSize: 13.5, color: 'var(--text)', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
              {x.testo}{x.testo && x.testo.length >= 240 ? '…' : ''}
            </div>
          </div>
          {x.url && (
            <a href={x.url} target="_blank" rel="noreferrer" className="btn btn-brand"
              style={{ marginTop: 12, padding: '8px 15px', fontSize: 13, textDecoration: 'none', display: 'inline-flex' }}>
              Vedi su Facebook ↗
            </a>
          )}
        </Card>
      ))}
    </div>
  )
}

/* ───────── TEST / INVIO MODAL ───────── */
function TestModal({ cliente, email, onClose, onDone }) {
  const [dest, setDest] = useState(email || '')
  const [log, setLog] = useState(null)
  const [running, setRunning] = useState(false)
  const toast = useToast()
  useEsc(onClose)
  const ivRef = useRef(null)
  useEffect(() => () => clearInterval(ivRef.current), [])

  const avvia = async () => {
    if (!dest.includes('@')) return toast('Email non valida', 'err')
    setRunning(true); setLog([])
    await api.testFlow(cliente, dest)
    ivRef.current = setInterval(async () => {
      const d = await api.testFlowLog()
      setLog(d.log)
      if (!d.running) { clearInterval(ivRef.current); setRunning(false); onDone && onDone() }
    }, 1500)
  }
  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)', backdropFilter: 'blur(6px)', zIndex: 1000, display: 'grid', placeItems: 'center', padding: 20 }}>
      <Card className="pop" onClick={(e) => e.stopPropagation()} style={{ width: 560, maxWidth: '95vw', padding: 28 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <h2 style={{ fontSize: 19, fontWeight: 800 }}>🚀 Invio / Test al cliente</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-faint)', fontSize: 19, cursor: 'pointer' }}>✕</button>
        </div>
        {log === null ? (
          <>
            <label style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>Invia il piano (con link Approva/Modifiche) a:</label>
            <input className="field" type="email" value={dest} onChange={(e) => setDest(e.target.value)} style={{ margin: '8px 0 14px' }} />
            <button className="btn btn-brand" onClick={avvia} style={{ width: '100%', justifyContent: 'center', padding: 13 }}>📧 Invia email</button>
          </>
        ) : (
          <>
            <div style={{ fontSize: 13, color: 'var(--brand)', marginBottom: 10 }}>{running ? '🔄 In corso…' : '✅ Completato'}</div>
            <div className="glass" style={{ borderRadius: 12, padding: 14, fontFamily: 'ui-monospace,monospace', fontSize: 12.5, maxHeight: 280, overflowY: 'auto', lineHeight: 1.7 }}>
              {log.map((l, i) => <div key={i} style={{ color: l.startsWith('✓') || l.startsWith('✅') ? 'var(--brand)' : l.startsWith('✗') ? '#f87171' : 'var(--text-muted)' }}>{l}</div>)}
            </div>
          </>
        )}
      </Card>
    </div>
  )
}

/* ───────── piccoli helper UI ───────── */
const Center = ({ children }) => <div style={{ height: '100vh', display: 'grid', placeItems: 'center', gap: 12 }}>{children}</div>
const SbLabel = ({ children }) => <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: 8, padding: '0 2px' }}>{children}</div>
function SbBtn({ children, onClick, accent, as }) {
  const Comp = as || 'button'
  return <Comp onClick={onClick} style={{
    display: 'flex', alignItems: 'center', gap: 8, width: '100%', padding: '10px 12px', borderRadius: 11, border: 'none',
    background: 'transparent', color: accent ? 'var(--brand-strong)' : 'var(--text)', fontSize: 13.5, fontWeight: 600,
    textAlign: 'left', cursor: 'pointer', transition: 'background .15s', fontFamily: 'inherit',
  }} onMouseEnter={(e) => e.currentTarget.style.background = 'var(--surface-hover)'} onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>{children}</Comp>
}
const Stat = ({ k, v }) => <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '3px 2px', color: 'var(--text-muted)' }}><span>{k}</span><b style={{ color: 'var(--text)' }}>{v}</b></div>
const Tab = ({ on, onClick, children }) => <button onClick={onClick} style={{ background: 'none', border: 'none', borderBottom: `2px solid ${on ? 'var(--brand)' : 'transparent'}`, color: on ? 'var(--text)' : 'var(--text-muted)', fontWeight: 700, fontSize: 14, padding: '9px 14px', cursor: 'pointer' }}>{children}</button>
const FieldL = ({ children }) => <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-faint)', margin: '12px 0 4px', fontWeight: 700 }}>{children}</div>
const Bar = ({ pct }) => <div style={{ height: 8, background: 'var(--surface)', borderRadius: 6, overflow: 'hidden' }}><div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg,var(--brand),var(--brand-bright))', borderRadius: 6, transition: 'width .4s' }} /></div>

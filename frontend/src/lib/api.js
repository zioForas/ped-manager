/* Client API verso il backend Flask (stesse rotte JSON già esistenti). */

async function req(url, opts = {}) {
  const r = await fetch(url, {
    credentials: 'same-origin',
    headers: opts.body ? { 'Content-Type': 'application/json' } : undefined,
    ...opts,
  })
  let data = null
  try { data = await r.json() } catch { /* no json */ }
  if (r.status === 401) {
    const err = new Error('Non autenticato')
    err.unauthorized = true
    throw err
  }
  if (!r.ok && !data) throw new Error(`HTTP ${r.status}`)
  return data
}

const J = (body) => ({ method: 'POST', body: JSON.stringify(body || {}) })

export const api = {
  // auth
  me: () => req('/api/me'),
  login: (username, password, ricordami) => req('/api/login', J({ username, password, ricordami })),
  logout: () => req('/api/logout', { method: 'POST' }),

  // clienti
  clienti: () => req('/api/clienti'),
  cliente: (id) => req(`/api/cliente/${id}`),
  nuovoCliente: (d) => req('/api/nuovo_cliente', J(d)),

  // contenuti
  salvaPost: (id, n, d) => req(`/api/post/${id}/${n}`, { method: 'PUT', body: JSON.stringify(d) }),
  salvaStory: (id, n, d) => req(`/api/story/${id}/${n}`, { method: 'PUT', body: JSON.stringify(d) }),
  rigeneraPost: (id, n) => req(`/api/rigenera/${id}/${n}`, { method: 'POST' }),
  rigeneraTutti: (id, note) => req(`/api/rigenera_tutti/${id}`, J({ note })),
  rigeneraTuttiStato: (id) => req(`/api/rigenera_tutti/${id}/stato`),
  ignoraNote: (id) => req(`/api/ignora_note/${id}`, { method: 'POST' }),
  genera: (id) => req(`/api/genera/${id}`, { method: 'POST' }),
  generaStato: (id) => req(`/api/genera/${id}/stato`),
  pdf: (id) => req(`/api/pdf/${id}`, { method: 'POST' }),

  // strategia
  strategia: (id) => req(`/api/strategia/${id}`),
  salvaStrategia: (id, d) => req(`/api/strategia/${id}`, { method: 'PUT', body: JSON.stringify(d) }),

  // media
  mediaScarica: (id) => req(`/api/media/scarica/${id}`, { method: 'POST' }),
  mediaStato: (id) => req(`/api/media/stato/${id}`),

  // meta
  metaVerifica: () => req('/api/meta/verifica'),
  metaDryRun: (id) => req(`/api/meta/dry_run/${id}`, { method: 'POST' }),
  metaSchedula: (id) => req(`/api/meta/schedula/${id}`, { method: 'POST' }),

  // test flow
  testFlow: (id, email) => req(`/api/test_flow/${id}`, J({ email })),
  testFlowLog: () => req('/api/test_flow/log'),
  pubblicati: (id) => req(`/api/pubblicati/${id}`),

  // AI
  aiModels: () => req('/api/ai_models'),
  aiModelsCheck: () => req('/api/ai_models/check', { method: 'POST' }),
  setAiModel: (model) => req('/api/ai_model', J({ model })),
  aiLog: () => req('/api/ai_log'),

  // chat
  chat: (id, payload) => req(`/api/chat/${id}`, J(payload)),

  // story media upload (multipart)
  uploadStoryMedia: async (id, n, file) => {
    const fd = new FormData()
    fd.append('file', file)
    const r = await fetch(`/api/story/${id}/${n}/media`, { method: 'POST', body: fd, credentials: 'same-origin' })
    return r.json()
  },
}

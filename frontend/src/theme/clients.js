/*
  WHITE-LABEL — configurazione per cliente.
  Per creare la piattaforma per un nuovo cliente basta aggiungere una voce qui
  con il suo colore brand (e opzionalmente nome/logo): tutto il design (accenti,
  bagliori, stati, bottoni) si ri-tematizza automaticamente da --brand.
*/

export const CLIENTS = {
  _default: { brand: '#0fa46a', nome: 'PED Manager', iniziali: 'PED' },
  example: { brand: '#0fa46a', nome: 'Cliente Demo', iniziali: 'CD' },
}

export function clientConfig(id) {
  return CLIENTS[id] || { ...CLIENTS._default }
}

/* applica il colore brand del cliente (white-label) */
export function applyBrand(brand) {
  if (brand) document.documentElement.style.setProperty('--brand', brand)
}

/* tema chiaro/scuro: 'auto' (sistema) | 'light' | 'dark' */
const THEME_KEY = 'ped-theme'

export function getTheme() {
  return localStorage.getItem(THEME_KEY) || 'auto'
}

export function applyTheme(mode) {
  const root = document.documentElement
  if (mode === 'auto') root.removeAttribute('data-theme')
  else root.setAttribute('data-theme', mode)
  localStorage.setItem(THEME_KEY, mode)
}

export function initTheme() {
  applyTheme(getTheme())
}

import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { initTheme } from './theme/clients'
import App from './App'
import './index.css'

initTheme()

createRoot(document.getElementById('root')).render(
  <BrowserRouter basename="/app">
    <App />
  </BrowserRouter>,
)

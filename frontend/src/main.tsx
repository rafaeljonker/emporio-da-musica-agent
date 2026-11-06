import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Dark mode follows the OS (responsive.md); the tokens use shadcn's class-based .dark.
const dark = window.matchMedia('(prefers-color-scheme: dark)')
const applyScheme = () => document.documentElement.classList.toggle('dark', dark.matches)
applyScheme()
dark.addEventListener('change', applyScheme)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

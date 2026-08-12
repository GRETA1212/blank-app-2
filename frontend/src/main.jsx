import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import PhaseTwo from './PhaseTwo.jsx'
import './styles.css'
import './fit360-extra.css'
import './phase2.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
    <PhaseTwo />
  </React.StrictMode>,
)

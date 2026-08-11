import { useEffect, useMemo, useState } from 'react'
import {
  Camera,
  CheckCircle2,
  ChevronRight,
  CircleUserRound,
  RefreshCw,
  ScanLine,
  Shirt,
  ShoppingBag,
  Sparkles,
} from 'lucide-react'

const defaultScore = {
  score: 91,
  label: 'strong match',
  notes: [
    'The blazer gives the outfit a strong tailored anchor.',
    'Light jeans keep the outfit sharp and modern.',
    'Low-profile footwear keeps the proportions clean.',
  ],
  recommended_additions: ['burgundy bag', 'gold earrings', 'black belt'],
}

function UploadCard({ title, subtitle, icon: Icon, file, onChange, accept = 'image/*' }) {
  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file])

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview)
    }
  }, [preview])

  return (
    <label className="upload-card">
      {preview ? (
        <img className="upload-preview" src={preview} alt={title} />
      ) : (
        <div className="upload-empty">
          <span className="icon-shell"><Icon size={24} /></span>
          <strong>{title}</strong>
          <span>{subtitle}</span>
        </div>
      )}
      <input
        hidden
        type="file"
        accept={accept}
        capture="environment"
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
      />
      <span className="upload-action"><Camera size={15} /> {file ? 'Change photo' : 'Add photo'}</span>
    </label>
  )
}

function ScoreRing({ score }) {
  const deg = Math.round((score / 100) * 360)
  return (
    <div className="score-ring" style={{ '--score-deg': `${deg}deg` }}>
      <div className="score-inner">
        <strong>{score}</strong>
        <span>/100</span>
      </div>
    </div>
  )
}

export default function App() {
  const [personFile, setPersonFile] = useState(null)
  const [garmentFile, setGarmentFile] = useState(null)
  const [occasion, setOccasion] = useState('casual')
  const [score, setScore] = useState(defaultScore)
  const [loading, setLoading] = useState(false)
  const [tryOnState, setTryOnState] = useState('idle')
  const [trends, setTrends] = useState([
    { name: 'slim retro sneakers', score: 94 },
    { name: 'burgundy bag', score: 91 },
    { name: 'fitted black top', score: 89 },
  ])

  useEffect(() => {
    fetch('/api/trends')
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (data?.items?.length) setTrends(data.items.slice(0, 3))
      })
      .catch(() => {})
  }, [])

  async function analyzeStyle() {
    setLoading(true)
    try {
      const response = await fetch('/api/style/score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          blazer_color: 'black and white',
          bottom_color: 'white',
          top_color: 'black',
          shoe_style: 'slim retro sneakers',
          occasion,
        }),
      })
      if (response.ok) setScore(await response.json())
    } catch {
      setScore(defaultScore)
    } finally {
      setLoading(false)
    }
  }

  function createTryOn() {
    if (!personFile || !garmentFile) {
      setTryOnState('missing')
      return
    }
    setTryOnState('working')
    window.setTimeout(() => setTryOnState('mock-ready'), 900)
  }

  const personPreview = useMemo(
    () => (personFile ? URL.createObjectURL(personFile) : null),
    [personFile],
  )
  const garmentPreview = useMemo(
    () => (garmentFile ? URL.createObjectURL(garmentFile) : null),
    [garmentFile],
  )

  useEffect(() => {
    return () => {
      if (personPreview) URL.revokeObjectURL(personPreview)
      if (garmentPreview) URL.revokeObjectURL(garmentPreview)
    }
  }, [personPreview, garmentPreview])

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Fit360 home">
          <span className="brand-mark">F</span>
          <span>FIT360 <em>AI</em></span>
        </a>
        <nav>
          <a href="#studio">Studio</a>
          <a href="#stylist">Stylist</a>
          <a href="#trends">Trends</a>
        </nav>
        <button className="avatar-button" aria-label="Profile"><CircleUserRound size={21} /></button>
      </header>

      <main id="top">
        <section className="hero">
          <div className="eyebrow"><Sparkles size={15} /> PERSONAL FASHION INTELLIGENCE</div>
          <h1>See the outfit <span>on you</span><br />before you buy.</h1>
          <p>
            Build your digital style profile, photograph any garment, and compare the look
            against your wardrobe, occasion, and current fashion direction.
          </p>
          <div className="hero-actions">
            <a className="primary-button" href="#studio">Create my look <ChevronRight size={17} /></a>
            <span className="privacy-note"><CheckCircle2 size={15} /> Photos stay under your control</span>
          </div>
        </section>

        <section className="studio-section" id="studio">
          <div className="section-heading">
            <div>
              <span className="step-kicker">01 · CREATE</span>
              <h2>Fit360 Studio</h2>
            </div>
            <span className="status-pill"><span /> MVP MODE</span>
          </div>

          <div className="studio-grid">
            <div className="upload-column">
              <UploadCard
                title="Your full-body photo"
                subtitle="Front view · natural pose · good light"
                icon={ScanLine}
                file={personFile}
                onChange={setPersonFile}
              />
              <UploadCard
                title="Garment or product"
                subtitle="Photo it, screenshot it, or upload it"
                icon={Shirt}
                file={garmentFile}
                onChange={setGarmentFile}
              />
            </div>

            <div className="tryon-stage">
              <div className="stage-label">VIRTUAL TRY-ON PREVIEW</div>
              {personPreview ? (
                <div className="person-stage">
                  <img src={personPreview} alt="Your try-on base" />
                  {garmentPreview && (
                    <div className="garment-chip">
                      <img src={garmentPreview} alt="Selected garment" />
                      <span>Selected item</span>
                    </div>
                  )}
                  <div className="view-tabs">
                    <button className="active">Front</button>
                    <button disabled>Side</button>
                    <button disabled>Back</button>
                    <button disabled>360°</button>
                  </div>
                </div>
              ) : (
                <div className="stage-placeholder">
                  <ScanLine size={42} />
                  <strong>Your digital fitting room</strong>
                  <span>Add your body photo to start.</span>
                </div>
              )}

              <button className="tryon-button" onClick={createTryOn} disabled={tryOnState === 'working'}>
                {tryOnState === 'working' ? <RefreshCw className="spin" size={18} /> : <Sparkles size={18} />}
                {tryOnState === 'working' ? 'Preparing look…' : 'Generate try-on'}
              </button>
              {tryOnState === 'missing' && <p className="inline-warning">Add both photos first.</p>}
              {tryOnState === 'mock-ready' && (
                <p className="inline-success">MVP flow works. The next step is connecting the photorealistic VTO engine.</p>
              )}
            </div>
          </div>
        </section>

        <section className="intelligence-grid" id="stylist">
          <article className="style-card">
            <div className="card-title-row">
              <div>
                <span className="step-kicker">02 · UNDERSTAND</span>
                <h3>AI Stylist</h3>
              </div>
              <ScoreRing score={score.score} />
            </div>

            <label className="occasion-field">
              <span>Dress for</span>
              <select value={occasion} onChange={(event) => setOccasion(event.target.value)}>
                <option value="casual">Casual day</option>
                <option value="work">Work</option>
                <option value="dinner">Dinner</option>
                <option value="event">Event</option>
                <option value="travel">Travel</option>
              </select>
            </label>

            <div className="analysis-copy">
              <strong>{score.label}</strong>
              {score.notes?.map((note) => <p key={note}><CheckCircle2 size={15} /> {note}</p>)}
            </div>

            <div className="recommendations">
              <span>Complete the look</span>
              <div>
                {score.recommended_additions?.map((item) => <button key={item}>{item}</button>)}
              </div>
            </div>

            <button className="secondary-button" onClick={analyzeStyle} disabled={loading}>
              {loading ? <RefreshCw className="spin" size={17} /> : <Sparkles size={17} />}
              Re-analyze outfit
            </button>
          </article>

          <article className="trend-card" id="trends">
            <span className="step-kicker">03 · DISCOVER</span>
            <h3>What’s working now</h3>
            <p className="muted">A trend layer that will later combine live fashion signals with your wardrobe and retailer inventory.</p>
            <div className="trend-list">
              {trends.map((trend, index) => (
                <div className="trend-row" key={trend.name}>
                  <span className="trend-number">0{index + 1}</span>
                  <div>
                    <strong>{trend.name}</strong>
                    <span>{trend.why ?? 'Recommended for this look'}</span>
                  </div>
                  <b>{trend.score}%</b>
                </div>
              ))}
            </div>
            <button className="shop-button"><ShoppingBag size={17} /> Find matching products</button>
          </article>
        </section>
      </main>

      <footer>
        <span>FIT360 AI · MVP</span>
        <span>Try-on · Style intelligence · Retail-ready architecture</span>
      </footer>
    </div>
  )
}

import { useEffect, useMemo, useState } from 'react'
import {
  Camera,
  CheckCircle2,
  ChevronRight,
  CircleUserRound,
  History,
  Plus,
  RefreshCw,
  Save,
  ScanLine,
  Shirt,
  ShoppingBag,
  Sparkles,
  Trash2,
} from 'lucide-react'

const USER_ID = 'demo'

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

async function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

async function readApiError(response) {
  try {
    const data = await response.json()
    return data.detail || data.message || `Request failed (${response.status})`
  } catch {
    return `Request failed (${response.status})`
  }
}

function UploadCard({ title, subtitle, icon: Icon, file, remotePreview, onChange }) {
  const localPreview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file])
  const preview = localPreview || remotePreview || null

  useEffect(() => {
    return () => {
      if (localPreview) URL.revokeObjectURL(localPreview)
    }
  }, [localPreview])

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
        accept="image/*"
        capture="environment"
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
      />
      <span className="upload-action"><Camera size={15} /> {preview ? 'Change photo' : 'Add photo'}</span>
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
  const [selectedWardrobeItem, setSelectedWardrobeItem] = useState(null)
  const [garmentName, setGarmentName] = useState('New garment')
  const [garmentCategory, setGarmentCategory] = useState('auto')
  const [occasion, setOccasion] = useState('casual')
  const [score, setScore] = useState(defaultScore)
  const [loading, setLoading] = useState(false)
  const [tryOnState, setTryOnState] = useState('idle')
  const [tryOnMessage, setTryOnMessage] = useState('')
  const [generatedImage, setGeneratedImage] = useState(null)
  const [provider, setProvider] = useState('mock')
  const [profile, setProfile] = useState({
    user_id: USER_ID,
    name: 'My profile',
    height_cm: '',
    preferred_style: 'modern tailored',
  })
  const [profileStatus, setProfileStatus] = useState('')
  const [wardrobe, setWardrobe] = useState([])
  const [looks, setLooks] = useState([])
  const [wardrobeStatus, setWardrobeStatus] = useState('')
  const [trends, setTrends] = useState([
    { name: 'slim retro sneakers', score: 94 },
    { name: 'burgundy bag', score: 91 },
    { name: 'fitted black top', score: 89 },
  ])

  const personPreview = useMemo(
    () => (personFile ? URL.createObjectURL(personFile) : null),
    [personFile],
  )
  const garmentLocalPreview = useMemo(
    () => (garmentFile ? URL.createObjectURL(garmentFile) : null),
    [garmentFile],
  )
  const garmentPreview = garmentLocalPreview || selectedWardrobeItem?.image_data || null
  const stageImage = generatedImage || personPreview

  useEffect(() => {
    return () => {
      if (personPreview) URL.revokeObjectURL(personPreview)
      if (garmentLocalPreview) URL.revokeObjectURL(garmentLocalPreview)
    }
  }, [personPreview, garmentLocalPreview])

  async function loadProfile() {
    try {
      const response = await fetch(`/api/profile/${USER_ID}`)
      if (!response.ok) return
      const data = await response.json()
      setProfile({ ...data, height_cm: data.height_cm ?? '' })
    } catch {}
  }

  async function loadWardrobe() {
    try {
      const response = await fetch(`/api/wardrobe/${USER_ID}`)
      if (!response.ok) return
      const data = await response.json()
      setWardrobe(data.items || [])
    } catch {}
  }

  async function loadLooks() {
    try {
      const response = await fetch(`/api/looks/${USER_ID}`)
      if (!response.ok) return
      const data = await response.json()
      setLooks(data.items || [])
    } catch {}
  }

  useEffect(() => {
    loadProfile()
    loadWardrobe()
    loadLooks()
    fetch('/api/trends')
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (data?.items?.length) setTrends(data.items.slice(0, 3))
      })
      .catch(() => {})
  }, [])

  async function saveProfile() {
    setProfileStatus('saving')
    try {
      const response = await fetch('/api/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: USER_ID,
          name: profile.name || 'My profile',
          height_cm: profile.height_cm ? Number(profile.height_cm) : null,
          preferred_style: profile.preferred_style || 'modern tailored',
        }),
      })
      if (!response.ok) throw new Error(await readApiError(response))
      setProfileStatus('saved')
    } catch (error) {
      setProfileStatus(error.message)
    }
  }

  async function saveGarmentToWardrobe() {
    if (!garmentFile) {
      setWardrobeStatus('Upload a garment first.')
      return
    }
    setWardrobeStatus('saving')
    try {
      const imageData = await fileToDataUrl(garmentFile)
      const response = await fetch('/api/wardrobe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: USER_ID,
          name: garmentName || 'Garment',
          category: garmentCategory,
          image_data: imageData,
        }),
      })
      if (!response.ok) throw new Error(await readApiError(response))
      setWardrobeStatus('saved')
      await loadWardrobe()
    } catch (error) {
      setWardrobeStatus(error.message)
    }
  }

  async function deleteWardrobeItem(itemId) {
    try {
      const response = await fetch(`/api/wardrobe/${itemId}`, { method: 'DELETE' })
      if (!response.ok) return
      if (selectedWardrobeItem?.id === itemId) setSelectedWardrobeItem(null)
      await loadWardrobe()
    } catch {}
  }

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

  async function pollTryOn(predictionId, providerName) {
    for (let attempt = 0; attempt < 30; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 2500))
      const response = await fetch(`/api/tryon/status/${predictionId}`)
      if (!response.ok) throw new Error(await readApiError(response))
      const data = await response.json()

      if (data.status === 'completed') {
        const outputUrl = data.output?.[0] || null
        if (outputUrl) {
          setGeneratedImage(outputUrl)
          setTryOnState('ready')
          setTryOnMessage('Photorealistic try-on generated.')
          await fetch('/api/looks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: USER_ID,
              prediction_id: predictionId,
              provider: providerName,
              status: 'completed',
              output_url: outputUrl,
              garment_name: selectedWardrobeItem?.name || garmentName,
            }),
          })
          await loadLooks()
        } else {
          setTryOnState('mock-ready')
          setTryOnMessage('The fitting-room workflow is working in free mock mode. Add a provider API key for generated clothing images.')
        }
        return
      }

      if (!['starting', 'in_queue', 'processing', 'queued'].includes(data.status)) {
        throw new Error(data.error || `Try-on stopped with status: ${data.status}`)
      }
      setTryOnMessage(`AI try-on: ${data.status.replace('_', ' ')}…`)
    }
    throw new Error('Try-on is taking longer than expected. Try again shortly.')
  }

  async function createTryOn() {
    const garmentData = garmentFile
      ? await fileToDataUrl(garmentFile)
      : selectedWardrobeItem?.image_data

    if (!personFile || !garmentData) {
      setTryOnState('missing')
      setTryOnMessage('Add your full-body photo and a garment first.')
      return
    }

    setTryOnState('working')
    setTryOnMessage('Uploading images securely to the try-on service…')
    setGeneratedImage(null)

    try {
      const personData = await fileToDataUrl(personFile)
      const response = await fetch('/api/tryon', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: USER_ID,
          person_image: personData,
          garment_image: garmentData,
          category: selectedWardrobeItem?.category || garmentCategory,
          garment_name: selectedWardrobeItem?.name || garmentName,
        }),
      })

      if (!response.ok) throw new Error(await readApiError(response))
      const data = await response.json()
      setProvider(data.provider || 'mock')

      if (data.status === 'completed') {
        setTryOnState('mock-ready')
        setTryOnMessage(data.message || 'Try-on flow completed.')
        return
      }

      setTryOnMessage('AI is fitting the garment to your body photo…')
      await pollTryOn(data.prediction_id, data.provider)
    } catch (error) {
      setTryOnState('error')
      setTryOnMessage(error.message)
    }
  }

  function selectWardrobeItem(item) {
    setSelectedWardrobeItem(item)
    setGarmentFile(null)
    setGarmentName(item.name)
    setGarmentCategory(item.category)
    setGeneratedImage(null)
    setTryOnState('idle')
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Fit360 home">
          <span className="brand-mark">F</span>
          <span>FIT360 <em>AI</em></span>
        </a>
        <nav>
          <a href="#studio">Studio</a>
          <a href="#profile">Profile</a>
          <a href="#wardrobe">Wardrobe</a>
          <a href="#stylist">Stylist</a>
        </nav>
        <a className="avatar-button" href="#profile" aria-label="Profile"><CircleUserRound size={21} /></a>
      </header>

      <main id="top">
        <section className="hero">
          <div className="eyebrow"><Sparkles size={15} /> PERSONAL FASHION INTELLIGENCE</div>
          <h1>See the outfit <span>on you</span><br />before you buy.</h1>
          <p>
            Create your profile once, save your wardrobe, photograph any garment and generate a personalized virtual try-on.
          </p>
          <div className="hero-actions">
            <a className="primary-button" href="#studio">Create my look <ChevronRight size={17} /></a>
            <span className="privacy-note"><CheckCircle2 size={15} /> Your profile and wardrobe are reusable</span>
          </div>
        </section>

        <section className="profile-section" id="profile">
          <div className="section-heading">
            <div>
              <span className="step-kicker">00 · REMEMBER ME</span>
              <h2>My Fit360 profile</h2>
            </div>
          </div>
          <div className="profile-card">
            <label>
              <span>Name</span>
              <input value={profile.name || ''} onChange={(event) => setProfile({ ...profile, name: event.target.value })} />
            </label>
            <label>
              <span>Height (cm)</span>
              <input type="number" min="100" max="230" value={profile.height_cm ?? ''} onChange={(event) => setProfile({ ...profile, height_cm: event.target.value })} />
            </label>
            <label>
              <span>Preferred style</span>
              <input value={profile.preferred_style || ''} onChange={(event) => setProfile({ ...profile, preferred_style: event.target.value })} />
            </label>
            <button className="secondary-button compact" onClick={saveProfile}><Save size={16} /> Save profile</button>
            {profileStatus && <span className="save-status">{profileStatus === 'saved' ? 'Profile saved.' : profileStatus === 'saving' ? 'Saving…' : profileStatus}</span>}
          </div>
        </section>

        <section className="studio-section" id="studio">
          <div className="section-heading">
            <div>
              <span className="step-kicker">01 · CREATE</span>
              <h2>Fit360 Studio</h2>
            </div>
            <span className="status-pill"><span /> {provider === 'fashn' ? 'AI CONNECTED' : 'FREE MVP MODE'}</span>
          </div>

          <div className="studio-grid">
            <div className="upload-column">
              <UploadCard
                title="Your full-body photo"
                subtitle="Front view · natural pose · good light"
                icon={ScanLine}
                file={personFile}
                onChange={(file) => {
                  setPersonFile(file)
                  setGeneratedImage(null)
                }}
              />
              <UploadCard
                title="Garment or product"
                subtitle="Photo it, screenshot it, upload it, or choose from wardrobe"
                icon={Shirt}
                file={garmentFile}
                remotePreview={selectedWardrobeItem?.image_data}
                onChange={(file) => {
                  setGarmentFile(file)
                  setSelectedWardrobeItem(null)
                  setGeneratedImage(null)
                }}
              />

              <div className="garment-meta">
                <input aria-label="Garment name" value={garmentName} onChange={(event) => setGarmentName(event.target.value)} placeholder="Garment name" />
                <select value={garmentCategory} onChange={(event) => setGarmentCategory(event.target.value)}>
                  <option value="auto">Auto category</option>
                  <option value="tops">Top</option>
                  <option value="bottoms">Bottom</option>
                  <option value="one-pieces">Dress / one-piece</option>
                </select>
                <button onClick={saveGarmentToWardrobe}><Plus size={15} /> Save to wardrobe</button>
                {wardrobeStatus && <span>{wardrobeStatus === 'saved' ? 'Saved to wardrobe.' : wardrobeStatus === 'saving' ? 'Saving…' : wardrobeStatus}</span>}
              </div>
            </div>

            <div className="tryon-stage">
              <div className="stage-label">VIRTUAL TRY-ON PREVIEW</div>
              {stageImage ? (
                <div className="person-stage">
                  <img src={stageImage} alt="Your try-on" />
                  {garmentPreview && !generatedImage && (
                    <div className="garment-chip">
                      <img src={garmentPreview} alt="Selected garment" />
                      <span>{selectedWardrobeItem?.name || garmentName}</span>
                    </div>
                  )}
                  <div className="view-tabs">
                    <button className="active">Front</button>
                    <button title="Multi-view generation comes next" disabled>Side</button>
                    <button title="Multi-view generation comes next" disabled>Back</button>
                    <button title="Interactive 360 comes after multi-view" disabled>360°</button>
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
                {tryOnState === 'working' ? 'Generating look…' : generatedImage ? 'Generate another' : 'Generate try-on'}
              </button>
              {tryOnMessage && (
                <p className={tryOnState === 'error' || tryOnState === 'missing' ? 'inline-warning' : 'inline-success'}>{tryOnMessage}</p>
              )}
            </div>
          </div>
        </section>

        <section className="wardrobe-section" id="wardrobe">
          <div className="section-heading">
            <div>
              <span className="step-kicker">02 · MY CLOSET</span>
              <h2>Wardrobe</h2>
            </div>
            <span className="count-pill">{wardrobe.length} items</span>
          </div>
          {wardrobe.length ? (
            <div className="wardrobe-grid">
              {wardrobe.map((item) => (
                <article className={`wardrobe-item ${selectedWardrobeItem?.id === item.id ? 'selected' : ''}`} key={item.id}>
                  <button className="wardrobe-select" onClick={() => selectWardrobeItem(item)}>
                    {item.image_data ? <img src={item.image_data} alt={item.name} /> : <Shirt size={28} />}
                    <span><strong>{item.name}</strong><small>{item.category}</small></span>
                  </button>
                  <button className="delete-button" aria-label={`Delete ${item.name}`} onClick={() => deleteWardrobeItem(item.id)}><Trash2 size={14} /></button>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-strip"><Shirt size={20} /> Save garments above and they will appear here.</div>
          )}
        </section>

        <section className="intelligence-grid" id="stylist">
          <article className="style-card">
            <div className="card-title-row">
              <div>
                <span className="step-kicker">03 · UNDERSTAND</span>
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
              <div>{score.recommended_additions?.map((item) => <button key={item}>{item}</button>)}</div>
            </div>

            <button className="secondary-button" onClick={analyzeStyle} disabled={loading}>
              {loading ? <RefreshCw className="spin" size={17} /> : <Sparkles size={17} />}
              Re-analyze outfit
            </button>
          </article>

          <article className="trend-card" id="trends">
            <span className="step-kicker">04 · DISCOVER</span>
            <h3>What’s working now</h3>
            <p className="muted">Trend intelligence can later combine live fashion signals with your wardrobe and retailer inventory.</p>
            <div className="trend-list">
              {trends.map((trend, index) => (
                <div className="trend-row" key={trend.name}>
                  <span className="trend-number">0{index + 1}</span>
                  <div><strong>{trend.name}</strong><span>{trend.why ?? 'Recommended for this look'}</span></div>
                  <b>{trend.score}%</b>
                </div>
              ))}
            </div>
            <button className="shop-button"><ShoppingBag size={17} /> Find matching products</button>
          </article>
        </section>

        <section className="history-section">
          <div className="section-heading">
            <div>
              <span className="step-kicker">05 · REMEMBER</span>
              <h2>Saved looks</h2>
            </div>
            <History size={20} />
          </div>
          {looks.length ? (
            <div className="looks-grid">
              {looks.map((look) => (
                <article key={look.id} className="look-card">
                  {look.output_url ? <img src={look.output_url} alt={look.garment_name || 'Saved look'} /> : <div className="look-placeholder"><Sparkles size={24} /></div>}
                  <div><strong>{look.garment_name || 'Virtual try-on'}</strong><span>{look.provider} · {look.status}</span></div>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-strip"><History size={20} /> Your completed AI try-ons will be saved here.</div>
          )}
        </section>
      </main>

      <footer>
        <span>FIT360 AI · MVP 0.2</span>
        <span>Profile · Wardrobe · Virtual try-on · Style intelligence · Saved looks</span>
      </footer>
    </div>
  )
}

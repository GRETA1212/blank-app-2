import { useEffect, useMemo, useState } from 'react'
import {
  BadgeEuro,
  Box,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleGauge,
  LoaderCircle,
  Ruler,
  Save,
  ScanLine,
  ShoppingBag,
  Sparkles,
  Store,
  Upload,
} from 'lucide-react'

const USER_ID = 'demo'
const VIEW_ORDER = ['front', 'left_45', 'left_side', 'back', 'right_side', 'right_45']
const VIEW_LABELS = {
  front: 'Front',
  left_45: 'Left 45°',
  left_side: 'Left side',
  back: 'Back',
  right_side: 'Right side',
  right_45: 'Right 45°',
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

function MetricInput({ label, value, suffix = 'cm', onChange, min = 0, max = 250, step = '0.5' }) {
  return (
    <label className="p2-metric">
      <span>{label}</span>
      <div>
        <input
          type="number"
          min={min}
          max={max}
          step={step}
          value={value ?? ''}
          onChange={(event) => onChange(event.target.value)}
          placeholder="—"
        />
        <em>{suffix}</em>
      </div>
    </label>
  )
}

function ProductCard({ product, selected, onSelect }) {
  return (
    <button className={`p2-product ${selected ? 'selected' : ''}`} onClick={() => onSelect(product)}>
      <div className="p2-product-visual">
        {product.image_url ? <img src={product.image_url} alt={product.name} /> : <ShoppingBag size={28} />}
      </div>
      <span className="p2-product-retailer">{product.retailer_name}</span>
      <strong>{product.name}</strong>
      <div className="p2-product-meta">
        <span>{product.category}</span>
        <b>€{Number(product.price_eur).toFixed(0)}</b>
      </div>
    </button>
  )
}

export default function PhaseTwo() {
  const [body, setBody] = useState({
    user_id: USER_ID,
    bust_cm: '',
    waist_cm: '',
    hip_cm: '',
    inseam_cm: '',
    shoulder_cm: '',
    shoe_eu: '',
    fit_preference: 'regular',
  })
  const [bodyStatus, setBodyStatus] = useState('')
  const [products, setProducts] = useState([])
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [fitResult, setFitResult] = useState(null)
  const [fitStatus, setFitStatus] = useState('')
  const [occasion, setOccasion] = useState('casual')
  const [budget, setBudget] = useState('')
  const [completeLook, setCompleteLook] = useState(null)
  const [lookStatus, setLookStatus] = useState('')
  const [latestLook, setLatestLook] = useState(null)
  const [sourceFile, setSourceFile] = useState(null)
  const [multiview, setMultiview] = useState(null)
  const [multiviewStatus, setMultiviewStatus] = useState('')
  const [viewIndex, setViewIndex] = useState(0)
  const [isGeneratingViews, setIsGeneratingViews] = useState(false)

  const sourcePreview = useMemo(() => {
    if (!sourceFile) return null
    return URL.createObjectURL(sourceFile)
  }, [sourceFile])

  useEffect(() => {
    return () => {
      if (sourcePreview) URL.revokeObjectURL(sourcePreview)
    }
  }, [sourcePreview])

  const outputs = multiview?.outputs || {}
  const availableViews = VIEW_ORDER.filter((angle) => outputs[angle])
  const activeView = availableViews[Math.min(viewIndex, Math.max(0, availableViews.length - 1))] || 'front'
  const activeImage = outputs[activeView] || sourcePreview || latestLook?.output_url || null

  async function loadPhaseTwo() {
    try {
      const [bodyResponse, catalogResponse, looksResponse, multiResponse] = await Promise.all([
        fetch(`/api/body-profile/${USER_ID}`),
        fetch('/api/catalog'),
        fetch(`/api/looks/${USER_ID}`),
        fetch(`/api/multiview/user/${USER_ID}/latest`),
      ])

      if (bodyResponse.ok) {
        const data = await bodyResponse.json()
        setBody({
          ...data,
          bust_cm: data.bust_cm ?? '',
          waist_cm: data.waist_cm ?? '',
          hip_cm: data.hip_cm ?? '',
          inseam_cm: data.inseam_cm ?? '',
          shoulder_cm: data.shoulder_cm ?? '',
          shoe_eu: data.shoe_eu ?? '',
        })
      }
      if (catalogResponse.ok) {
        const data = await catalogResponse.json()
        setProducts(data.items || [])
        if (data.items?.length) setSelectedProduct(data.items[0])
      }
      if (looksResponse.ok) {
        const data = await looksResponse.json()
        const saved = (data.items || []).find((item) => item.output_url)
        if (saved) setLatestLook(saved)
      }
      if (multiResponse.ok) {
        const data = await multiResponse.json()
        if (data.item) setMultiview(data.item)
      }
    } catch {
      // Existing MVP remains usable if phase-two endpoints are temporarily unavailable.
    }
  }

  useEffect(() => {
    loadPhaseTwo()
  }, [])

  async function saveBody() {
    setBodyStatus('Saving…')
    try {
      const response = await fetch('/api/body-profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: USER_ID,
          bust_cm: body.bust_cm ? Number(body.bust_cm) : null,
          waist_cm: body.waist_cm ? Number(body.waist_cm) : null,
          hip_cm: body.hip_cm ? Number(body.hip_cm) : null,
          inseam_cm: body.inseam_cm ? Number(body.inseam_cm) : null,
          shoulder_cm: body.shoulder_cm ? Number(body.shoulder_cm) : null,
          shoe_eu: body.shoe_eu ? Number(body.shoe_eu) : null,
          fit_preference: body.fit_preference,
        }),
      })
      if (!response.ok) throw new Error(await readApiError(response))
      setBodyStatus('Measurements saved.')
    } catch (error) {
      setBodyStatus(error.message)
    }
  }

  async function recommendSize() {
    if (!selectedProduct) return
    setFitStatus('Calculating size…')
    setFitResult(null)
    try {
      const response = await fetch('/api/fit/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: USER_ID, product_id: selectedProduct.id }),
      })
      if (!response.ok) throw new Error(await readApiError(response))
      const data = await response.json()
      setFitResult(data)
      setFitStatus('')
    } catch (error) {
      setFitStatus(error.message)
    }
  }

  async function buildCompleteLook() {
    setLookStatus('Building your look…')
    setCompleteLook(null)
    try {
      const response = await fetch('/api/catalog/complete-look', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: USER_ID,
          anchor_product_id: selectedProduct?.id || null,
          occasion,
          max_budget_eur: budget ? Number(budget) : null,
        }),
      })
      if (!response.ok) throw new Error(await readApiError(response))
      setCompleteLook(await response.json())
      setLookStatus('')
    } catch (error) {
      setLookStatus(error.message)
    }
  }

  async function pollMultiview(setId) {
    for (let attempt = 0; attempt < 45; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 3000))
      const response = await fetch(`/api/multiview/${setId}`)
      if (!response.ok) throw new Error(await readApiError(response))
      const data = await response.json()
      setMultiview(data)
      setViewIndex(0)

      if (['completed', 'partial', 'failed', 'mock'].includes(data.status)) return data
      setMultiviewStatus(`Generating angles… ${Object.keys(data.outputs || {}).length}/6 ready`)
    }
    throw new Error('The 360 generation is still processing. You can return later and reload the latest set.')
  }

  async function generateMultiview() {
    setIsGeneratingViews(true)
    setMultiviewStatus('Preparing AI 360 views…')
    setViewIndex(0)
    try {
      const sourceImage = sourceFile
        ? await fileToDataUrl(sourceFile)
        : latestLook?.output_url || multiview?.outputs?.front

      if (!sourceImage) {
        throw new Error('Generate a try-on above or upload a finished outfit image first.')
      }

      const response = await fetch('/api/multiview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: USER_ID,
          source_image: sourceImage,
          garment_name: latestLook?.garment_name || selectedProduct?.name || 'Outfit',
        }),
      })
      if (!response.ok) throw new Error(await readApiError(response))
      const data = await response.json()
      setMultiview(data)

      if (data.status === 'processing') {
        const finalData = await pollMultiview(data.id)
        if (finalData.status === 'completed') setMultiviewStatus('Six-view AI fitting set ready.')
        else if (finalData.status === 'partial') setMultiviewStatus('Some angles are ready; one or more AI views could not be generated.')
        else setMultiviewStatus('View generation did not complete.')
      } else {
        setMultiviewStatus(data.message || 'Multi-view workflow is in mock mode.')
      }
    } catch (error) {
      setMultiviewStatus(error.message)
    } finally {
      setIsGeneratingViews(false)
    }
  }

  function moveView(delta) {
    if (!availableViews.length) return
    setViewIndex((current) => {
      const next = current + delta
      if (next < 0) return availableViews.length - 1
      if (next >= availableViews.length) return 0
      return next
    })
  }

  return (
    <section className="p2-shell" id="fit360-phase-two">
      <div className="p2-header">
        <div>
          <span className="p2-kicker">FIT360 · PHASE 2</span>
          <h2>Fit, 360° and complete-look commerce</h2>
          <p>
            Turn the first try-on into a reusable fitting profile, multi-angle fashion view and retailer shopping recommendation.
          </p>
        </div>
        <span className="p2-badge"><Sparkles size={14} /> B2B ENGINE</span>
      </div>

      <div className="p2-grid p2-grid-two">
        <article className="p2-card">
          <div className="p2-title-row">
            <div className="p2-icon"><Ruler size={21} /></div>
            <div>
              <span className="p2-step">04 · FIT PROFILE</span>
              <h3>Body measurements</h3>
            </div>
          </div>
          <p className="p2-muted">
            Measurements make size recommendations useful. Fit360 does not claim to infer exact body measurements from one photo.
          </p>
          <div className="p2-metrics-grid">
            <MetricInput label="Bust" value={body.bust_cm} onChange={(value) => setBody({ ...body, bust_cm: value })} min={50} max={180} />
            <MetricInput label="Waist" value={body.waist_cm} onChange={(value) => setBody({ ...body, waist_cm: value })} min={45} max={180} />
            <MetricInput label="Hips" value={body.hip_cm} onChange={(value) => setBody({ ...body, hip_cm: value })} min={50} max={200} />
            <MetricInput label="Inseam" value={body.inseam_cm} onChange={(value) => setBody({ ...body, inseam_cm: value })} min={45} max={120} />
            <MetricInput label="Shoulders" value={body.shoulder_cm} onChange={(value) => setBody({ ...body, shoulder_cm: value })} min={25} max={70} />
            <MetricInput label="Shoe" value={body.shoe_eu} onChange={(value) => setBody({ ...body, shoe_eu: value })} min={30} max={52} suffix="EU" step="1" />
          </div>
          <label className="p2-select-field">
            <span>Fit preference</span>
            <select value={body.fit_preference} onChange={(event) => setBody({ ...body, fit_preference: event.target.value })}>
              <option value="slim">Slim</option>
              <option value="regular">Regular</option>
              <option value="relaxed">Relaxed</option>
            </select>
          </label>
          <button className="p2-primary" onClick={saveBody}><Save size={16} /> Save measurements</button>
          {bodyStatus && <p className="p2-status">{bodyStatus}</p>}
        </article>

        <article className="p2-card">
          <div className="p2-title-row">
            <div className="p2-icon"><CircleGauge size={21} /></div>
            <div>
              <span className="p2-step">05 · SIZE ENGINE</span>
              <h3>What size should I buy?</h3>
            </div>
          </div>
          <div className="p2-product-picker">
            {products.slice(0, 6).map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                selected={selectedProduct?.id === product.id}
                onSelect={(item) => {
                  setSelectedProduct(item)
                  setFitResult(null)
                  setFitStatus('')
                }}
              />
            ))}
          </div>
          <button className="p2-primary" onClick={recommendSize} disabled={!selectedProduct}>
            <Ruler size={16} /> Recommend my size
          </button>
          {fitResult && (
            <div className="p2-fit-result">
              <span>Recommended size</span>
              <strong>{fitResult.recommended_size}</strong>
              <div><CheckCircle2 size={15} /> {fitResult.confidence}% measurement confidence</div>
              <p>{fitResult.basis}</p>
            </div>
          )}
          {fitStatus && <p className="p2-status">{fitStatus}</p>}
        </article>
      </div>

      <article className="p2-card p2-360-card">
        <div className="p2-title-row">
          <div className="p2-icon"><ScanLine size={21} /></div>
          <div>
            <span className="p2-step">06 · MULTI-VIEW</span>
            <h3>AI 360° fitting view</h3>
          </div>
        </div>
        <p className="p2-muted p2-copy-wide">
          Fit360 generates additional viewpoints while preserving the person and outfit. It is an AI multi-view preview, not yet a geometry-accurate 3D cloth simulation.
        </p>

        <div className="p2-360-layout">
          <div className="p2-viewer">
            {activeImage ? (
              <img src={activeImage} alt={`${VIEW_LABELS[activeView] || activeView} outfit view`} />
            ) : (
              <div className="p2-empty-viewer"><Box size={42} /><strong>No outfit source yet</strong><span>Use a saved try-on above or upload one here.</span></div>
            )}
            {activeImage && <span className="p2-view-label">{VIEW_LABELS[activeView] || 'Front'}</span>}
            {availableViews.length > 1 && (
              <>
                <button className="p2-view-arrow left" onClick={() => moveView(-1)} aria-label="Previous angle"><ChevronLeft /></button>
                <button className="p2-view-arrow right" onClick={() => moveView(1)} aria-label="Next angle"><ChevronRight /></button>
              </>
            )}
          </div>

          <div className="p2-360-controls">
            <label className="p2-upload-source">
              <Upload size={18} />
              <div><strong>Upload finished outfit</strong><span>Optional if a saved try-on already exists</span></div>
              <input hidden type="file" accept="image/*" onChange={(event) => setSourceFile(event.target.files?.[0] || null)} />
            </label>

            <div className="p2-angle-track">
              {VIEW_ORDER.map((angle) => (
                <button
                  key={angle}
                  className={activeView === angle ? 'active' : ''}
                  disabled={!outputs[angle]}
                  onClick={() => setViewIndex(Math.max(0, availableViews.indexOf(angle)))}
                >
                  <span>{VIEW_LABELS[angle]}</span>
                  <i>{outputs[angle] ? 'ready' : 'pending'}</i>
                </button>
              ))}
            </div>

            <button className="p2-primary p2-large" onClick={generateMultiview} disabled={isGeneratingViews}>
              {isGeneratingViews ? <LoaderCircle className="p2-spin" size={18} /> : <Sparkles size={18} />}
              {isGeneratingViews ? 'Generating viewpoints…' : 'Generate 360° beta'}
            </button>
            {multiviewStatus && <p className="p2-status">{multiviewStatus}</p>}
          </div>
        </div>
      </article>

      <div className="p2-grid p2-grid-commerce">
        <article className="p2-card">
          <div className="p2-title-row">
            <div className="p2-icon"><ShoppingBag size={21} /></div>
            <div>
              <span className="p2-step">07 · COMPLETE THE LOOK</span>
              <h3>Shop the whole outfit</h3>
            </div>
          </div>
          <div className="p2-commerce-controls">
            <label>
              <span>Occasion</span>
              <select value={occasion} onChange={(event) => setOccasion(event.target.value)}>
                <option value="casual">Casual</option>
                <option value="work">Work</option>
                <option value="dinner">Dinner</option>
                <option value="event">Event</option>
                <option value="travel">Travel</option>
              </select>
            </label>
            <label>
              <span>Budget €</span>
              <input type="number" min="0" placeholder="No limit" value={budget} onChange={(event) => setBudget(event.target.value)} />
            </label>
          </div>
          <button className="p2-primary" onClick={buildCompleteLook}><Sparkles size={16} /> Build complete look</button>
          {lookStatus && <p className="p2-status">{lookStatus}</p>}
          {completeLook && (
            <div className="p2-complete-look">
              {completeLook.items.map((item) => (
                <div key={item.id}>
                  <span>{item.category}</span>
                  <strong>{item.name}</strong>
                  <b>€{Number(item.price_eur).toFixed(0)}</b>
                </div>
              ))}
              <footer><span>Total</span><strong>€{Number(completeLook.total_eur).toFixed(2)}</strong></footer>
            </div>
          )}
        </article>

        <article className="p2-card p2-b2b-card">
          <div className="p2-title-row">
            <div className="p2-icon"><Store size={21} /></div>
            <div>
              <span className="p2-step">08 · RETAILER LAYER</span>
              <h3>Built to sell B2B</h3>
            </div>
          </div>
          <p>
            Retailers can feed their own products, prices, sizes and size charts into the catalog API. Fit360 can then return try-on, size and complete-look recommendations from that retailer’s inventory.
          </p>
          <div className="p2-b2b-points">
            <div><Store size={17} /><span><strong>Catalog API</strong> Product and size-chart ingestion</span></div>
            <div><Ruler size={17} /><span><strong>Fit API</strong> Measurement-to-size recommendation</span></div>
            <div><ShoppingBag size={17} /><span><strong>Commerce API</strong> Complete-look basket generation</span></div>
            <div><BadgeEuro size={17} /><span><strong>Revenue layer</strong> SaaS, API usage and affiliate-ready</span></div>
          </div>
        </article>
      </div>
    </section>
  )
}

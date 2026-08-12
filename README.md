# Fit360 AI

Fit360 AI is a B2B/consumer fashion intelligence MVP combining reusable personal profiles, digital wardrobe, photorealistic virtual try-on, AI multi-view fitting previews, measurement-based size recommendations, complete-look commerce, and retailer catalog APIs.

## Implemented

- Mobile-friendly React/Vite interface.
- Reusable style profile and height.
- Persistent body-measurement profile: bust, waist, hips, inseam, shoulders, shoe size and fit preference.
- Upload a full-body photo from camera or photo library.
- Upload garments/products and save them to a persistent wardrobe.
- Persistent saved-look history.
- FastAPI + SQLite persistence.
- Real FASHN virtual try-on adapter with status polling.
- `tryon-v1.6` fast/cost-sensitive mode and optional `tryon-max` quality mode.
- Free mock provider mode when no paid VTO provider is configured.
- AI multi-view / 360 beta using a completed outfit image as the source.
- Front, left 45°, left side, back, right side and right 45° view workflow.
- Measurement + retailer-size-chart recommendation engine.
- Seed retailer catalog for demo/testing.
- Retailer catalog ingestion endpoint.
- Complete-the-look basket recommendations by occasion and optional budget.
- AI stylist score and trend recommendation UI.
- CI for backend route/import checks and frontend production build.

## Architecture

```text
frontend/
  React + Vite fitting room
  PhaseTwo: body fit, multi-view, sizing and commerce UI

backend/
  FastAPI API
  SQLite persistence
  FASHN VTO + edit provider integration
  size recommendation engine
  retailer catalog + complete-look engine

.github/
  GitHub Actions CI
```

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Fit360 defaults to free mock mode:

```text
FIT360_VTON_PROVIDER=mock
```

To enable real FASHN generation, set server-side secrets only:

```text
FIT360_VTON_PROVIDER=fashn
FASHN_API_KEY=your_private_key_here
```

Choose the VTO model:

```text
# Fast, lower-cost try-on
FIT360_VTON_MODEL=tryon-v1.6

# Higher-quality and broader wearable support
FIT360_VTON_MODEL=tryon-max
```

For shorter provider retention, request Base64 outputs where supported:

```text
FIT360_PRIVATE_OUTPUT=true
```

Optional persistent database location:

```text
FIT360_DB_PATH=/path/to/fit360.db
```

Never commit provider keys to GitHub.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Product flow

1. Save the Fit360 style profile.
2. Save body measurements and fit preference.
3. Take/upload a full-body photo.
4. Upload a garment or select one from My Wardrobe.
5. Generate the photorealistic try-on.
6. Save/reuse the finished look.
7. Generate the AI 360 beta: front, three-quarter, side and back viewpoints.
8. Select a retailer product and request a size recommendation.
9. Build a complete outfit from that retailer's connected catalog.

## B2B API layer

Key phase-two endpoints:

```text
GET/POST /api/body-profile
GET/POST /api/catalog
POST     /api/fit/recommend
POST     /api/catalog/complete-look
POST     /api/multiview
GET      /api/multiview/{set_id}
```

The demo catalog is intentionally synthetic. Production merchants should ingest their own product feed, prices, image URLs, inventory and official size charts.

## Important product boundaries

- The 360 feature is currently AI-generated multi-view imagery, not a metrically accurate 3D mesh or physics-based cloth simulation.
- Size recommendations are based on saved measurements and retailer size charts; they are not a guarantee of physical fit.
- Exact automatic body measurement from photographs still requires a dedicated validated body-scanning/measurement service.
- Production deployment still needs authentication, per-user data isolation, consent flows, rate limiting, cloud object storage and retailer authorization.

## Next milestones

1. Authentication, consent, retention controls and secure cloud image storage.
2. Real merchant inventory feeds and stock-aware complete-look recommendations.
3. Shopify/retailer embeddable SDK and analytics dashboard.
4. Dedicated body-scanning provider or validated measurement model.
5. Geometry-aware 3D avatar/cloth layer for true rotatable 360 fitting.
6. Live trend-intelligence and retailer product discovery agents.

## Development branch

Implementation remains on `fit360-mvp`. Keep `main` untouched until the MVP is reviewed and tested.

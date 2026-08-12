# Fit360 AI

Fit360 AI is an MVP for a B2B/consumer fashion intelligence platform that combines a reusable personal profile, digital wardrobe, virtual try-on, outfit scoring, saved looks, trend recommendations, and a provider-ready retail architecture.

## MVP implemented

- Mobile-friendly React/Vite interface.
- Save a reusable user style profile and height.
- Upload a full-body photo from camera or photo library.
- Upload garments/products and save them to a persistent wardrobe.
- Re-select wardrobe items for new try-ons.
- Persistent saved-look history.
- FastAPI + SQLite persistence for profiles, wardrobe items, and looks.
- Real FASHN Virtual Try-On v1.6 adapter with status polling.
- Free mock provider mode when no paid VTO provider is configured.
- Front/side/back/360 UI prepared for later multi-view generation.
- AI stylist score and outfit recommendations.
- Trend recommendation endpoint and UI.
- CI for backend import/compile checks and frontend production build.

## Architecture

```text
frontend/   React + Vite customer experience
backend/    FastAPI API, SQLite persistence, and VTO provider layer
.github/    GitHub Actions CI
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

By default Fit360 runs without a paid AI provider:

```text
FIT360_VTON_PROVIDER=mock
```

To enable photorealistic try-on with FASHN, set these environment variables on the server. Never commit the API key to GitHub.

```text
FIT360_VTON_PROVIDER=fashn
FASHN_API_KEY=your_private_key_here
```

Optional persistent database location:

```text
FIT360_DB_PATH=/path/to/fit360.db
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Current product flow

1. Save your Fit360 profile.
2. Take/upload a full-body photo.
3. Upload a garment or select one from My Wardrobe.
4. Generate a try-on.
5. In FASHN mode, the backend submits the images to the provider and polls until the generated image is ready.
6. Completed try-ons are stored in Saved Looks.
7. Reuse wardrobe items for future styling sessions.

## Next product milestones

1. Add authentication, per-user accounts, consent, image-retention controls, and cloud object storage.
2. Generate consistent front/side/back views, followed by an interactive 360 experience.
3. Add body-measurement and size recommendation services.
4. Add retailer catalogue ingestion and complete-the-look recommendations.
5. Add merchant SDK/widget and retailer analytics dashboard.
6. Add a live trend-intelligence agent and product discovery layer.

## Development branch

Implementation is on `fit360-mvp`. Keep `main` untouched until the MVP has been reviewed and tested.

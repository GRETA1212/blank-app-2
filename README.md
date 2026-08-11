# Fit360 AI

Fit360 AI is an MVP for a B2B/consumer fashion intelligence platform that combines a personal fitting-room workflow, outfit scoring, trend recommendations, and a provider-ready virtual try-on integration layer.

## MVP implemented

- Mobile-friendly React/Vite interface.
- Upload a full-body photo from camera or photo library.
- Upload a garment/product image.
- Virtual fitting-room preview workflow.
- Front/side/back/360 UI prepared for later multi-view generation.
- AI stylist score and outfit recommendations.
- Trend recommendation endpoint and UI.
- FastAPI backend with health, trend, style-score, and virtual-try-on provider-hook endpoints.
- CI for backend import/compile checks and frontend production build.

The current try-on step intentionally runs in MVP/mock mode. The product architecture is ready to connect a commercial virtual try-on provider without hard-coding provider credentials into the repository.

## Architecture

```text
frontend/   React + Vite customer experience
backend/    FastAPI API and AI/provider integration layer
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

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Next product milestones

1. Replace mock try-on with a commercial VTO API adapter.
2. Add authentication and consent/privacy controls for body images.
3. Add persistent wardrobe and user style profiles.
4. Add retailer catalogue ingestion and complete-the-look recommendations.
5. Add body-measurement/size recommendation service.
6. Generate consistent front/side/back views, then an interactive 360 experience.
7. Add merchant SDK/widget and analytics dashboard for B2B customers.

## Development branch

Initial implementation is on `fit360-mvp`. Keep `main` untouched until the MVP has been reviewed and tested.

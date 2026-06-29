# Virtual Creator Money Studio

A Streamlit operating system for planning, producing, publishing and measuring fictional virtual creators.

The first creator brands are:

- **Sofia** — beauty and makeup
- **Elena** — real estate and property
- **Luna** — episodic mini-movies

The studio measures retention, follower conversion, publishing status, production cost and profit—not views alone.

## Connected workflow

```text
Niche Manager
→ Trend Radar
→ Daily Content Planner
→ Greta Private Studio
→ Reality Pipeline
→ AI Provider Hub
→ FFmpeg master MP4
→ Publish & Analytics
→ Calendar & Revenue
→ better recommendations tomorrow
```

## Modules

### Niche Manager

Each creator has an editable profile containing:

- primary niche and subtopics
- trend keywords
- target audience
- competitor watchlist
- products and revenue opportunities
- content pillars
- languages and platforms
- topics and claims to avoid

Profiles are stored under `storage/niches.json` and directly influence research and recommendations.

### Trend Radar

- YouTube trend search through the YouTube Data API
- Google Trending Now RSS ingestion
- manually saved TikTok Creative Center, feed and public competitor observations
- scoring for trend strength, niche fit, monetization, originality, production ease and past performance
- no copied TikTok login cookies, Tor routing or block-bypass code

### Daily Content Planner

- creates daily recommendations from Trend Radar data
- falls back to the creator's signature series when trend data is unavailable
- uses the Niche Manager audience, products, content pillars and avoid list
- generates a hook, script, five-shot plan, caption and hashtags
- approves an idea into the content calendar and Greta Private Studio queue

### Character Lab

- appearance, voice, personality and behavior DNA
- wardrobe, locations, actions and camera rules
- permanent consistency rules and negative prompts
- reference-image slots and licensed voice samples
- pre-publish consistency checks

### Reality Pipeline

```text
consenting human performance
→ fictional or authorized creator appearance
→ licensed or consented voice
→ short controllable shots
→ subtitles and sound
→ 1080 × 1920 MP4
→ Reality Gate
```

It includes:

- actor, face, voice and media-rights gates
- AI-disclosure tracking
- five editable shot templates
- project assets and provider manifests
- SRT subtitle generation
- FFmpeg normalization, audio mixing and vertical MP4 assembly
- a quality gate for consistency, anatomy, motion, lip sync, lighting, audio, facts, rights and disclosure

Private assets and renders are stored under `storage/` and ignored by Git.

### AI Provider Hub

- **HeyGen Avatar V** for authorized talking shots
- **Runway** for reference-controlled lifestyle and B-roll shots
- **ElevenLabs** for licensed or consented speech
- one-click submission of all shots
- bulk provider-status refresh
- bulk completed-clip download
- bulk voice generation
- per-shot regeneration controls
- first-pass generation-cost estimate
- provider-neutral job records

### Secure object storage

The app supports S3-compatible object storage for:

- temporary signed HTTPS reference-image links
- provider input media
- publish-ready video assets

This works with AWS S3 and compatible services when the relevant environment variables are configured.

### Publish & Analytics

Publishing is connected through the official `upload-post` Python package:

- one account profile for TikTok, YouTube, Instagram and additional platforms
- secure social-account connection link
- multi-platform video upload
- scheduling and posting queue
- upload history and status polling
- TikTok AI-generated-content flag
- TikTok media-upload or direct-post modes
- YouTube synthetic-media flag and privacy controls
- Instagram Reels settings
- creator-level and post-level analytics

Publishing defaults should remain review-oriented until the workflow is proven: private YouTube, TikTok media upload or self-only, and queueing before public release.

### Calendar & Revenue

- 7–90 day content calendar
- planned, queued and in-production states
- income records for YouTube, TikTok, affiliates, sponsors, digital products, leads, services and licensing
- revenue summaries by creator and source

## Configuration

Copy `.env.example` to `.env`, or add the same values to `.streamlit/secrets.toml`.

### Generation providers

```text
HEYGEN_API_KEY=
HEYGEN_AVATAR_ID=
HEYGEN_VOICE_ID=
HEYGEN_ENGINE=avatar_v

RUNWAYML_API_SECRET=
RUNWAY_MODEL=gen4_turbo

ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
```

### Object storage

```text
OBJECT_STORAGE_BUCKET=
OBJECT_STORAGE_REGION=
OBJECT_STORAGE_ENDPOINT_URL=
OBJECT_STORAGE_ACCESS_KEY_ID=
OBJECT_STORAGE_SECRET_ACCESS_KEY=
OBJECT_STORAGE_PUBLIC_BASE_URL=
OBJECT_STORAGE_PREFIX=creator-studio
```

### Trends and publishing

```text
YOUTUBE_DATA_API_KEY=
UPLOAD_POST_API_KEY=
UPLOAD_POST_PROFILE=sofia
```

Never commit real keys, access tokens, browser cookies or voice credentials.

## Run locally on Windows

```powershell
git clone https://github.com/GRETA1212/blank-app-2.git
cd blank-app-2
git checkout feature/provider-orchestrator-v1

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open the Streamlit address, normally:

```text
http://localhost:8501
```

The sidebar includes:

- Greta Private Studio
- Character Lab
- Reality Pipeline
- AI Provider Hub
- Trend Radar
- Daily Planner
- Publish & Analytics
- Calendar & Revenue
- Niche Manager

## FFmpeg

Final MP4 assembly requires FFmpeg on the Windows `PATH`.

```powershell
ffmpeg -version
```

Restart PowerShell and Streamlit after installing FFmpeg or modifying `PATH`.

## Pull the branch into an existing clone

```powershell
git fetch origin
git checkout feature/provider-orchestrator-v1
git pull origin feature/provider-orchestrator-v1
pip install -r requirements.txt
```

## Tests

```powershell
pytest -q
```

Coverage includes:

- character persistence and asset validation
- rights and consent blocking
- shot manifests, subtitles and Reality Gate decisions
- HeyGen, Runway and ElevenLabs request behavior
- bulk generation routing
- Upload-Post account connection, publishing flags and status polling
- niche persistence and blocked-topic filtering
- daily ideas and calendar creation
- revenue aggregation

## First connected Sofia pilot

1. Configure Sofia in **Niche Manager** and **Character Lab**.
2. Fetch or save opportunities in **Trend Radar**.
3. Create and approve one recommendation in **Daily Planner**.
4. Open **Greta Private Studio**, confirm rights, and start production.
5. Review the five shots in **Reality Pipeline**.
6. Open **AI Provider Hub** and generate all shots.
7. Refresh jobs, save finished clips, and assemble the master MP4.
8. Pass every Reality Gate check.
9. Create the `sofia` profile in **Publish & Analytics** and connect TikTok, YouTube and Instagram.
10. Submit with review-safe privacy settings.
11. Import analytics and record revenue.
12. Use the results to improve the next recommendation.

Do not scale to many creators until one creator has a repeatable production workflow, a reliable publishing connection and measurable audience response.

## Current limitations

- Real generation requires paid provider accounts, credits and valid credentials.
- Upload-Post requires its own account and connected social profiles.
- YouTube automated trend search requires a YouTube Data API key.
- TikTok broad organic trends are saved from compliant public sources rather than reverse-engineered logged-in endpoints.
- This is the working Streamlit product layer. A React/FastAPI multi-user SaaS migration should follow after the single-creator workflow is proven.

## Repository branch

```text
feature/provider-orchestrator-v1
```

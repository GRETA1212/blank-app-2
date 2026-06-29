# Virtual Creator Money Studio

A Streamlit system for creating, testing and scaling a network of fictional virtual creators.

The first three creator brands are:

- **Sofia** — beauty and makeup
- **Elena** — real estate and property
- **Luna** — episodic mini-movies

The studio measures **retention, follower conversion and profit**, not views alone.

## Current modules

### Money Studio

- character bibles and custom-character creation
- complete video planning with hooks, scripts, scenes, captions and hashtags
- downloadable production packages
- Viral Test Lab for retention, completion, shares, followers, cost and profit
- SCALE / OPTIMIZE / PAUSE recommendations
- TikTok and YouTube Shorts revenue simulator with editable assumptions
- 30-day launch plan

### Character Lab

- detailed appearance DNA for Sofia, Elena and Luna
- permanent eye, hair, face, signature-item and color-palette rules
- personality, gestures, habits, boundaries and catchphrases
- named reference-image slots for multiple angles and expressions
- local reference-image and licensed voice-sample storage
- persistent profiles under `storage/characters/`
- voice language, accent, pitch, pace, emotional modes and provider IDs
- wardrobe, location and physical-action libraries
- visual, acting, voice and camera direction
- negative prompts and continuity checks
- pre-publish consistency gate

### Reality Pipeline

The **Reality Pipeline** implements the recommended high-realism workflow:

```text
consenting human performance
→ fictional/authorized identity transfer
→ licensed voice and lip sync
→ sound design
→ shot-level quality control
→ 1080 × 1920 MP4 assembly
```

It includes:

- project-level actor, face, voice and media-rights gates
- AI-disclosure tracking
- upload and local storage for consenting performance footage
- approved master-identity and licensed voice references
- five short, controllable shot templates for each character
- editable dialogue, emotion, action, location, wardrobe and camera direction
- provider-neutral manifests containing Character DNA and shot prompts
- automatically generated SRT subtitles
- downloadable production ZIPs
- upload slots for approved generated/identity-transferred shot clips
- optional final narration/audio mix
- FFmpeg normalization and assembly to a 1080 × 1920 MP4
- burned-in subtitles
- a strict Reality Gate for face, skin, motion, hands, lip sync, lighting, world continuity, audio, facts, rights and disclosure

Private performance footage, identity references, voices and renders are stored under `storage/` and ignored by Git.

### AI Provider Hub

The provider hub connects an approved Reality Pipeline project to current external generation services:

- **HeyGen v3** for authorized talking-avatar shots
- **Runway** for reference-controlled lifestyle and B-roll shots
- **ElevenLabs** for a licensed synthetic voice or a voice used with documented consent
- persisted provider task IDs, status, errors and output URLs
- completed-video download into the existing `generated_shots` folder
- automatic handoff to the Reality Pipeline **Assemble MP4** tab

The browser never receives provider API keys. Keys are read only from environment variables or `.streamlit/secrets.toml`.

## Current boundary

The provider layer is now implemented, but real generation still requires Greta's own provider accounts, credits, approved avatar/reference assets and API credentials. Runway reference images currently use an HTTPS or signed storage URL; direct object-storage upload is the next infrastructure step.

Automatic public posting is intentionally excluded until content quality and account safety are proven. The next product layer is trend discovery, daily content planning, YouTube publishing/analytics and TikTok draft publishing.

## Provider configuration

Copy `.env.example` to `.env`, or add the same names to `.streamlit/secrets.toml`:

```text
HEYGEN_API_KEY=
HEYGEN_AVATAR_ID=
HEYGEN_VOICE_ID=
RUNWAYML_API_SECRET=
RUNWAY_MODEL=gen4_turbo
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
```

Never commit real values.

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

Open the address shown by Streamlit, normally:

```text
http://localhost:8501
```

Use the Streamlit sidebar to open:

- Character Lab
- Reality Pipeline
- AI Provider Hub

## FFmpeg requirement

The final MP4 assembly step requires FFmpeg to be installed and available on the Windows `PATH`.

Verify it in PowerShell:

```powershell
ffmpeg -version
```

Restart the terminal after installing or changing the `PATH`, then restart Streamlit.

## Pull the latest branch into an existing clone

```powershell
git fetch origin
git checkout feature/provider-orchestrator-v1
git pull origin feature/provider-orchestrator-v1
```

## Run tests

```powershell
pytest -q
```

Tests cover:

- character identity completeness and persistence
- safe local asset storage
- performable scene packages
- rights and consent blocking
- short-shot realism plans
- SRT timing
- production ZIP generation
- Reality Gate decisions
- provider routing and request payloads
- provider task polling and output handling
- licensed voice audio output
- money and growth calculations

## First connected Sofia pilot

1. Open **Character Lab** and approve Sofia's permanent face, voice, wardrobe and gestures.
2. Open **Reality Pipeline**.
3. Create a Sofia project and confirm all rights.
4. Record a consenting performer completing the short actions when performance transfer is used.
5. Upload the approved identity and licensed voice references.
6. Open **AI Provider Hub** and verify provider readiness.
7. Build the provider generation plan.
8. Submit talking shots to HeyGen and reference-controlled lifestyle shots to Runway.
9. Refresh each task and save the completed clips into Reality Pipeline.
10. Generate or upload the licensed voice/audio mix.
11. Render the vertical MP4 with FFmpeg.
12. Pass every Reality Gate check before publishing.
13. Record the 72-hour results in Viral Test Lab.

Do not expand to 20 characters until one character has a repeatable, high-quality production workflow and measurable audience response.

## Repository branch

```text
feature/provider-orchestrator-v1
```

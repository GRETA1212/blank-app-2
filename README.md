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

The new **Reality Pipeline** implements the recommended high-realism workflow:

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

## What the application does not yet do

The application does not currently call a commercial image-to-video, identity-transfer, digital-twin, voice or lip-sync provider automatically.

It creates the complete provider handoff, accepts the approved returned shot clips, and assembles the final video locally. Provider integrations require the user's own accounts, API credentials, provider terms and consent-compliant workflow.

Automatic posting is intentionally excluded until content quality and account safety are proven.

## Run locally on Windows

```powershell
git clone https://github.com/GRETA1212/blank-app-2.git
cd blank-app-2
git checkout feature/virtual-creator-studio

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
git checkout feature/virtual-creator-studio
git pull origin feature/virtual-creator-studio
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
- money and growth calculations

## First ultra-real pilot

1. Open **Character Lab** and approve Sofia's permanent face, voice, wardrobe and gestures.
2. Open **Reality Pipeline**.
3. Create a Sofia project and confirm all rights.
4. Record a consenting performer completing the five short actions.
5. Upload the master identity and licensed voice reference.
6. Export the provider package.
7. Generate or identity-transfer each shot with an authorized provider.
8. Upload only approved shot clips.
9. Add the licensed narration/audio mix.
10. Render the vertical MP4 with FFmpeg.
11. Pass every Reality Gate check before publishing.
12. Record the 72-hour results in Viral Test Lab.

Do not expand to 20 characters until one character has a repeatable, high-quality production workflow and measurable audience response.

## Repository branch

```text
feature/virtual-creator-studio
```

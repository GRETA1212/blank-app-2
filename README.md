# Virtual Creator Money Studio

A Streamlit MVP for building and testing a network of virtual creators.

The first three creator brands are:

- **Sofia** — beauty and makeup
- **Elena** — real estate and property
- **Luna** — episodic mini-movies

The studio is designed around one rule: measure **retention, follower conversion and profit**, not views alone.

## Current features

### Money Studio

- character bibles for consistent identities
- add custom virtual creators
- create a complete video production plan
- generate hooks, script sections, scenes, captions and hashtags
- download a production package as JSON
- record published-video performance
- calculate a growth score
- receive a scale / optimize / pause recommendation
- simulate TikTok and YouTube Shorts revenue using editable RPM assumptions
- track affiliate, sponsor, lead and production-cost inputs
- follow a practical 30-day launch plan

### Character Lab

The Streamlit sidebar now includes a separate **Character Lab** page with:

- detailed appearance DNA for Sofia, Elena and Luna
- permanent eye, hair, face, signature-item and color-palette rules
- editable personality, gestures, habits and catchphrases
- named reference-image slots for multiple angles and expressions
- local reference-image and licensed voice-sample storage
- persistent character profiles under `storage/characters/`
- voice language, accent, pitch, pace, emotion and provider settings
- explicit voice-rights confirmation before saving provider IDs or samples
- recurring wardrobe, location and action libraries
- scene direction for visual generation, acting, voice and camera
- negative prompts and continuity checks
- a pre-publish consistency gate that approves, requests fixes or rejects a scene
- downloadable Character DNA and scene packages as JSON

Local character media and profiles are ignored by Git so private reference assets are not accidentally committed.

## Important limitation

The application does **not** yet generate or publish the final MP4.

The next engineering milestone is:

1. connect an image/video generation provider to the Character DNA
2. connect a licensed voice provider
3. generate timed narration and subtitles
4. add FFmpeg vertical-video rendering
5. add a render and human-approval queue
6. connect official publishing APIs only after quality is reliable

Manual publishing is intentional during the test phase so broken, repetitive or inaccurate content is not posted automatically.

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

Open the local address shown by Streamlit, normally:

```text
http://localhost:8501
```

Use the Streamlit sidebar to switch between the main studio and **Character Lab**.

## Pull this branch into an existing clone

```powershell
git fetch origin
git checkout feature/virtual-creator-studio
git pull origin feature/virtual-creator-studio
```

## Run tests

```powershell
pytest -q
```

The Character Lab unit tests cover:

- default identity completeness
- profile persistence
- safe reference-image storage
- file validation
- performable scene packages
- consistency-gate decisions

## First real-world experiment

1. Open **Character Lab**.
2. Review Sofia, Elena and Luna's Identity DNA.
3. Upload approved face angles and expression references.
4. Configure only licensed synthetic voices or consenting actor voices.
5. Create one directed scene for each character.
6. Produce and publish three pilot videos per character.
7. Record the 72-hour results in **Viral Test Lab**.

Do not expand to 20 characters until at least one of the first three has a repeatable winning format.

## Repository branch

Development work is currently on:

```text
feature/virtual-creator-studio
```

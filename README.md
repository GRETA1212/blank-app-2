# Virtual Creator Money Studio

A Streamlit MVP for building and testing a network of virtual creators.

The first three creator brands are:

- **Sofia** — beauty and makeup
- **Elena** — real estate and property
- **Luna** — episodic mini-movies

The studio is designed around one rule: measure **retention, follower conversion and profit**, not views alone.

## Current features

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

## Important limitation

This is Phase 1. It does **not** yet generate or publish the final MP4.

The next milestone will add:

1. character reference-image storage
2. image/video asset generation providers
3. voice generation providers
4. subtitles
5. FFmpeg vertical-video rendering
6. a human approval queue
7. official publishing integrations later

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

## First real-world experiment

Create and publish:

- 3 Sofia videos
- 3 Elena videos
- 3 Luna videos

Record the results after 72 hours in **Viral Test Lab**. The program will compare the characters using retention, completion rate, shares, followers gained and profit.

Do not expand to 20 characters until at least one of the first three has a repeatable winning format.

## Repository branch

Development work is currently on:

```text
feature/virtual-creator-studio
```

# Implementation Status

## Implemented

- React and TypeScript Studio Control Center
- PostgreSQL persistence and rerunnable migrations
- Local single-user workspace bootstrap
- SearXNG current-web research
- Evidence, inference, and creative-hypothesis labelling
- Exactly five research ideas per completed scan
- Ollama script and scene generation
- Editable content packages
- Originality-risk and quality review
- Quality-gated pipeline stages
- English, Italian, Albanian, and Macedonian content variants
- Per-language human review and approval status
- Local Piper neural voices for configured languages
- Macedonian eSpeak NG fallback
- Voice preview, installation, and speed control
- faster-whisper transcription of generated audio
- SRT generation from actual audio timestamps
- Transcript-to-script verification reports
- Persistent voice and Whisper model storage
- Manual MiroFish seed generation and report import
- Structured synthetic-audience findings
- Manual performance and revenue ledger
- Local FFmpeg MP4 draft renderer
- Production-job tracking
- Node-RED render webhook flow
- Windows start, stop, and status scripts
- Unit tests for localization and audio helpers
- GitHub Actions definitions for Python, TypeScript, unit tests, and Docker Compose validation

## Deliberately not implemented

- Automatic TikTok, YouTube, Instagram, or Facebook publishing
- Automatic MiroFish submission against undocumented routes
- Live platform analytics without OAuth or official API connections
- Multi-user authentication or public-hosting hardening
- Guaranteed plagiarism detection
- Guaranteed translation, pronunciation, or transcript accuracy
- Revenue prediction from views
- Automatic use of copyrighted or watermarked assets

## Verification status

The code has undergone static review and unit tests are committed. Connector-authored commits did not automatically start GitHub Actions, and the current execution environment could not resolve GitHub or run Docker. Before merging, manually run the CI workflows from GitHub Actions and run the Windows startup script on the target computer.

# Audio and Language Workflow

The dashboard now supports separate English, Italian, Albanian, and Macedonian variants.

## Language workflow

1. Open **Languages**.
2. Select a project and target languages.
3. Add glossary terms as `term=required wording`.
4. Generate variants.
5. Review each title, hook, narration, description, and scene caption.
6. Approve each language separately.

Generated translations always start as `NEEDS_REVIEW`. They cannot be rendered until approved.

## Local voices

Defaults:

- English: `en_US-lessac-medium`
- Italian: `it_IT-paola-medium`
- Albanian: `sq_AL-edon-medium`
- Macedonian: eSpeak NG `mk` fallback

Piper voices are saved in the `piper_voices` Docker volume. Each voice model has its own model card and licence, which must be checked before commercial distribution.

## Subtitle verification

The enhanced renderer creates the voice audio first, transcribes that audio with faster-whisper, and builds the SRT from the transcription. It then compares the transcript with the approved script.

Each production job stores:

- language and selected voice;
- transcript and subtitle links;
- transcript similarity score;
- detected language;
- missing or unexpected word samples;
- a warning when the score is below the configured threshold.

This is a quality-control aid, not a guarantee of correct pronunciation or translation.

## Configuration

```env
PIPER_AUTO_DOWNLOAD=true
PIPER_AUTO_VOICES=en_US-lessac-medium,it_IT-paola-medium,sq_AL-edon-medium
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
SUBTITLE_VERIFY_THRESHOLD=0.82
```

Voice and Whisper models persist across restarts in Docker volumes.

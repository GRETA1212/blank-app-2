from app.audio_enhancements import (
    DEFAULT_VOICE_BY_LANGUAGE,
    VOICE_CATALOG,
    normalized_words,
    srt_timestamp,
)


def test_supported_languages_have_default_voices() -> None:
    assert set(DEFAULT_VOICE_BY_LANGUAGE) == {"en", "it", "sq", "mk"}
    assert all(voice_id in VOICE_CATALOG for voice_id in DEFAULT_VOICE_BY_LANGUAGE.values())


def test_normalized_words_preserves_multilingual_letters() -> None:
    assert normalized_words("Çfarë është GNSS? Геодетски елаборат!") == [
        "çfarë",
        "është",
        "gnss",
        "геодетски",
        "елаборат",
    ]


def test_srt_timestamp() -> None:
    assert srt_timestamp(65.432) == "00:01:05,432"

from app.localization import LANGUAGES, LocalizedSceneText, merge_scenes


def test_all_requested_languages_are_configured() -> None:
    assert set(LANGUAGES) == {"en", "it", "sq", "mk"}
    assert all(item["default_voice_id"] for item in LANGUAGES.values())


def test_merge_scenes_preserves_assets_and_updates_language_text() -> None:
    original = [
        {
            "scene_number": 1,
            "onscreen_text": "English title",
            "voice_segment": "English voice",
            "asset_id": "asset-1",
            "fit": "cover",
        }
    ]
    localized = [
        LocalizedSceneText(
            scene_number=1,
            onscreen_text="Titolo italiano",
            voice_segment="Voce italiana",
        )
    ]
    result = merge_scenes(original, localized)
    assert result[0]["onscreen_text"] == "Titolo italiano"
    assert result[0]["voice_segment"] == "Voce italiana"
    assert result[0]["asset_id"] == "asset-1"
    assert result[0]["fit"] == "cover"

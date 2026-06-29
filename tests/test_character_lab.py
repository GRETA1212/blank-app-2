from pathlib import Path

import pytest

from character_lab import (
    DEFAULT_CHARACTER_DNA,
    build_scene_direction,
    calculate_consistency_score,
    clone_default_character,
    list_assets,
    load_character,
    save_asset,
    save_character,
    validate_asset,
)


def test_default_character_profiles_have_identity_locks() -> None:
    for character in DEFAULT_CHARACTER_DNA.values():
        assert character.appearance.eye_color
        assert character.appearance.signature_item
        assert character.voice.words_per_minute > 0
        assert character.actions
        assert character.locations
        assert character.wardrobe
        assert character.continuity_rules


def test_character_profile_round_trip(tmp_path: Path) -> None:
    sofia = clone_default_character("Sofia")
    sofia.behavior.catchphrase = "Test phrase"
    profile_path = save_character(sofia, tmp_path)

    assert profile_path.exists()
    loaded = load_character("Sofia", tmp_path)
    assert loaded.behavior.catchphrase == "Test phrase"
    assert loaded.appearance.eye_color == sofia.appearance.eye_color


def test_save_reference_asset_to_named_slot(tmp_path: Path) -> None:
    path = save_asset(
        "Sofia",
        "reference_image",
        "../../front face.JPG",
        b"fake-image-bytes",
        slot="front neutral",
        storage_root=tmp_path,
    )

    assert path.exists()
    assert path.suffix == ".jpg"
    assets = list_assets("Sofia", tmp_path)
    assert len(assets) == 1
    assert "references/front-neutral" in assets[0]["relative_path"].replace("\\", "/")


def test_reject_invalid_reference_extension() -> None:
    with pytest.raises(ValueError):
        validate_asset("reference.exe", b"not-an-image", "reference_image")


def test_scene_direction_contains_voice_performance_and_continuity() -> None:
    luna = clone_default_character("Luna")
    scene = build_scene_direction(
        luna,
        dialogue="The message was sent tomorrow.",
        emotion="frightened",
        action_name=luna.actions[0]["name"],
        location_name=luna.locations[0]["name"],
        wardrobe_name=luna.wardrobe[0]["name"],
        camera="close-up, eye level",
        duration_seconds=6,
    )

    assert "Photorealistic recurring virtual character Luna" in scene["visual_prompt"]
    assert "frightened" in scene["voice_direction"]
    assert scene["continuity_checks"]
    assert "different pendant" in scene["negative_prompt"]


def test_consistency_gate_rejects_low_score() -> None:
    result = calculate_consistency_score(
        {"face": True, "voice": False, "hair": False, "rights": True}
    )
    assert result["score"] == 50.0
    assert result["status"] == "REJECT AND REGENERATE"

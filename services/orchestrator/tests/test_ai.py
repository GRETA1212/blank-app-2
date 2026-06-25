import pytest

from app.ai import extract_json


def test_extract_json_plain_object() -> None:
    assert extract_json('{"ok": true}') == {"ok": True}


def test_extract_json_from_markdown_fence() -> None:
    assert extract_json('```json\n{"items": [1, 2]}\n```') == {"items": [1, 2]}


def test_extract_json_with_leading_model_text() -> None:
    assert extract_json('Here is the result:\n{"score": 82}\nDone.') == {"score": 82}


def test_extract_json_rejects_missing_json() -> None:
    with pytest.raises(ValueError):
        extract_json('No structured payload was returned.')

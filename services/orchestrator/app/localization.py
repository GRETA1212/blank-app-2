import json
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb

from .ai import chat_json
from .db import execute_returning, fetch_all, fetch_one, identity

router = APIRouter(prefix="/localization", tags=["localization"])
LanguageCode = Literal["en", "it", "sq", "mk"]

LANGUAGES: dict[str, dict[str, str]] = {
    "en": {"name": "English", "default_voice_id": "en_US-lessac-medium"},
    "it": {"name": "Italian", "default_voice_id": "it_IT-paola-medium"},
    "sq": {"name": "Albanian", "default_voice_id": "sq_AL-edon-medium"},
    "mk": {"name": "Macedonian", "default_voice_id": "mk-espeak"},
}


class LocalizedSceneText(BaseModel):
    scene_number: int
    onscreen_text: str
    voice_segment: str


class LocalizedContent(BaseModel):
    title: str
    hook: str
    narration: str
    description: str
    hashtags: list[str]
    scene_texts: list[LocalizedSceneText]
    translation_notes: str


class GenerateVariantsRequest(BaseModel):
    languages: list[LanguageCode] = Field(default_factory=lambda: ["en", "it", "sq", "mk"])
    glossary: dict[str, str] = Field(default_factory=dict)
    overwrite: bool = False


class UpdateVariantRequest(BaseModel):
    title: str | None = None
    hook: str | None = None
    narration: str | None = None
    description: str | None = None
    hashtags: list[str] | None = None
    scenes: list[dict[str, Any]] | None = None
    voice_id: str | None = None
    translation_notes: str | None = None
    review_status: Literal["NEEDS_REVIEW", "APPROVED", "REJECTED"] | None = None


def serialise(value: Any) -> Any:
    if isinstance(value, list):
        return [serialise(item) for item in value]
    if isinstance(value, dict):
        return {key: serialise(item) for key, item in value.items()}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def project_for_user(project_id: str, user_id: str) -> dict[str, Any]:
    project = fetch_one("select * from projects where id = %s and user_id = %s", (project_id, user_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def english_copy(project: dict[str, Any]) -> LocalizedContent:
    scene_texts = [
        LocalizedSceneText(
            scene_number=int(scene.get("scene_number", index + 1)),
            onscreen_text=str(scene.get("onscreen_text", "")),
            voice_segment=str(scene.get("voice_segment", "")),
        )
        for index, scene in enumerate(project.get("scenes") or [])
    ]
    return LocalizedContent(
        title=project["title"],
        hook=project.get("hook") or "",
        narration=project.get("narration") or "",
        description=project.get("description") or "",
        hashtags=list(project.get("hashtags") or []),
        scene_texts=scene_texts,
        translation_notes="English master copied without translation.",
    )


def merge_scenes(original: list[dict[str, Any]], localized: list[LocalizedSceneText]) -> list[dict[str, Any]]:
    mapped = {item.scene_number: item for item in localized}
    merged: list[dict[str, Any]] = []
    for index, scene in enumerate(original):
        item = dict(scene)
        number = int(item.get("scene_number", index + 1))
        translated = mapped.get(number)
        if translated:
            item["onscreen_text"] = translated.onscreen_text
            item["voice_segment"] = translated.voice_segment
        merged.append(item)
    return merged


async def translate_project(
    project: dict[str, Any],
    language_code: str,
    glossary: dict[str, str],
) -> LocalizedContent:
    language_name = LANGUAGES[language_code]["name"]
    scene_packet = [
        {
            "scene_number": scene.get("scene_number", index + 1),
            "onscreen_text": scene.get("onscreen_text", ""),
            "voice_segment": scene.get("voice_segment", ""),
        }
        for index, scene in enumerate(project.get("scenes") or [])
    ]
    prompt = f"""
Adapt this approved content into {language_name} ({language_code}).

MASTER CONTENT:
Title: {project['title']}
Hook: {project.get('hook') or ''}
Narration: {project.get('narration') or ''}
Description: {project.get('description') or ''}
Hashtags: {json.dumps(project.get('hashtags') or [], ensure_ascii=False)}
Scene text: {json.dumps(scene_packet, ensure_ascii=False)}
Required glossary: {json.dumps(glossary, ensure_ascii=False)}

Return ONLY JSON:
{{
  "title": "...",
  "hook": "...",
  "narration": "...",
  "description": "...",
  "hashtags": ["..."],
  "scene_texts": [{{"scene_number": 1, "onscreen_text": "...", "voice_segment": "..."}}],
  "translation_notes": "..."
}}

Rules:
- Preserve every factual claim, number, proper name, source meaning, legal qualification, and technical limitation.
- Do not add facts, promises, statistics, or cultural assumptions.
- Adapt idiom and rhythm naturally for the target audience rather than translating word-for-word.
- Keep the same scene numbers and return one scene_texts entry for every supplied scene.
- Keep technical terms from the glossary exactly as supplied.
- Hashtags must be relevant translations, not invented trend claims.
- Mention any term that needs human review in translation_notes.
"""
    result = await chat_json(
        prompt,
        "You are a conservative professional localization editor. Preserve meaning and uncertainty exactly.",
        LocalizedContent,
        temperature=0.2,
        timeout=420,
    )
    if len(result.scene_texts) != len(scene_packet):
        raise HTTPException(status_code=502, detail=f"{language_name} localization returned the wrong number of scenes")
    return result


@router.get("/languages")
def list_languages() -> dict[str, Any]:
    return {
        "languages": [
            {"code": code, **data}
            for code, data in LANGUAGES.items()
        ],
        "notice": "Each localized version requires human linguistic and factual review before rendering or publishing.",
    }


@router.get("/variants")
def list_variants(project_id: str | None = None) -> list[dict[str, Any]]:
    user_id, _ = identity()
    if project_id:
        rows = fetch_all(
            "select * from content_variants where user_id = %s and project_id = %s order by language_code",
            (user_id, project_id),
        )
    else:
        rows = fetch_all(
            "select * from content_variants where user_id = %s order by updated_at desc",
            (user_id,),
        )
    return serialise(rows)


@router.post("/projects/{project_id}/generate")
async def generate_variants(project_id: str, request: GenerateVariantsRequest) -> dict[str, Any]:
    user_id, _ = identity()
    project = project_for_user(project_id, user_id)
    requested = list(dict.fromkeys(request.languages))
    results: list[dict[str, Any]] = []

    for language_code in requested:
        existing = fetch_one(
            "select * from content_variants where user_id = %s and project_id = %s and language_code = %s",
            (user_id, project_id, language_code),
        )
        if existing and not request.overwrite:
            results.append(serialise(existing))
            continue

        localized = english_copy(project) if language_code == "en" else await translate_project(
            project,
            language_code,
            request.glossary,
        )
        scenes = merge_scenes(project.get("scenes") or [], localized.scene_texts)
        language = LANGUAGES[language_code]
        row = execute_returning(
            """
            insert into content_variants (
              user_id, project_id, language_code, language_name, title, hook,
              narration, description, hashtags, scenes, voice_id,
              translation_notes, review_status
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'NEEDS_REVIEW')
            on conflict (project_id, language_code) do update set
              title = excluded.title,
              hook = excluded.hook,
              narration = excluded.narration,
              description = excluded.description,
              hashtags = excluded.hashtags,
              scenes = excluded.scenes,
              voice_id = excluded.voice_id,
              translation_notes = excluded.translation_notes,
              review_status = 'NEEDS_REVIEW'
            returning *
            """,
            (
                user_id,
                project_id,
                language_code,
                language["name"],
                localized.title,
                localized.hook,
                localized.narration,
                localized.description,
                localized.hashtags,
                Jsonb(scenes),
                language["default_voice_id"],
                localized.translation_notes,
            ),
        )
        assert row is not None
        results.append(serialise(row))

    return {
        "variants": results,
        "notice": "Generated variants remain NEEDS_REVIEW until a human approves the language and facts.",
    }


@router.patch("/variants/{variant_id}")
def update_variant(variant_id: str, request: UpdateVariantRequest) -> dict[str, Any]:
    user_id, _ = identity()
    current = fetch_one("select * from content_variants where id = %s and user_id = %s", (variant_id, user_id))
    if current is None:
        raise HTTPException(status_code=404, detail="Localized variant not found")
    changes = request.model_dump(exclude_unset=True)
    if not changes:
        return serialise(current)
    assignments: list[str] = []
    values: list[Any] = []
    for field, value in changes.items():
        assignments.append(f"{field} = %s")
        values.append(Jsonb(value) if field == "scenes" else value)
    values.extend([variant_id, user_id])
    row = execute_returning(
        f"update content_variants set {', '.join(assignments)} where id = %s and user_id = %s returning *",
        tuple(values),
    )
    assert row is not None
    return serialise(row)

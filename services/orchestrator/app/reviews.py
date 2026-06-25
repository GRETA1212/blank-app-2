from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .db import execute_returning, fetch_one, identity

router = APIRouter(prefix="/reviews", tags=["reviews"])


class ReviewDecision(BaseModel):
    status: Literal["PENDING", "APPROVED", "REJECTED"]
    factual_review: bool = False
    rights_review: bool = False
    ai_disclosure_review: bool = False
    audio_review: bool = False
    visual_review: bool = False
    subtitle_review: bool = False
    reviewer_notes: str = Field(default="", max_length=10000)


def serialise(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: serialise(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialise(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


@router.get("/{project_id}")
def get_review(project_id: str) -> dict[str, Any]:
    user_id, _ = identity()
    project = fetch_one("select id from projects where id = %s and user_id = %s", (project_id, user_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    row = fetch_one("select * from approval_reviews where project_id = %s and user_id = %s", (project_id, user_id))
    if row is None:
        return {
            "project_id": project_id,
            "status": "PENDING",
            "factual_review": False,
            "rights_review": False,
            "ai_disclosure_review": False,
            "audio_review": False,
            "visual_review": False,
            "subtitle_review": False,
            "reviewer_notes": "",
        }
    return serialise(row)


@router.put("/{project_id}")
def save_review(project_id: str, request: ReviewDecision) -> dict[str, Any]:
    user_id, _ = identity()
    project = fetch_one("select * from projects where id = %s and user_id = %s", (project_id, user_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if request.status == "APPROVED":
        checks = [
            request.factual_review,
            request.rights_review,
            request.ai_disclosure_review,
            request.audio_review,
            request.visual_review,
            request.subtitle_review,
        ]
        if not all(checks):
            raise HTTPException(status_code=422, detail="Every human-review checklist item must be completed")
        if (project.get("quality_report") or {}).get("pass") is not True:
            raise HTTPException(status_code=422, detail="The originality-risk and quality review must pass first")
        completed_job = fetch_one(
            "select id from production_jobs where project_id = %s and user_id = %s and status = 'COMPLETED' order by completed_at desc limit 1",
            (project_id, user_id),
        )
        if completed_job is None:
            raise HTTPException(status_code=422, detail="A completed rendered draft is required before approval")

    row = execute_returning(
        """
        insert into approval_reviews (
          user_id, project_id, status, factual_review, rights_review,
          ai_disclosure_review, audio_review, visual_review, subtitle_review,
          reviewer_notes, decided_at
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
          case when %s in ('APPROVED', 'REJECTED') then now() else null end)
        on conflict (project_id) do update set
          status = excluded.status,
          factual_review = excluded.factual_review,
          rights_review = excluded.rights_review,
          ai_disclosure_review = excluded.ai_disclosure_review,
          audio_review = excluded.audio_review,
          visual_review = excluded.visual_review,
          subtitle_review = excluded.subtitle_review,
          reviewer_notes = excluded.reviewer_notes,
          decided_at = excluded.decided_at
        returning *
        """,
        (
            user_id,
            project_id,
            request.status,
            request.factual_review,
            request.rights_review,
            request.ai_disclosure_review,
            request.audio_review,
            request.visual_review,
            request.subtitle_review,
            request.reviewer_notes,
            request.status,
        ),
    )
    assert row is not None
    if request.status == "APPROVED":
        execute_returning(
            "update projects set status = 'REVIEW' where id = %s and user_id = %s returning id",
            (project_id, user_id),
        )
    return serialise(row)

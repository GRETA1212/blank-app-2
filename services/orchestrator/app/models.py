from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl

ProjectStatus = Literal[
    "QUEUE",
    "SCRIPTED",
    "IN_PRODUCTION",
    "RENDERING",
    "REVIEW",
    "PUBLISHED",
]


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=30000)
    system: str = Field(default="You are a careful content studio assistant.", max_length=8000)
    temperature: float = Field(default=0.4, ge=0, le=1.5)


class GenerateResponse(BaseModel):
    model: str
    content: str


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    audience: str = Field(min_length=2, max_length=500)
    platform: str = Field(default="YouTube", max_length=100)
    region: str = Field(default="Global", max_length=100)
    language: str = Field(default="English", max_length=100)
    notes: str = Field(default="", max_length=3000)


class SourceItem(BaseModel):
    id: str
    title: str
    url: HttpUrl
    publisher: str = ""
    published_date: str = ""
    snippet: str = ""


class ResearchIdea(BaseModel):
    topic: str
    angle: str
    hook: str
    rationale: str
    audience: str
    format: Literal["long_video", "short_video"]
    estimated_duration: str
    supporting_source_ids: list[str] = Field(default_factory=list)
    evidence_level: Literal["verified", "inference", "creative_hypothesis"]


class ResearchResult(BaseModel):
    id: str | None = None
    research_date: str
    query_summary: str
    landscape_summary: str
    verified_observations: list[dict[str, Any]]
    content_gaps: list[dict[str, Any]]
    sources: list[SourceItem]
    ideas: list[ResearchIdea]


class ScriptRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    angle: str = Field(default="", max_length=1000)
    audience: str = Field(default="", max_length=500)
    target_minutes: int = Field(default=7, ge=1, le=30)
    tone: str = Field(default="clear and professional", max_length=300)
    creator_notes: str = Field(default="", max_length=12000)
    research_context: dict[str, Any] = Field(default_factory=dict)


class ScriptPackage(BaseModel):
    title: str
    hook: str
    narration: str
    description: str
    hashtags: list[str]
    platform_targets: list[str]


class SceneRequest(BaseModel):
    title: str
    hook: str
    narration: str
    scene_count: int = Field(default=8, ge=4, le=20)


class Scene(BaseModel):
    scene_number: int
    duration_seconds: int = Field(ge=1, le=600)
    purpose: str
    visual_direction: str
    onscreen_text: str
    voice_segment: str
    asset_notes: str


class QualityRequest(BaseModel):
    title: str
    hook: str
    narration: str
    scenes: list[dict[str, Any]] = Field(default_factory=list)
    research_context: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = None


class QualityReport(BaseModel):
    passed: bool = Field(alias="pass")
    score: int = Field(ge=0, le=100)
    blocking_issues: list[str]
    warnings: list[str]
    originality_notes: str
    human_review_checklist: list[str]

    model_config = {"populate_by_name": True}


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    topic: str = Field(min_length=1, max_length=500)
    hook: str = ""
    narration: str = ""
    description: str = ""
    hashtags: list[str] = Field(default_factory=list)
    scenes: list[dict[str, Any]] = Field(default_factory=list)
    quality_report: dict[str, Any] = Field(default_factory=dict)
    status: ProjectStatus = "QUEUE"
    platform_targets: list[str] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    title: str | None = None
    topic: str | None = None
    hook: str | None = None
    narration: str | None = None
    description: str | None = None
    hashtags: list[str] | None = None
    scenes: list[dict[str, Any]] | None = None
    quality_report: dict[str, Any] | None = None
    status: ProjectStatus | None = None
    platform_targets: list[str] | None = None


class MiroFishSeedRequest(BaseModel):
    project_id: str
    topic: str
    audience: dict[str, Any]
    content_variants: list[dict[str, Any]]
    simulation_question: str
    research_context: dict[str, Any] = Field(default_factory=dict)


class SimulationReportRequest(BaseModel):
    project_id: str
    scenario_question: str
    seed_payload: dict[str, Any] = Field(default_factory=dict)
    raw_report: str = Field(min_length=20, max_length=100000)


class PerformanceCreate(BaseModel):
    project_id: str
    platform: str
    recorded_on: date
    views: int = Field(default=0, ge=0)
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    watch_time_minutes: float = Field(default=0, ge=0)
    revenue: float = Field(default=0, ge=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    notes: str = ""

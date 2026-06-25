import json
import os
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb

from .ai import OLLAMA_BASE_URL, OLLAMA_MODEL, chat_json, chat_text
from .db import ensure_local_identity, execute, execute_returning, fetch_all, fetch_one, identity
from .models import (
    GenerateRequest,
    GenerateResponse,
    MiroFishSeedRequest,
    PerformanceCreate,
    ProjectCreate,
    ProjectStatus,
    ProjectUpdate,
    QualityReport,
    QualityRequest,
    ResearchIdea,
    ResearchRequest,
    ResearchResult,
    Scene,
    SceneRequest,
    ScriptPackage,
    ScriptRequest,
    SimulationReportRequest,
    SourceItem,
)
from .search import SEARXNG_BASE_URL, web_search

MIROFISH_BASE_URL = os.getenv("MIROFISH_BASE_URL", "http://localhost:5001")

app = FastAPI(title="Studio Orchestrator", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchAnalysis(BaseModel):
    query_summary: str
    landscape_summary: str
    verified_observations: list[dict[str, Any]]
    content_gaps: list[dict[str, Any]]
    ideas: list[ResearchIdea]


class ScenePackage(BaseModel):
    scenes: list[Scene]


class SimulationFindings(BaseModel):
    audience_segments: list[dict[str, Any]]
    hook_comparison: list[dict[str, Any]]
    objections: list[str]
    predicted_comments: list[str]
    risks: list[str]
    recommended_changes: list[str]
    confidence_notes: str


@app.on_event("startup")
def startup() -> None:
    ensure_local_identity()


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date, UUID)):
        return str(value)
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _require_project(project_id: str, user_id: str) -> dict[str, Any]:
    row = fetch_one(
        "select * from projects where id = %s and user_id = %s",
        (project_id, user_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return row


@app.get("/health")
async def health() -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "ok",
        "database": False,
        "ollama": False,
        "search": False,
        "mirofish": False,
        "model": OLLAMA_MODEL,
    }
    try:
        ensure_local_identity()
        result["database"] = True
    except Exception:
        result["status"] = "degraded"
    async with httpx.AsyncClient(timeout=5) as client:
        for name, url in (
            ("ollama", f"{OLLAMA_BASE_URL}/api/tags"),
            ("search", f"{SEARXNG_BASE_URL}/search?q=health&format=json"),
            ("mirofish", MIROFISH_BASE_URL),
        ):
            try:
                response = await client.get(url)
                result[name] = response.status_code < 500
            except httpx.HTTPError:
                pass
    if not result["ollama"] or not result["database"]:
        result["status"] = "degraded"
    return result


@app.get("/overview")
def overview() -> dict[str, Any]:
    user_id, workspace_id = identity()
    counts = fetch_one(
        """
        select
          count(*) filter (where status = 'QUEUE') as queue,
          count(*) filter (where status = 'SCRIPTED') as scripted,
          count(*) filter (where status = 'IN_PRODUCTION') as in_production,
          count(*) filter (where status = 'RENDERING') as rendering,
          count(*) filter (where status = 'REVIEW') as review,
          count(*) filter (where status = 'PUBLISHED') as published,
          count(*) as total
        from projects where user_id = %s and workspace_id = %s
        """,
        (user_id, workspace_id),
    ) or {}
    research_count = fetch_one(
        "select count(*) as count from research_runs where user_id = %s and workspace_id = %s",
        (user_id, workspace_id),
    ) or {"count": 0}
    blocked = fetch_one(
        """
        select count(*) as count from projects
        where user_id = %s and workspace_id = %s
          and coalesce((quality_report->>'pass')::boolean, true) = false
        """,
        (user_id, workspace_id),
    ) or {"count": 0}
    total = int(counts.get("total") or 0)
    if total == 0:
        next_action = "Run a sourced research scan and save one evidence-backed idea."
    elif int(counts.get("queue") or 0) > 0:
        next_action = "Open the oldest queued project and generate or revise its script."
    elif int(counts.get("review") or 0) > 0:
        next_action = "Complete human review before moving any project to production."
    else:
        next_action = "Review current projects and select the next concrete production action."
    return {
        "project_counts": _jsonable(counts),
        "research_runs": int(research_count["count"]),
        "quality_blocks": int(blocked["count"]),
        "next_action": next_action,
    }


@app.post("/ai/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
    content = await chat_text(request.prompt, request.system, request.temperature)
    return GenerateResponse(model=OLLAMA_MODEL, content=content)


@app.post("/research", response_model=ResearchResult)
async def research(request: ResearchRequest) -> ResearchResult:
    language_code = "en" if request.language.lower().startswith("en") else "all"
    queries = [
        f"{request.topic} {request.platform} {request.region}",
        f"{request.topic} questions challenges {request.audience}",
    ]
    gathered: list[dict[str, Any]] = []
    seen: set[str] = set()
    try:
        for query_text in queries:
            for item in await web_search(query_text, language=language_code, limit=8):
                if item["url"] not in seen:
                    gathered.append(item)
                    seen.add(item["url"])
                if len(gathered) >= 12:
                    break
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Self-hosted search service is unavailable") from exc
    if not gathered:
        raise HTTPException(status_code=422, detail="Search returned no usable sources")

    sources = [
        SourceItem(id=f"source-{index + 1}", **item)
        for index, item in enumerate(gathered)
    ]
    evidence = [source.model_dump(mode="json") for source in sources]
    prompt = f"""
Topic: {request.topic}
Audience: {request.audience}
Platform: {request.platform}
Region: {request.region}
Language: {request.language}
Creator notes: {request.notes}
Research date: {date.today().isoformat()}

SOURCE PACKET:
{json.dumps(evidence, ensure_ascii=False, indent=2)}

Return ONLY JSON matching this shape:
{{
  "query_summary": "...",
  "landscape_summary": "...",
  "verified_observations": [{{"observation":"...","source_ids":["source-1"]}}],
  "content_gaps": [{{"gap":"...","evidence":"...","source_ids":["source-1"],"confidence":"high|medium|low"}}],
  "ideas": [
    {{"topic":"...","angle":"...","hook":"...","rationale":"...","audience":"...","format":"long_video|short_video","estimated_duration":"...","supporting_source_ids":["source-1"],"evidence_level":"verified|inference|creative_hypothesis"}}
  ]
}}

Rules:
- Return exactly five ideas.
- Use only the source packet for factual observations.
- Never invent view counts, revenue, RPM, search volume, engagement, or trend claims.
- A source ID may be cited only when its title/snippet supports the claim.
- Label unsupported creative angles as creative_hypothesis.
- Distinguish observations from inferences.
"""
    analysis = await chat_json(
        prompt,
        "You are an evidence-first content researcher. Never manufacture citations or metrics.",
        ResearchAnalysis,
        temperature=0.15,
    )
    if len(analysis.ideas) != 5:
        raise HTTPException(status_code=502, detail="Research model did not return exactly five ideas")
    valid_ids = {source.id for source in sources}
    for observation in analysis.verified_observations:
        observation["source_ids"] = [sid for sid in observation.get("source_ids", []) if sid in valid_ids]
    for gap in analysis.content_gaps:
        gap["source_ids"] = [sid for sid in gap.get("source_ids", []) if sid in valid_ids]
    for idea in analysis.ideas:
        idea.supporting_source_ids = [sid for sid in idea.supporting_source_ids if sid in valid_ids]

    user_id, workspace_id = identity()
    raw_result = {
        **analysis.model_dump(mode="json"),
        "sources": evidence,
    }
    saved = execute_returning(
        """
        insert into research_runs (
          user_id, workspace_id, query, research_date, landscape_summary,
          verified_observations, content_gaps, sources, raw_result
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning id
        """,
        (
            user_id,
            workspace_id,
            request.topic,
            date.today(),
            analysis.landscape_summary,
            Jsonb(analysis.verified_observations),
            Jsonb(analysis.content_gaps),
            Jsonb(evidence),
            Jsonb(raw_result),
        ),
    )
    return ResearchResult(
        id=str(saved["id"]) if saved else None,
        research_date=date.today().isoformat(),
        query_summary=analysis.query_summary,
        landscape_summary=analysis.landscape_summary,
        verified_observations=analysis.verified_observations,
        content_gaps=analysis.content_gaps,
        sources=sources,
        ideas=analysis.ideas,
    )


@app.get("/research")
def list_research(limit: int = Query(default=20, ge=1, le=100)) -> list[dict[str, Any]]:
    user_id, workspace_id = identity()
    rows = fetch_all(
        """
        select id, query, research_date, landscape_summary, sources, raw_result, created_at
        from research_runs where user_id = %s and workspace_id = %s
        order by created_at desc limit %s
        """,
        (user_id, workspace_id, limit),
    )
    return _jsonable(rows)


@app.post("/content/script", response_model=ScriptPackage)
async def create_script(request: ScriptRequest) -> ScriptPackage:
    prompt = f"""
Create an original {request.target_minutes}-minute content package.
Topic: {request.topic}
Angle: {request.angle}
Audience: {request.audience}
Tone: {request.tone}
Creator's real expertise/notes: {request.creator_notes}
Research context: {json.dumps(request.research_context, ensure_ascii=False)}

Return ONLY JSON:
{{"title":"...","hook":"...","narration":"...","description":"...","hashtags":["..."],"platform_targets":["YouTube","TikTok","Instagram Reels","YouTube Shorts"]}}

Rules: build around the creator notes, do not invent facts, flag uncertainty inside the narration, avoid copied phrasing and generic filler, and include a clear viewer payoff.
"""
    return await chat_json(
        prompt,
        "You are an original documentary and educational script writer.",
        ScriptPackage,
        temperature=0.45,
        timeout=420,
    )


@app.post("/content/scenes", response_model=list[Scene])
async def create_scenes(request: SceneRequest) -> list[Scene]:
    prompt = f"""
Title: {request.title}
Hook: {request.hook}
Narration: {request.narration}
Create exactly {request.scene_count} scenes and return ONLY JSON:
{{"scenes":[{{"scene_number":1,"duration_seconds":30,"purpose":"...","visual_direction":"...","onscreen_text":"...","voice_segment":"...","asset_notes":"..."}}]}}
Do not request copyrighted watermarked footage. Prefer original screen recordings, diagrams, licensed assets, maps, and creator-provided material.
"""
    package = await chat_json(
        prompt,
        "You are a practical video director creating producible scene plans.",
        ScenePackage,
        temperature=0.35,
    )
    if len(package.scenes) != request.scene_count:
        raise HTTPException(status_code=502, detail="Scene model returned the wrong number of scenes")
    return package.scenes


@app.post("/quality-check", response_model=QualityReport, response_model_by_alias=True)
async def quality_check(request: QualityRequest) -> QualityReport:
    user_id, workspace_id = identity()
    previous = fetch_all(
        """
        select id, title, topic, hook, left(narration, 1500) as narration_excerpt
        from projects where user_id = %s and workspace_id = %s
          and (%s is null or id::text <> %s)
        order by created_at desc limit 20
        """,
        (user_id, workspace_id, request.project_id, request.project_id),
    )
    prompt = f"""
Review this content for originality risk and production quality.
Title: {request.title}
Hook: {request.hook}
Narration: {request.narration}
Scenes: {json.dumps(request.scenes, ensure_ascii=False)}
Research context: {json.dumps(request.research_context, ensure_ascii=False)}
Previous project summaries: {json.dumps(_jsonable(previous), ensure_ascii=False)}

Return ONLY JSON:
{{"pass":true,"score":0,"blocking_issues":[],"warnings":[],"originality_notes":"...","human_review_checklist":["..."]}}

Check: unique thesis, meaningful creator contribution, unsupported factual claims, source alignment, repetitive AI-template language, similarity to prior projects, watermarked/unlicensed asset requests, realistic AI disclosure, and viewer payoff.
This is not plagiarism detection. Call it an originality-risk and quality review.
"""
    report = await chat_json(
        prompt,
        "You are a conservative editorial quality reviewer. Do not claim guaranteed plagiarism detection.",
        QualityReport,
        temperature=0.1,
    )
    deterministic_blocks: list[str] = []
    deterministic_warnings: list[str] = []
    if len(request.narration.split()) < 180:
        deterministic_blocks.append("Narration is too short for a substantive long-form episode.")
    if not request.hook.strip():
        deterministic_blocks.append("A clear opening hook is missing.")
    if not request.scenes:
        deterministic_warnings.append("No scene plan was supplied for production review.")
    if deterministic_blocks:
        report.passed = False
        report.score = min(report.score, 55)
        report.blocking_issues = list(dict.fromkeys(report.blocking_issues + deterministic_blocks))
    report.warnings = list(dict.fromkeys(report.warnings + deterministic_warnings))
    return report


@app.get("/projects")
def list_projects(status: ProjectStatus | None = None) -> list[dict[str, Any]]:
    user_id, workspace_id = identity()
    if status:
        rows = fetch_all(
            "select * from projects where user_id = %s and workspace_id = %s and status = %s order by created_at desc",
            (user_id, workspace_id, status),
        )
    else:
        rows = fetch_all(
            "select * from projects where user_id = %s and workspace_id = %s order by created_at desc",
            (user_id, workspace_id),
        )
    return _jsonable(rows)


@app.post("/projects", status_code=201)
def create_project(request: ProjectCreate) -> dict[str, Any]:
    user_id, workspace_id = identity()
    if request.status in {"REVIEW", "PUBLISHED"} and request.quality_report.get("pass") is not True:
        raise HTTPException(status_code=422, detail="A passing quality report is required for REVIEW or PUBLISHED")
    row = execute_returning(
        """
        insert into projects (
          user_id, workspace_id, title, topic, hook, narration, description,
          hashtags, scenes, quality_report, status, platform_targets
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning *
        """,
        (
            user_id,
            workspace_id,
            request.title,
            request.topic,
            request.hook,
            request.narration,
            request.description,
            request.hashtags,
            Jsonb(request.scenes),
            Jsonb(request.quality_report),
            request.status,
            request.platform_targets,
        ),
    )
    assert row is not None
    return _jsonable(row)


@app.patch("/projects/{project_id}")
def update_project(project_id: str, request: ProjectUpdate) -> dict[str, Any]:
    user_id, _ = identity()
    current = _require_project(project_id, user_id)
    changes = request.model_dump(exclude_unset=True)
    if not changes:
        return _jsonable(current)
    proposed_quality = changes.get("quality_report", current.get("quality_report") or {})
    proposed_status = changes.get("status", current["status"])
    if proposed_status in {"REVIEW", "PUBLISHED"} and proposed_quality.get("pass") is not True:
        raise HTTPException(status_code=422, detail="A passing quality report is required for REVIEW or PUBLISHED")
    assignments: list[str] = []
    values: list[Any] = []
    json_fields = {"scenes", "quality_report"}
    for field, value in changes.items():
        assignments.append(f"{field} = %s")
        values.append(Jsonb(value) if field in json_fields else value)
    if proposed_status == "PUBLISHED" and current.get("published_at") is None:
        assignments.append("published_at = now()")
    values.extend([project_id, user_id])
    row = execute_returning(
        f"update projects set {', '.join(assignments)} where id = %s and user_id = %s returning *",
        tuple(values),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return _jsonable(row)


@app.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: str) -> None:
    user_id, _ = identity()
    deleted = execute("delete from projects where id = %s and user_id = %s", (project_id, user_id))
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Project not found")


@app.post("/mirofish/seed")
def build_mirofish_seed(request: MiroFishSeedRequest) -> dict[str, Any]:
    return {
        "version": "1.0",
        "project_id": request.project_id,
        "research_context": request.research_context,
        "audience": request.audience,
        "content_variants": request.content_variants,
        "simulation_question": request.simulation_question,
        "requested_outputs": [
            "audience_segment_reactions",
            "hook_comparison",
            "objections",
            "confusing_sections",
            "trust_risks",
            "predicted_comments",
            "recommended_changes",
        ],
        "disclaimer": "Synthetic audience simulation only; not real audience measurement or guaranteed performance.",
    }


@app.post("/simulations/report")
async def analyse_simulation_report(request: SimulationReportRequest) -> dict[str, Any]:
    user_id, _ = identity()
    _require_project(request.project_id, user_id)
    prompt = f"""
Simulation question: {request.scenario_question}
Seed: {json.dumps(request.seed_payload, ensure_ascii=False)}
Raw MiroFish report:
{request.raw_report}

Return ONLY JSON:
{{"audience_segments":[],"hook_comparison":[],"objections":[],"predicted_comments":[],"risks":[],"recommended_changes":[],"confidence_notes":"..."}}
Treat all findings as synthetic-agent reactions, not real users, measured demand, or guaranteed outcomes.
"""
    findings = await chat_json(
        prompt,
        "You structure synthetic simulation reports conservatively and preserve uncertainty.",
        SimulationFindings,
        temperature=0.15,
    )
    run = execute_returning(
        """
        insert into simulation_runs (
          user_id, project_id, status, scenario_question, seed_payload,
          raw_report, structured_result, started_at, completed_at
        ) values (%s, %s, 'COMPLETED', %s, %s, %s, %s, now(), now())
        returning id
        """,
        (
            user_id,
            request.project_id,
            request.scenario_question,
            Jsonb(request.seed_payload),
            request.raw_report,
            Jsonb(findings.model_dump(mode="json")),
        ),
    )
    assert run is not None
    execute_returning(
        """
        insert into simulation_findings (
          user_id, simulation_run_id, audience_segments, hook_comparison,
          objections, predicted_comments, risks, recommended_changes, confidence_notes
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning id
        """,
        (
            user_id,
            run["id"],
            Jsonb(findings.audience_segments),
            Jsonb(findings.hook_comparison),
            Jsonb(findings.objections),
            Jsonb(findings.predicted_comments),
            Jsonb(findings.risks),
            Jsonb(findings.recommended_changes),
            findings.confidence_notes,
        ),
    )
    return {
        "simulation_run_id": str(run["id"]),
        "disclaimer": "AI-generated synthetic audience simulation; not real user research or guaranteed performance.",
        **findings.model_dump(mode="json"),
    }


@app.get("/performance")
def list_performance() -> list[dict[str, Any]]:
    user_id, _ = identity()
    rows = fetch_all(
        """
        select pe.*, p.title as project_title
        from performance_entries pe join projects p on p.id = pe.project_id
        where pe.user_id = %s order by pe.recorded_on desc, pe.created_at desc
        """,
        (user_id,),
    )
    return _jsonable(rows)


@app.post("/performance", status_code=201)
def create_performance(request: PerformanceCreate) -> dict[str, Any]:
    user_id, _ = identity()
    _require_project(request.project_id, user_id)
    row = execute_returning(
        """
        insert into performance_entries (
          user_id, project_id, platform, recorded_on, views, likes, comments,
          shares, watch_time_minutes, revenue, currency, notes
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (project_id, platform, recorded_on) do update set
          views = excluded.views,
          likes = excluded.likes,
          comments = excluded.comments,
          shares = excluded.shares,
          watch_time_minutes = excluded.watch_time_minutes,
          revenue = excluded.revenue,
          currency = excluded.currency,
          notes = excluded.notes
        returning *
        """,
        (
            user_id,
            request.project_id,
            request.platform,
            request.recorded_on,
            request.views,
            request.likes,
            request.comments,
            request.shares,
            request.watch_time_minutes,
            request.revenue,
            request.currency.upper(),
            request.notes,
        ),
    )
    assert row is not None
    return _jsonable(row)

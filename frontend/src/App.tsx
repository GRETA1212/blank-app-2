import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Clapperboard,
  Copy,
  Database,
  Download,
  ExternalLink,
  FlaskConical,
  LayoutDashboard,
  Loader2,
  Network,
  Plus,
  Save,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Trash2,
  TriangleAlert,
  Workflow,
} from 'lucide-react';
import { Background, Controls, type Edge, type Node, ReactFlow } from '@xyflow/react';
import { api } from './api';
import type {
  Health,
  PerformanceEntry,
  Project,
  ProjectStatus,
  QualityReport,
  ResearchIdea,
  ResearchResult,
  Scene,
  ScriptPackage,
} from './types';

type Tab = 'overview' | 'research' | 'create' | 'pipeline' | 'simulation' | 'performance' | 'settings';

const navigation: Array<{ id: Tab; label: string; icon: LucideIcon }> = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'research', label: 'Research', icon: Search },
  { id: 'create', label: 'Create', icon: Clapperboard },
  { id: 'pipeline', label: 'Pipeline', icon: Workflow },
  { id: 'simulation', label: 'Audience Simulation', icon: FlaskConical },
  { id: 'performance', label: 'Performance', icon: BarChart3 },
  { id: 'settings', label: 'Settings', icon: Settings },
];

const stages: ProjectStatus[] = ['QUEUE', 'SCRIPTED', 'IN_PRODUCTION', 'RENDERING', 'REVIEW', 'PUBLISHED'];
const stageLabels: Record<ProjectStatus, string> = {
  QUEUE: 'Queue',
  SCRIPTED: 'Scripted',
  IN_PRODUCTION: 'In production',
  RENDERING: 'Rendering',
  REVIEW: 'Review',
  PUBLISHED: 'Published',
};

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unexpected error';
}

function StatusPill({ active, label }: { active: boolean; label: string }) {
  return (
    <span className={`status-pill ${active ? 'status-live' : 'status-offline'}`}>
      <span className="status-dot" />
      {label}
    </span>
  );
}

function Badge({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: 'neutral' | 'good' | 'warn' | 'danger' }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function PanelTitle({ eyebrow, title, copy }: { eyebrow: string; title: string; copy: string }) {
  return (
    <header className="panel-title">
      <span className="eyebrow">{eyebrow}</span>
      <h2>{title}</h2>
      <p>{copy}</p>
    </header>
  );
}

function LoadingBlock({ label }: { label: string }) {
  return <div className="loading-block"><Loader2 className="spin" size={20} /><span>{label}</span></div>;
}

function EmptyState({ icon: Icon, title, copy }: { icon: LucideIcon; title: string; copy: string }) {
  return <div className="empty-state"><Icon size={34} /><strong>{title}</strong><p>{copy}</p></div>;
}

function OverviewPanel({ health }: { health?: Health }) {
  const overview = useQuery({ queryKey: ['overview'], queryFn: api.overview });
  const nodes = useMemo<Node[]>(() => [
    { id: 'research', position: { x: 0, y: 80 }, data: { label: 'Research' }, className: 'flow-node' },
    { id: 'create', position: { x: 210, y: 80 }, data: { label: 'Create' }, className: 'flow-node' },
    { id: 'simulate', position: { x: 420, y: 0 }, data: { label: 'Simulate' }, className: 'flow-node' },
    { id: 'quality', position: { x: 420, y: 155 }, data: { label: 'Quality Gate' }, className: 'flow-node' },
    { id: 'produce', position: { x: 650, y: 80 }, data: { label: 'Produce Draft' }, className: 'flow-node' },
  ], []);
  const edges = useMemo<Edge[]>(() => [
    { id: 'e1', source: 'research', target: 'create', animated: true },
    { id: 'e2', source: 'create', target: 'simulate', animated: true },
    { id: 'e3', source: 'simulate', target: 'quality', animated: true },
    { id: 'e4', source: 'quality', target: 'produce', animated: true },
  ], []);

  if (overview.isLoading) return <LoadingBlock label="Loading studio state" />;
  const counts = overview.data?.project_counts ?? {};
  return (
    <section>
      <PanelTitle eyebrow="Orchestrator" title="Your local content studio" copy="A database-backed workflow with sourced research, local AI, human review, and no automatic publishing." />
      {overview.isError && <p className="error-box">{errorMessage(overview.error)}</p>}
      <div className="metric-grid">
        <article className="metric-card"><span>Projects</span><strong>{counts.total ?? 0}</strong><small>Saved in PostgreSQL</small></article>
        <article className="metric-card"><span>Research runs</span><strong>{overview.data?.research_runs ?? 0}</strong><small>Sourced scans stored</small></article>
        <article className="metric-card"><span>Quality blocks</span><strong>{overview.data?.quality_blocks ?? 0}</strong><small>Require revision</small></article>
        <article className="metric-card"><span>Published</span><strong>{counts.published ?? 0}</strong><small>Human-confirmed status</small></article>
      </div>
      <div className="content-grid">
        <article className="surface flow-surface">
          <div className="surface-heading"><Network size={18} /><span>Studio workflow</span></div>
          <div className="flow-canvas">
            <ReactFlow nodes={nodes} edges={edges} fitView nodesDraggable={false} nodesConnectable={false} elementsSelectable={false}>
              <Background gap={20} size={1} />
              <Controls showInteractive={false} />
            </ReactFlow>
          </div>
        </article>
        <article className="surface action-list">
          <div className="surface-heading"><Activity size={18} /><span>Next best action</span></div>
          <h3>Database-driven recommendation</h3>
          <p>{overview.data?.next_action ?? 'Start the local services to calculate the next action.'}</p>
          <div className="integration-stack">
            <StatusPill active={Boolean(health?.database)} label="Database" />
            <StatusPill active={Boolean(health?.ollama)} label={`Ollama · ${health?.model ?? 'local model'}`} />
            <StatusPill active={Boolean(health?.search)} label="SearXNG" />
            <StatusPill active={Boolean(health?.mirofish)} label={health?.mirofish ? 'MiroFish reachable' : 'MiroFish manual'} />
          </div>
        </article>
      </div>
    </section>
  );
}

function ResearchPanel({ onUseIdea }: { onUseIdea: (idea: ResearchIdea, result: ResearchResult) => void }) {
  const [topic, setTopic] = useState('');
  const [audience, setAudience] = useState('');
  const [platform, setPlatform] = useState('YouTube');
  const [region, setRegion] = useState('Europe');
  const [language, setLanguage] = useState('English');
  const [notes, setNotes] = useState('');
  const mutation = useMutation({ mutationFn: api.research });

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate({ topic, audience, platform, region, language, notes });
  }

  return (
    <section>
      <PanelTitle eyebrow="Research agent" title="Research with current public sources" copy="SearXNG retrieves sources; Ollama must distinguish evidence, inference, and creative hypotheses. No invented metrics are permitted." />
      <div className="two-column research-layout">
        <form className="surface form-stack" onSubmit={submit}>
          <label>Topic<input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="AI automation for land surveyors" required /></label>
          <label>Target audience<input value={audience} onChange={(event) => setAudience(event.target.value)} placeholder="Survey-company owners" required /></label>
          <div className="form-row">
            <label>Platform<select value={platform} onChange={(event) => setPlatform(event.target.value)}><option>YouTube</option><option>TikTok</option><option>Instagram Reels</option><option>LinkedIn</option></select></label>
            <label>Region<input value={region} onChange={(event) => setRegion(event.target.value)} /></label>
          </div>
          <label>Language<input value={language} onChange={(event) => setLanguage(event.target.value)} /></label>
          <label>Creator notes<textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={5} placeholder="Your expertise, constraints, or questions." /></label>
          <button className="primary-button" disabled={mutation.isPending}>{mutation.isPending ? <Loader2 className="spin" size={17} /> : <Search size={17} />}{mutation.isPending ? 'Searching and analysing' : 'Run sourced research'}</button>
          {mutation.isError && <p className="error-box">{errorMessage(mutation.error)}</p>}
        </form>
        <div className="result-stack">
          {!mutation.data && !mutation.isPending && <article className="surface"><EmptyState icon={Search} title="No research run yet" copy="Enter a focused topic and audience to retrieve current public sources." /></article>}
          {mutation.isPending && <article className="surface"><LoadingBlock label="Searching sources and validating five ideas" /></article>}
          {mutation.data && (
            <>
              <article className="surface">
                <div className="surface-heading"><Sparkles size={18} /><span>Landscape summary · {mutation.data.research_date}</span></div>
                <p className="long-copy">{mutation.data.landscape_summary}</p>
                <div className="finding-grid">
                  <div><h4>Verified observations</h4>{mutation.data.verified_observations.map((item, index) => <div className="finding" key={index}><p>{item.observation}</p><small>{item.source_ids.join(', ') || 'No source mapped'}</small></div>)}</div>
                  <div><h4>Content gaps</h4>{mutation.data.content_gaps.map((item, index) => <div className="finding" key={index}><Badge tone={item.confidence === 'high' ? 'good' : 'warn'}>{item.confidence}</Badge><p>{item.gap}</p><small>{item.evidence}</small></div>)}</div>
                </div>
              </article>
              <article className="surface">
                <div className="surface-heading"><Clapperboard size={18} /><span>Five content opportunities</span></div>
                <div className="idea-list">
                  {mutation.data.ideas.map((idea, index) => (
                    <div className="idea-card" key={`${idea.topic}-${index}`}>
                      <div className="card-top"><Badge tone={idea.evidence_level === 'verified' ? 'good' : idea.evidence_level === 'inference' ? 'warn' : 'neutral'}>{idea.evidence_level.replace('_', ' ')}</Badge><span>{idea.estimated_duration}</span></div>
                      <h3>{idea.topic}</h3><p className="hook">“{idea.hook}”</p><p>{idea.angle}</p><small>{idea.rationale}</small>
                      <button className="secondary-button" onClick={() => onUseIdea(idea, mutation.data!)}><Plus size={16} />Send to Create</button>
                    </div>
                  ))}
                </div>
              </article>
              <article className="surface">
                <div className="surface-heading"><ExternalLink size={18} /><span>Sources</span></div>
                <div className="source-list">
                  {mutation.data.sources.map((source) => (
                    <a className="source-card" href={source.url} target="_blank" rel="noreferrer" key={source.id}>
                      <span>{source.id}</span><strong>{source.title}</strong><small>{source.publisher}{source.published_date ? ` · ${source.published_date}` : ''}</small><p>{source.snippet}</p>
                    </a>
                  ))}
                </div>
              </article>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

function CreatePanel({ seed, researchContext, onSaved }: { seed: ResearchIdea | null; researchContext: ResearchResult | null; onSaved: () => void }) {
  const queryClient = useQueryClient();
  const [topic, setTopic] = useState('');
  const [angle, setAngle] = useState('');
  const [audience, setAudience] = useState('');
  const [notes, setNotes] = useState('');
  const [minutes, setMinutes] = useState(7);
  const [script, setScript] = useState<ScriptPackage | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [quality, setQuality] = useState<QualityReport | null>(null);

  useEffect(() => {
    if (!seed) return;
    setTopic(seed.topic);
    setAngle(seed.angle);
    setAudience(seed.audience);
    setScript(null);
    setScenes([]);
    setQuality(null);
  }, [seed]);

  const scriptMutation = useMutation({
    mutationFn: () => api.generateScript({ topic, angle, audience, target_minutes: minutes, tone: 'clear, useful and credible', creator_notes: notes, research_context: researchContext ?? {} }),
    onSuccess: (data) => { setScript(data); setScenes([]); setQuality(null); },
  });
  const scenesMutation = useMutation({
    mutationFn: () => api.generateScenes({ title: script!.title, hook: script!.hook, narration: script!.narration, scene_count: 8 }),
    onSuccess: (data) => { setScenes(data); setQuality(null); },
  });
  const qualityMutation = useMutation({
    mutationFn: () => api.qualityCheck({ title: script!.title, hook: script!.hook, narration: script!.narration, scenes, research_context: researchContext ?? {} }),
    onSuccess: setQuality,
  });
  const saveMutation = useMutation({
    mutationFn: () => api.createProject({
      title: script!.title,
      topic,
      hook: script!.hook,
      narration: script!.narration,
      description: script!.description,
      hashtags: script!.hashtags,
      scenes,
      quality_report: quality ?? {},
      status: quality?.pass ? 'SCRIPTED' : 'QUEUE',
      platform_targets: script!.platform_targets,
    }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['projects'] }),
        queryClient.invalidateQueries({ queryKey: ['overview'] }),
      ]);
      onSaved();
    },
  });

  return (
    <section>
      <PanelTitle eyebrow="Creation agent" title="Create, inspect, and approve an episode" copy="The AI prepares editable material. A project cannot reach Review or Published without a passing quality report." />
      <div className="two-column create-layout">
        <div className="surface form-stack">
          <label>Topic<input value={topic} onChange={(event) => setTopic(event.target.value)} /></label>
          <label>Angle<textarea value={angle} onChange={(event) => setAngle(event.target.value)} rows={3} /></label>
          <label>Audience<input value={audience} onChange={(event) => setAudience(event.target.value)} /></label>
          <label>Target minutes<input type="number" min={1} max={30} value={minutes} onChange={(event) => setMinutes(Number(event.target.value))} /></label>
          <label>Your expertise and facts<textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={8} placeholder="Add real examples, measurements, limits, opinions and claims that must be verified." /></label>
          <button className="primary-button" disabled={!topic.trim() || scriptMutation.isPending} onClick={() => scriptMutation.mutate()}>{scriptMutation.isPending ? <Loader2 className="spin" size={17} /> : <Sparkles size={17} />}Generate script package</button>
          {scriptMutation.isError && <p className="error-box">{errorMessage(scriptMutation.error)}</p>}
        </div>
        <div className="result-stack">
          {!script && <article className="surface"><EmptyState icon={Clapperboard} title="No script yet" copy="Start from a researched idea or enter your own topic and expertise." /></article>}
          {script && (
            <article className="surface form-stack">
              <div className="surface-heading"><Clapperboard size={18} /><span>Editable script package</span></div>
              <label>Title<input value={script.title} onChange={(event) => setScript({ ...script, title: event.target.value })} /></label>
              <label>Hook<textarea value={script.hook} onChange={(event) => setScript({ ...script, hook: event.target.value })} rows={3} /></label>
              <label>Narration<textarea value={script.narration} onChange={(event) => setScript({ ...script, narration: event.target.value })} rows={18} /></label>
              <label>Description<textarea value={script.description} onChange={(event) => setScript({ ...script, description: event.target.value })} rows={5} /></label>
              <div className="tag-row">{script.hashtags.map((tag) => <Badge key={tag}>{tag}</Badge>)}</div>
              <button className="secondary-button" disabled={scenesMutation.isPending} onClick={() => scenesMutation.mutate()}>{scenesMutation.isPending ? <Loader2 className="spin" size={16} /> : <Clapperboard size={16} />}{scenes.length ? 'Regenerate scenes' : 'Generate scene plan'}</button>
              {scenesMutation.isError && <p className="error-box">{errorMessage(scenesMutation.error)}</p>}
            </article>
          )}
          {scenes.length > 0 && (
            <article className="surface">
              <div className="surface-heading"><Network size={18} /><span>Scene plan</span></div>
              <div className="scene-list">{scenes.map((scene) => <div className="scene-card" key={scene.scene_number}><span>{scene.scene_number}</span><div><strong>{scene.purpose}</strong><p>{scene.visual_direction}</p><small>{scene.duration_seconds}s · {scene.asset_notes}</small></div></div>)}</div>
              <button className="primary-button" disabled={qualityMutation.isPending} onClick={() => qualityMutation.mutate()}>{qualityMutation.isPending ? <Loader2 className="spin" size={17} /> : <ShieldCheck size={17} />}Run originality-risk and quality review</button>
              {qualityMutation.isError && <p className="error-box">{errorMessage(qualityMutation.error)}</p>}
            </article>
          )}
          {quality && (
            <article className={`surface quality-card ${quality.pass ? 'quality-pass' : 'quality-fail'}`}>
              <div className="quality-score"><div>{quality.pass ? <CheckCircle2 size={26} /> : <TriangleAlert size={26} />}</div><div><span>Quality score</span><strong>{quality.score}/100</strong></div><Badge tone={quality.pass ? 'good' : 'danger'}>{quality.pass ? 'Pass' : 'Blocked'}</Badge></div>
              <p>{quality.originality_notes}</p>
              {quality.blocking_issues.length > 0 && <div><h4>Blocking issues</h4><ul>{quality.blocking_issues.map((item) => <li key={item}>{item}</li>)}</ul></div>}
              {quality.warnings.length > 0 && <div><h4>Warnings</h4><ul>{quality.warnings.map((item) => <li key={item}>{item}</li>)}</ul></div>}
              <div><h4>Human review checklist</h4><ul>{quality.human_review_checklist.map((item) => <li key={item}>{item}</li>)}</ul></div>
              <button className="primary-button" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate()}>{saveMutation.isPending ? <Loader2 className="spin" size={17} /> : <Save size={17} />}Save to {quality.pass ? 'Scripted' : 'Queue'}</button>
              {saveMutation.isError && <p className="error-box">{errorMessage(saveMutation.error)}</p>}
            </article>
          )}
        </div>
      </div>
    </section>
  );
}

function PipelinePanel() {
  const queryClient = useQueryClient();
  const projects = useQuery({ queryKey: ['projects'], queryFn: api.projects });
  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: ProjectStatus }) => api.updateProject(id, { status }),
    onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ['projects'] }), queryClient.invalidateQueries({ queryKey: ['overview'] })]); },
  });
  const deleteMutation = useMutation({
    mutationFn: api.deleteProject,
    onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ['projects'] }), queryClient.invalidateQueries({ queryKey: ['overview'] })]); },
  });

  function move(project: Project, direction: -1 | 1) {
    const index = stages.indexOf(project.status);
    const target = stages[index + direction];
    if (target) updateMutation.mutate({ id: project.id, status: target });
  }

  return (
    <section>
      <PanelTitle eyebrow="Execution tracker" title="Production pipeline" copy="Move projects manually. Review and Published remain blocked until the quality gate passes." />
      {projects.isLoading && <LoadingBlock label="Loading projects" />}
      {projects.isError && <p className="error-box">{errorMessage(projects.error)}</p>}
      <div className="kanban">
        {stages.map((stage) => {
          const items = (projects.data ?? []).filter((project) => project.status === stage);
          return (
            <article className="kanban-column" key={stage}>
              <header><span>{stageLabels[stage]}</span><strong>{items.length}</strong></header>
              <div className="kanban-items">
                {items.length === 0 && <div className="empty-card">No projects</div>}
                {items.map((project) => {
                  const passed = project.quality_report?.pass === true;
                  const forwardTarget = stages[stages.indexOf(stage) + 1];
                  const forwardBlocked = Boolean(forwardTarget && ['REVIEW', 'PUBLISHED'].includes(forwardTarget) && !passed);
                  return (
                    <div className="project-card" key={project.id}>
                      <div className="card-top"><Badge tone={passed ? 'good' : 'warn'}>{passed ? 'QC pass' : 'QC pending'}</Badge><button className="icon-button danger" aria-label="Delete project" onClick={() => window.confirm('Delete this project?') && deleteMutation.mutate(project.id)}><Trash2 size={14} /></button></div>
                      <h3>{project.title}</h3><p>{project.topic}</p>
                      <div className="tag-row">{project.platform_targets.slice(0, 2).map((platform) => <Badge key={platform}>{platform}</Badge>)}</div>
                      <small>{project.scenes.length} scenes · {new Date(project.created_at).toLocaleDateString()}</small>
                      <div className="move-row">
                        <button className="icon-button" disabled={stage === 'QUEUE'} onClick={() => move(project, -1)}><ArrowLeft size={15} /></button>
                        <button className="secondary-button compact" disabled={stage === 'PUBLISHED' || forwardBlocked || updateMutation.isPending} title={forwardBlocked ? 'Run and pass quality review first' : ''} onClick={() => move(project, 1)}>Move <ArrowRight size={14} /></button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </article>
          );
        })}
      </div>
      {updateMutation.isError && <p className="error-box">{errorMessage(updateMutation.error)}</p>}
    </section>
  );
}

function SimulationPanel() {
  const projects = useQuery({ queryKey: ['projects'], queryFn: api.projects });
  const [projectId, setProjectId] = useState('');
  const [audience, setAudience] = useState('Professionals interested in the topic');
  const [countries, setCountries] = useState('Italy, Germany, United Kingdom');
  const [question, setQuestion] = useState('Which parts create trust, confusion, or scepticism?');
  const [seed, setSeed] = useState<Record<string, unknown> | null>(null);
  const [rawReport, setRawReport] = useState('');
  const selected = projects.data?.find((project) => project.id === projectId);
  const seedMutation = useMutation({
    mutationFn: () => api.mirofishSeed({
      project_id: selected!.id,
      topic: selected!.topic,
      audience: { description: audience, countries: countries.split(',').map((item) => item.trim()).filter(Boolean), language: 'English', platform: selected!.platform_targets[0] ?? 'YouTube' },
      content_variants: [{ id: 'A', title: selected!.title, hook: selected!.hook, script_summary: selected!.narration.slice(0, 1500) }],
      simulation_question: question,
      research_context: {},
    }),
    onSuccess: setSeed,
  });
  const analyseMutation = useMutation({
    mutationFn: () => api.analyseSimulation({ project_id: selected!.id, scenario_question: question, seed_payload: seed!, raw_report: rawReport }),
  });

  function downloadSeed() {
    if (!seed) return;
    const blob = new Blob([JSON.stringify(seed, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = `mirofish-seed-${projectId}.json`; anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section>
      <PanelTitle eyebrow="MiroFish manual bridge" title="Simulate synthetic audience reactions" copy="Generate a seed, run it manually in MiroFish, then import the report. Findings are not real user research or guaranteed performance." />
      <div className="two-column">
        <div className="surface form-stack">
          <label>Saved project<select value={projectId} onChange={(event) => { setProjectId(event.target.value); setSeed(null); }}><option value="">Choose a project</option>{projects.data?.map((project) => <option value={project.id} key={project.id}>{project.title}</option>)}</select></label>
          <label>Synthetic audience<textarea value={audience} onChange={(event) => setAudience(event.target.value)} rows={3} /></label>
          <label>Countries<input value={countries} onChange={(event) => setCountries(event.target.value)} /></label>
          <label>Simulation question<textarea value={question} onChange={(event) => setQuestion(event.target.value)} rows={4} /></label>
          <button className="primary-button" disabled={!selected || seedMutation.isPending} onClick={() => seedMutation.mutate()}>{seedMutation.isPending ? <Loader2 className="spin" size={17} /> : <FlaskConical size={17} />}Generate seed</button>
          {seedMutation.isError && <p className="error-box">{errorMessage(seedMutation.error)}</p>}
          {seed && <div className="button-row"><button className="secondary-button" onClick={() => navigator.clipboard.writeText(JSON.stringify(seed, null, 2))}><Copy size={15} />Copy JSON</button><button className="secondary-button" onClick={downloadSeed}><Download size={15} />Download</button></div>}
        </div>
        <div className="result-stack">
          <article className="surface result-panel">
            <div className="surface-heading"><FlaskConical size={18} /><span>Seed JSON</span></div>
            {seed ? <pre>{JSON.stringify(seed, null, 2)}</pre> : <EmptyState icon={FlaskConical} title="No seed generated" copy="Choose a saved project and define the simulation audience." />}
          </article>
          {seed && <article className="surface form-stack"><label>Paste completed MiroFish report<textarea rows={14} value={rawReport} onChange={(event) => setRawReport(event.target.value)} /></label><button className="primary-button" disabled={rawReport.trim().length < 20 || analyseMutation.isPending} onClick={() => analyseMutation.mutate()}>{analyseMutation.isPending ? <Loader2 className="spin" size={17} /> : <ShieldCheck size={17} />}Analyse imported report</button>{analyseMutation.isError && <p className="error-box">{errorMessage(analyseMutation.error)}</p>}</article>}
          {analyseMutation.data && <article className="surface"><div className="surface-heading"><Sparkles size={18} /><span>Structured synthetic findings</span></div><p className="notice-box">{analyseMutation.data.disclaimer}</p><h4>Recommended changes</h4><ul>{analyseMutation.data.recommended_changes.map((item) => <li key={item}>{item}</li>)}</ul><h4>Risks</h4><ul>{analyseMutation.data.risks.map((item) => <li key={item}>{item}</li>)}</ul><p>{analyseMutation.data.confidence_notes}</p></article>}
        </div>
      </div>
    </section>
  );
}

function PerformancePanel() {
  const queryClient = useQueryClient();
  const projects = useQuery({ queryKey: ['projects'], queryFn: api.projects });
  const entries = useQuery({ queryKey: ['performance'], queryFn: api.performance });
  const published = (projects.data ?? []).filter((project) => project.status === 'PUBLISHED');
  const [projectId, setProjectId] = useState('');
  const [platform, setPlatform] = useState('YouTube');
  const [recordedOn, setRecordedOn] = useState(new Date().toISOString().slice(0, 10));
  const [views, setViews] = useState(0);
  const [revenue, setRevenue] = useState(0);
  const [notes, setNotes] = useState('');
  const save = useMutation({
    mutationFn: () => api.savePerformance({ project_id: projectId, platform, recorded_on: recordedOn, views, likes: 0, comments: 0, shares: 0, watch_time_minutes: 0, revenue, currency: 'EUR', notes }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['performance'] }),
  });
  const totals = useMemo(() => (entries.data ?? []).reduce((acc, entry) => ({ views: acc.views + Number(entry.views), revenue: acc.revenue + Number(entry.revenue) }), { views: 0, revenue: 0 }), [entries.data]);

  return (
    <section>
      <PanelTitle eyebrow="Manual analytics" title="Verified performance ledger" copy="Enter values from platform dashboards. The system never estimates revenue from views." />
      <div className="metric-grid"><article className="metric-card"><span>Published projects</span><strong>{published.length}</strong><small>Pipeline status</small></article><article className="metric-card"><span>Logged views</span><strong>{totals.views.toLocaleString()}</strong><small>User-entered only</small></article><article className="metric-card"><span>Logged revenue</span><strong>€{totals.revenue.toFixed(2)}</strong><small>User-entered only</small></article><article className="metric-card"><span>Entries</span><strong>{entries.data?.length ?? 0}</strong><small>Platform/date records</small></article></div>
      <div className="two-column">
        <div className="surface form-stack">
          <label>Published project<select value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">Choose a project</option>{published.map((project) => <option value={project.id} key={project.id}>{project.title}</option>)}</select></label>
          <label>Platform<select value={platform} onChange={(event) => setPlatform(event.target.value)}><option>YouTube</option><option>TikTok</option><option>Instagram</option><option>Facebook</option></select></label>
          <label>Date<input type="date" value={recordedOn} onChange={(event) => setRecordedOn(event.target.value)} /></label>
          <label>Views<input type="number" min={0} value={views} onChange={(event) => setViews(Number(event.target.value))} /></label>
          <label>Revenue EUR<input type="number" min={0} step="0.01" value={revenue} onChange={(event) => setRevenue(Number(event.target.value))} /></label>
          <label>Notes<textarea rows={4} value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
          <button className="primary-button" disabled={!projectId || save.isPending} onClick={() => save.mutate()}>{save.isPending ? <Loader2 className="spin" size={17} /> : <Save size={17} />}Save verified entry</button>
          {save.isError && <p className="error-box">{errorMessage(save.error)}</p>}
        </div>
        <article className="surface">
          <div className="surface-heading"><BarChart3 size={18} /><span>Performance entries</span></div>
          {entries.isLoading && <LoadingBlock label="Loading entries" />}
          {!entries.isLoading && (entries.data?.length ?? 0) === 0 && <EmptyState icon={BarChart3} title="No data entered" copy="Move a quality-approved project to Published, then record verified metrics." />}
          <div className="table-wrap">{(entries.data?.length ?? 0) > 0 && <table><thead><tr><th>Date</th><th>Project</th><th>Platform</th><th>Views</th><th>Revenue</th></tr></thead><tbody>{entries.data?.map((entry: PerformanceEntry) => <tr key={entry.id}><td>{entry.recorded_on}</td><td>{entry.project_title}</td><td>{entry.platform}</td><td>{Number(entry.views).toLocaleString()}</td><td>{entry.currency} {Number(entry.revenue).toFixed(2)}</td></tr>)}</tbody></table>}</div>
        </article>
      </div>
    </section>
  );
}

function SettingsPanel({ health }: { health?: Health }) {
  const items = [
    { name: 'PostgreSQL', active: Boolean(health?.database), copy: 'Projects, research, simulations, and verified metrics.' },
    { name: `Ollama · ${health?.model ?? 'model unknown'}`, active: Boolean(health?.ollama), copy: 'Local scripts, scenes, analysis, and quality review.' },
    { name: 'SearXNG', active: Boolean(health?.search), copy: 'Self-hosted current public-web retrieval.' },
    { name: 'MiroFish', active: Boolean(health?.mirofish), copy: 'Manual seed/report workflow remains available while disconnected.' },
    { name: 'Node-RED', active: false, copy: 'Open http://localhost:1880 to build approved draft-production flows.' },
  ];
  return (
    <section>
      <PanelTitle eyebrow="Local services" title="Integration status" copy="All core data and AI services can run on your computer. Keep the stack private until authentication is added." />
      <div className="settings-grid">{items.map((item) => <article className="surface service-card" key={item.name}><StatusPill active={item.active} label={item.active ? 'Connected' : 'Not verified'} /><h3>{item.name}</h3><p>{item.copy}</p></article>)}</div>
      <article className="surface notice-card"><Database size={22} /><div><h3>Local single-user mode</h3><p>This build creates one local workspace automatically. Do not expose ports 5433, 8000, 8080, 11434, 1880, or 5001 publicly. Multi-user authentication is a separate hardening phase.</p></div></article>
    </section>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [creationSeed, setCreationSeed] = useState<ResearchIdea | null>(null);
  const [researchContext, setResearchContext] = useState<ResearchResult | null>(null);
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, refetchInterval: 30_000 });

  function useIdea(idea: ResearchIdea, result: ResearchResult) {
    setCreationSeed(idea);
    setResearchContext(result);
    setActiveTab('create');
  }

  const panel: Record<Tab, React.ReactNode> = {
    overview: <OverviewPanel health={health.data} />,
    research: <ResearchPanel onUseIdea={useIdea} />,
    create: <CreatePanel seed={creationSeed} researchContext={researchContext} onSaved={() => setActiveTab('pipeline')} />,
    pipeline: <PipelinePanel />,
    simulation: <SimulationPanel />,
    performance: <PerformancePanel />,
    settings: <SettingsPanel health={health.data} />,
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><Clapperboard size={21} /></span><div><strong>Studio</strong><small>CONTROL CENTER</small></div></div>
        <nav>{navigation.map(({ id, label, icon: Icon }) => <button key={id} className={activeTab === id ? 'nav-active' : ''} onClick={() => setActiveTab(id)}><Icon size={18} /><span>{label}</span></button>)}</nav>
        <div className="sidebar-footer"><StatusPill active={Boolean(health.data?.ollama)} label={health.data?.model ?? 'Local AI'} /><small>Human approval is required before production and publishing.</small></div>
      </aside>
      <main>
        <header className="topbar"><div><span className="eyebrow">LOCAL-FIRST WORKSPACE</span><strong>My Studio</strong></div><div className="topbar-status"><StatusPill active={health.data?.status === 'ok'} label={health.data?.status ?? 'Checking'} /><StatusPill active={false} label="Publishing manual" /></div></header>
        <div className="main-content">{panel[activeTab]}</div>
      </main>
    </div>
  );
}

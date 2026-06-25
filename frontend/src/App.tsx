import { FormEvent, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Activity,
  BarChart3,
  Bot,
  Clapperboard,
  FlaskConical,
  LayoutDashboard,
  Loader2,
  Network,
  Search,
  Settings,
  Sparkles,
  Workflow
} from 'lucide-react';
import { Background, Controls, Edge, Node, ReactFlow } from '@xyflow/react';
import { z } from 'zod';

const healthSchema = z.object({
  status: z.string(),
  ollama: z.boolean(),
  mirofish: z.boolean(),
  model: z.string()
});

const generationSchema = z.object({ model: z.string(), content: z.string() });

type Tab = 'overview' | 'research' | 'create' | 'pipeline' | 'simulation' | 'performance' | 'settings';

const navigation: Array<{ id: Tab; label: string; icon: typeof LayoutDashboard }> = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'research', label: 'Research', icon: Search },
  { id: 'create', label: 'Create', icon: Clapperboard },
  { id: 'pipeline', label: 'Pipeline', icon: Workflow },
  { id: 'simulation', label: 'Audience Simulation', icon: FlaskConical },
  { id: 'performance', label: 'Performance', icon: BarChart3 },
  { id: 'settings', label: 'Settings', icon: Settings }
];

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

function StatusPill({ active, label }: { active: boolean; label: string }) {
  return (
    <span className={`status-pill ${active ? 'status-live' : 'status-offline'}`}>
      <span className="status-dot" />
      {label}
    </span>
  );
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

function Overview({ health }: { health?: z.infer<typeof healthSchema> }) {
  const nodes = useMemo<Node[]>(
    () => [
      { id: 'research', position: { x: 0, y: 80 }, data: { label: 'Research' }, className: 'flow-node' },
      { id: 'create', position: { x: 210, y: 80 }, data: { label: 'Create' }, className: 'flow-node' },
      { id: 'simulate', position: { x: 420, y: 0 }, data: { label: 'Simulate' }, className: 'flow-node' },
      { id: 'quality', position: { x: 420, y: 155 }, data: { label: 'Quality Gate' }, className: 'flow-node' },
      { id: 'produce', position: { x: 650, y: 80 }, data: { label: 'Produce Draft' }, className: 'flow-node' }
    ],
    []
  );
  const edges = useMemo<Edge[]>(
    () => [
      { id: 'e1', source: 'research', target: 'create', animated: true },
      { id: 'e2', source: 'create', target: 'simulate', animated: true },
      { id: 'e3', source: 'simulate', target: 'quality', animated: true },
      { id: 'e4', source: 'quality', target: 'produce', animated: true }
    ],
    []
  );

  return (
    <section>
      <PanelTitle
        eyebrow="Orchestrator"
        title="Your local content studio"
        copy="Research, create, test and track original content while keeping local AI and human approval in control."
      />
      <div className="metric-grid">
        <article className="metric-card"><span>Projects</span><strong>0</strong><small>No projects saved yet</small></article>
        <article className="metric-card"><span>Research runs</span><strong>0</strong><small>No researched scans yet</small></article>
        <article className="metric-card"><span>Quality blocks</span><strong>0</strong><small>No projects evaluated</small></article>
        <article className="metric-card"><span>Published</span><strong>0</strong><small>No performance entered</small></article>
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
          <h3>Start with a researched topic</h3>
          <p>The catalog is empty. Run one sourced research scan, review the evidence, then send one idea to Create.</p>
          <div className="integration-stack">
            <StatusPill active={Boolean(health?.ollama)} label={`Ollama ${health?.ollama ? 'connected' : 'offline'}`} />
            <StatusPill active={Boolean(health?.mirofish)} label={`MiroFish ${health?.mirofish ? 'reachable' : 'manual mode'}`} />
          </div>
        </article>
      </div>
    </section>
  );
}

function ResearchPanel() {
  const [topic, setTopic] = useState('');
  const [audience, setAudience] = useState('');
  const [platform, setPlatform] = useState('YouTube');

  const mutation = useMutation({
    mutationFn: async () => {
      const prompt = [
        'Create a careful content research brief using only information supplied by the user.',
        'Do not claim current trends, view counts, revenue, search volume or popularity because live search is not connected yet.',
        `Topic: ${topic}`,
        `Audience: ${audience}`,
        `Platform: ${platform}`,
        'Return: questions to research, evidence needed, five clearly labelled creative hypotheses, and a source-verification checklist.'
      ].join('\n');
      const result = await apiRequest<unknown>('/ai/generate', {
        method: 'POST',
        body: JSON.stringify({ prompt, system: 'You are a cautious research-planning agent. Separate facts from hypotheses.', temperature: 0.3 })
      });
      return generationSchema.parse(result);
    }
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (topic.trim() && audience.trim()) mutation.mutate();
  }

  return (
    <section>
      <PanelTitle eyebrow="Research agent" title="Build an evidence-first brief" copy="Until SearXNG is connected, this screen creates a research plan—not fictional live market data." />
      <div className="two-column">
        <form className="surface form-stack" onSubmit={submit}>
          <label>Topic<input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="AI automation for land surveyors" required /></label>
          <label>Target audience<input value={audience} onChange={(event) => setAudience(event.target.value)} placeholder="Survey-company owners in Europe" required /></label>
          <label>Primary platform<select value={platform} onChange={(event) => setPlatform(event.target.value)}><option>YouTube</option><option>TikTok</option><option>Instagram Reels</option><option>LinkedIn</option></select></label>
          <button className="primary-button" disabled={mutation.isPending}>{mutation.isPending ? <Loader2 className="spin" size={17} /> : <Search size={17} />}Create research brief</button>
        </form>
        <article className="surface result-panel">
          <div className="surface-heading"><Sparkles size={18} /><span>Research output</span></div>
          {mutation.isError && <p className="error-box">{mutation.error.message}</p>}
          {mutation.data ? <pre>{mutation.data.content}</pre> : <div className="empty-state"><Search size={32} /><p>No research brief yet.</p></div>}
        </article>
      </div>
    </section>
  );
}

function CreatePanel() {
  const [topic, setTopic] = useState('');
  const [notes, setNotes] = useState('');
  const mutation = useMutation({
    mutationFn: async () => {
      const result = await apiRequest<unknown>('/ai/generate', {
        method: 'POST',
        body: JSON.stringify({
          system: 'You are an original content writer. Avoid generic filler and unsupported factual claims.',
          prompt: `Create a structured draft for this topic: ${topic}\nCreator expertise and notes: ${notes}\nReturn a title, hook, outline, human-review questions and a draft call to action.`,
          temperature: 0.5
        })
      });
      return generationSchema.parse(result);
    }
  });

  return (
    <section>
      <PanelTitle eyebrow="Creation agent" title="Develop an original episode" copy="Use your expertise as source material, then review every claim before production." />
      <div className="two-column">
        <div className="surface form-stack">
          <label>Working topic<input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="From GNSS points to final drawing" /></label>
          <label>Creator notes<textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Explain your real workflow, examples and limitations." rows={8} /></label>
          <button className="primary-button" disabled={!topic.trim() || mutation.isPending} onClick={() => mutation.mutate()}>{mutation.isPending ? <Loader2 className="spin" size={17} /> : <Bot size={17} />}Generate structured draft</button>
        </div>
        <article className="surface result-panel">
          <div className="surface-heading"><Clapperboard size={18} /><span>Draft package</span></div>
          {mutation.isError && <p className="error-box">{mutation.error.message}</p>}
          {mutation.data ? <pre>{mutation.data.content}</pre> : <div className="empty-state"><Clapperboard size={32} /><p>Add a topic and your real expertise.</p></div>}
        </article>
      </div>
    </section>
  );
}

function PipelinePanel() {
  const stages = ['QUEUE', 'SCRIPTED', 'IN PRODUCTION', 'RENDERING', 'REVIEW', 'PUBLISHED'];
  return (
    <section>
      <PanelTitle eyebrow="Execution tracker" title="Production pipeline" copy="Projects will move through these stages after database endpoints are connected." />
      <div className="kanban">
        {stages.map((stage) => <article className="kanban-column" key={stage}><header><span>{stage}</span><strong>0</strong></header><div className="empty-card">No projects</div></article>)}
      </div>
    </section>
  );
}

function SimulationPanel() {
  const [topic, setTopic] = useState('');
  const [question, setQuestion] = useState('Which hook creates trust without exaggerating the claim?');
  const mutation = useMutation({
    mutationFn: () => apiRequest<Record<string, unknown>>('/mirofish/seed', {
      method: 'POST',
      body: JSON.stringify({
        project_id: crypto.randomUUID(),
        topic,
        audience: { description: 'To be completed by the creator', countries: [], language: 'English', platform: 'YouTube' },
        content_variants: [],
        simulation_question: question,
        research_context: {}
      })
    })
  });

  return (
    <section>
      <PanelTitle eyebrow="MiroFish manual bridge" title="Prepare an audience-simulation seed" copy="Results are synthetic agent reactions, not real users or guaranteed predictions." />
      <div className="two-column">
        <div className="surface form-stack">
          <label>Project topic<input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="Can AI replace cadastral checking?" /></label>
          <label>Simulation question<textarea value={question} onChange={(event) => setQuestion(event.target.value)} rows={5} /></label>
          <button className="primary-button" disabled={!topic.trim() || mutation.isPending} onClick={() => mutation.mutate()}>{mutation.isPending ? <Loader2 className="spin" size={17} /> : <FlaskConical size={17} />}Generate manual seed</button>
        </div>
        <article className="surface result-panel">
          <div className="surface-heading"><FlaskConical size={18} /><span>MiroFish seed JSON</span></div>
          {mutation.isError && <p className="error-box">{mutation.error.message}</p>}
          {mutation.data ? <pre>{JSON.stringify(mutation.data, null, 2)}</pre> : <div className="empty-state"><FlaskConical size={32} /><p>No simulation seed yet.</p></div>}
        </article>
      </div>
    </section>
  );
}

function Placeholder({ type }: { type: 'performance' | 'settings' }) {
  const isPerformance = type === 'performance';
  return (
    <section>
      <PanelTitle eyebrow={isPerformance ? 'Manual analytics' : 'Local services'} title={isPerformance ? 'Performance' : 'Settings'} copy={isPerformance ? 'Only user-entered analytics will appear here; earnings are never inferred from views.' : 'Manage local model, search, simulation and automation connections.'} />
      <article className="surface empty-large">
        {isPerformance ? <BarChart3 size={42} /> : <Settings size={42} />}
        <h3>{isPerformance ? 'No published projects yet' : 'Configuration panel is next'}</h3>
        <p>{isPerformance ? 'Publish a reviewed project and enter verified platform metrics manually.' : 'The current health indicators already verify Ollama and MiroFish reachability.'}</p>
      </article>
    </section>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: async () => healthSchema.parse(await apiRequest<unknown>('/health')),
    refetchInterval: 30_000
  });

  const panel = {
    overview: <Overview health={healthQuery.data} />,
    research: <ResearchPanel />,
    create: <CreatePanel />,
    pipeline: <PipelinePanel />,
    simulation: <SimulationPanel />,
    performance: <Placeholder type="performance" />,
    settings: <Placeholder type="settings" />
  }[activeTab];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><Clapperboard size={21} /></span><div><strong>Studio</strong><small>CONTROL CENTER</small></div></div>
        <nav>{navigation.map(({ id, label, icon: Icon }) => <button key={id} className={activeTab === id ? 'nav-active' : ''} onClick={() => setActiveTab(id)}><Icon size={18} /><span>{label}</span></button>)}</nav>
        <div className="sidebar-footer"><StatusPill active={Boolean(healthQuery.data?.ollama)} label={healthQuery.data?.model ?? 'Local AI'} /><small>Human approval required before production.</small></div>
      </aside>
      <main>
        <header className="topbar"><div><span className="eyebrow">LOCAL-FIRST WORKSPACE</span><strong>My Studio</strong></div><div className="topbar-status"><StatusPill active={Boolean(healthQuery.data?.ollama)} label="AI" /><StatusPill active={false} label="Publishing manual" /></div></header>
        <div className="main-content">{panel}</div>
      </main>
    </div>
  );
}

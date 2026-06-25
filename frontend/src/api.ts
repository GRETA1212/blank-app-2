import type {
  Health,
  OverviewData,
  PerformanceEntry,
  Project,
  ProjectStatus,
  QualityReport,
  ResearchResult,
  Scene,
  ScriptPackage,
  SimulationFindings,
} from './types';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      // Keep the status-based message.
    }
    throw new Error(detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>('/health'),
  overview: () => request<OverviewData>('/overview'),
  projects: () => request<Project[]>('/projects'),
  research: (payload: {
    topic: string;
    audience: string;
    platform: string;
    region: string;
    language: string;
    notes: string;
  }) => request<ResearchResult>('/research', { method: 'POST', body: JSON.stringify(payload) }),
  generateScript: (payload: {
    topic: string;
    angle: string;
    audience: string;
    target_minutes: number;
    tone: string;
    creator_notes: string;
    research_context: Record<string, unknown>;
  }) => request<ScriptPackage>('/content/script', { method: 'POST', body: JSON.stringify(payload) }),
  generateScenes: (payload: {
    title: string;
    hook: string;
    narration: string;
    scene_count: number;
  }) => request<Scene[]>('/content/scenes', { method: 'POST', body: JSON.stringify(payload) }),
  qualityCheck: (payload: {
    title: string;
    hook: string;
    narration: string;
    scenes: Scene[];
    research_context: Record<string, unknown>;
    project_id?: string;
  }) => request<QualityReport>('/quality-check', { method: 'POST', body: JSON.stringify(payload) }),
  createProject: (payload: {
    title: string;
    topic: string;
    hook: string;
    narration: string;
    description: string;
    hashtags: string[];
    scenes: Scene[];
    quality_report: Partial<QualityReport>;
    status: ProjectStatus;
    platform_targets: string[];
  }) => request<Project>('/projects', { method: 'POST', body: JSON.stringify(payload) }),
  updateProject: (id: string, payload: Partial<Project>) =>
    request<Project>(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteProject: (id: string) => request<void>(`/projects/${id}`, { method: 'DELETE' }),
  mirofishSeed: (payload: {
    project_id: string;
    topic: string;
    audience: Record<string, unknown>;
    content_variants: Array<Record<string, unknown>>;
    simulation_question: string;
    research_context: Record<string, unknown>;
  }) => request<Record<string, unknown>>('/mirofish/seed', { method: 'POST', body: JSON.stringify(payload) }),
  analyseSimulation: (payload: {
    project_id: string;
    scenario_question: string;
    seed_payload: Record<string, unknown>;
    raw_report: string;
  }) => request<SimulationFindings>('/simulations/report', { method: 'POST', body: JSON.stringify(payload) }),
  performance: () => request<PerformanceEntry[]>('/performance'),
  savePerformance: (payload: {
    project_id: string;
    platform: string;
    recorded_on: string;
    views: number;
    likes: number;
    comments: number;
    shares: number;
    watch_time_minutes: number;
    revenue: number;
    currency: string;
    notes: string;
  }) => request<PerformanceEntry>('/performance', { method: 'POST', body: JSON.stringify(payload) }),
};

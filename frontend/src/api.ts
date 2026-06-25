import type {
  ApprovalReview,
  ContentDerivative,
  Health,
  MediaAsset,
  OverviewData,
  PerformanceEntry,
  ProductionJob,
  Project,
  ProjectStatus,
  QualityReport,
  ResearchResult,
  Scene,
  ScriptPackage,
  SimulationFindings,
  VoiceList,
  YouTubeStatus,
} from './types';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const response = await fetch(`/api${path}`, { ...init, headers });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      // Keep status-based message.
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
  research: (payload: { topic: string; audience: string; platform: string; region: string; language: string; notes: string }) =>
    request<ResearchResult>('/research', { method: 'POST', body: JSON.stringify(payload) }),
  generateScript: (payload: { topic: string; angle: string; audience: string; target_minutes: number; tone: string; creator_notes: string; research_context: object }) =>
    request<ScriptPackage>('/content/script', { method: 'POST', body: JSON.stringify(payload) }),
  generateScenes: (payload: { title: string; hook: string; narration: string; scene_count: number }) =>
    request<Scene[]>('/content/scenes', { method: 'POST', body: JSON.stringify(payload) }),
  qualityCheck: (payload: { title: string; hook: string; narration: string; scenes: Scene[]; research_context: object; project_id?: string }) =>
    request<QualityReport>('/quality-check', { method: 'POST', body: JSON.stringify(payload) }),
  createProject: (payload: { title: string; topic: string; hook: string; narration: string; description: string; hashtags: string[]; scenes: Scene[]; quality_report: Partial<QualityReport>; status: ProjectStatus; platform_targets: string[] }) =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify(payload) }),
  updateProject: (id: string, payload: Partial<Project>) => request<Project>(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteProject: (id: string) => request<void>(`/projects/${id}`, { method: 'DELETE' }),

  assets: (projectId?: string) => request<MediaAsset[]>(`/assets${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`),
  uploadAsset: (form: FormData) => request<MediaAsset>('/assets', { method: 'POST', body: form }),
  deleteAsset: (id: string) => request<void>(`/assets/${id}`, { method: 'DELETE' }),

  productionJobs: () => request<ProductionJob[]>('/production/jobs'),
  renderProject: (id: string, options: { aspect_ratio: '16:9' | '9:16'; voice_id?: string | null; burn_subtitles: boolean }) =>
    request<ProductionJob>(`/production/jobs/${id}`, { method: 'POST', body: JSON.stringify(options) }),
  derivatives: (projectId?: string) => request<ContentDerivative[]>(`/production/derivatives${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`),
  generateShorts: (jobId: string, payload: { count: number; duration_seconds: number }) =>
    request<{ derivatives: ContentDerivative[] }>(`/production/jobs/${jobId}/shorts`, { method: 'POST', body: JSON.stringify(payload) }),
  voices: () => request<VoiceList>('/production/voices'),
  previewVoice: (payload: { text: string; voice_id?: string | null }) =>
    request<{ audio_url: string; voice_engine: string }>('/production/voice-preview', { method: 'POST', body: JSON.stringify(payload) }),

  review: (projectId: string) => request<ApprovalReview>(`/reviews/${projectId}`),
  saveReview: (projectId: string, payload: ApprovalReview) =>
    request<ApprovalReview>(`/reviews/${projectId}`, { method: 'PUT', body: JSON.stringify(payload) }),

  youtubeStatus: () => request<YouTubeStatus>('/youtube/status'),
  youtubeStart: () => request<{ authorization_url: string }>('/youtube/oauth/start'),
  youtubeDisconnect: () => request<void>('/youtube/connection', { method: 'DELETE' }),
  youtubeUploadPrivate: (projectId: string, payload: { title?: string; description?: string; tags: string[]; category_id: string }) =>
    request<{ video_id?: string; studio_url?: string; notice: string }>(`/youtube/upload/${projectId}`, { method: 'POST', body: JSON.stringify(payload) }),

  mirofishSeed: (payload: { project_id: string; topic: string; audience: object; content_variants: object[]; simulation_question: string; research_context: object }) =>
    request<Record<string, unknown>>('/mirofish/seed', { method: 'POST', body: JSON.stringify(payload) }),
  analyseSimulation: (payload: { project_id: string; scenario_question: string; seed_payload: object; raw_report: string }) =>
    request<SimulationFindings>('/simulations/report', { method: 'POST', body: JSON.stringify(payload) }),
  performance: () => request<PerformanceEntry[]>('/performance'),
  savePerformance: (payload: { project_id: string; platform: string; recorded_on: string; views: number; likes: number; comments: number; shares: number; watch_time_minutes: number; revenue: number; currency: string; notes: string }) =>
    request<PerformanceEntry>('/performance', { method: 'POST', body: JSON.stringify(payload) }),
};

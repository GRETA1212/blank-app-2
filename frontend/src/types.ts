export type ProjectStatus =
  | 'QUEUE'
  | 'SCRIPTED'
  | 'IN_PRODUCTION'
  | 'RENDERING'
  | 'REVIEW'
  | 'PUBLISHED';

export interface Health {
  status: string;
  database: boolean;
  ollama: boolean;
  search: boolean;
  mirofish: boolean;
  model: string;
}

export interface OverviewData {
  project_counts: Record<string, number>;
  research_runs: number;
  quality_blocks: number;
  next_action: string;
}

export interface SourceItem {
  id: string;
  title: string;
  url: string;
  publisher: string;
  published_date: string;
  snippet: string;
}

export interface ResearchIdea {
  topic: string;
  angle: string;
  hook: string;
  rationale: string;
  audience: string;
  format: 'long_video' | 'short_video';
  estimated_duration: string;
  supporting_source_ids: string[];
  evidence_level: 'verified' | 'inference' | 'creative_hypothesis';
}

export interface ResearchResult {
  id?: string;
  research_date: string;
  query_summary: string;
  landscape_summary: string;
  verified_observations: Array<{ observation: string; source_ids: string[] }>;
  content_gaps: Array<{ gap: string; evidence: string; source_ids: string[]; confidence: string }>;
  sources: SourceItem[];
  ideas: ResearchIdea[];
}

export interface ScriptPackage {
  title: string;
  hook: string;
  narration: string;
  description: string;
  hashtags: string[];
  platform_targets: string[];
}

export interface Scene {
  scene_number: number;
  duration_seconds: number;
  purpose: string;
  visual_direction: string;
  onscreen_text: string;
  voice_segment: string;
  asset_notes: string;
}

export interface QualityReport {
  pass: boolean;
  score: number;
  blocking_issues: string[];
  warnings: string[];
  originality_notes: string;
  human_review_checklist: string[];
}

export interface Project {
  id: string;
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
  created_at: string;
  updated_at: string;
  published_at?: string | null;
}

export interface ProductionJob {
  id: string;
  project_id: string;
  project_title?: string;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  worker: string;
  output_url?: string | null;
  subtitle_url?: string | null;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  notice?: string;
}

export interface PerformanceEntry {
  id: string;
  project_id: string;
  project_title: string;
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
}

export interface SimulationFindings {
  simulation_run_id: string;
  disclaimer: string;
  audience_segments: Array<Record<string, unknown>>;
  hook_comparison: Array<Record<string, unknown>>;
  objections: string[];
  predicted_comments: string[];
  risks: string[];
  recommended_changes: string[];
  confidence_notes: string;
}

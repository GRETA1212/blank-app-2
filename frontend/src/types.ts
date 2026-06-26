export type ProjectStatus =
  | 'QUEUE'
  | 'SCRIPTED'
  | 'IN_PRODUCTION'
  | 'RENDERING'
  | 'REVIEW'
  | 'PUBLISHED';

export type LanguageCode = 'en' | 'it' | 'sq' | 'mk';

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
  [key: string]: unknown;
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
  asset_id?: string | null;
  fit?: 'cover' | 'contain';
  motion?: 'none' | 'slow_zoom';
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

export interface LanguageOption {
  code: LanguageCode;
  name: string;
  default_voice_id: string;
}

export interface LocalizedVariant {
  id: string;
  project_id: string;
  language_code: LanguageCode;
  language_name: string;
  title: string;
  hook: string;
  narration: string;
  description: string;
  hashtags: string[];
  scenes: Scene[];
  voice_id?: string | null;
  translation_notes: string;
  review_status: 'NEEDS_REVIEW' | 'APPROVED' | 'REJECTED';
  created_at: string;
  updated_at: string;
}

export interface SubtitleVerification {
  passed?: boolean;
  similarity?: number | null;
  threshold?: number;
  detected_language?: string;
  language_probability?: number;
  segment_count?: number;
  missing_words_sample?: string[];
  unexpected_words_sample?: string[];
  warning?: string;
}

export interface ProductionJob {
  id: string;
  project_id: string;
  project_title?: string;
  content_variant_id?: string | null;
  variant_language_name?: string | null;
  variant_title?: string | null;
  language_code?: LanguageCode | null;
  voice_id?: string | null;
  voice_engine?: string | null;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  worker: string;
  output_url?: string | null;
  subtitle_url?: string | null;
  transcript_url?: string | null;
  subtitle_verification?: SubtitleVerification;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  notice?: string;
  renderer?: {
    subtitle_verification?: SubtitleVerification;
    voice_engine?: string;
    voice_id?: string;
    language_code?: LanguageCode;
  };
}

export interface MediaAsset {
  id: string;
  project_id?: string | null;
  file_name: string;
  media_type: 'IMAGE' | 'VIDEO' | 'AUDIO' | 'DOCUMENT';
  mime_type: string;
  file_size: number;
  public_url: string;
  license_status: 'OWNED' | 'LICENSED' | 'PUBLIC_DOMAIN' | 'UNKNOWN';
  license_source: string;
  attribution: string;
  notes: string;
  created_at: string;
}

export interface ApprovalReview {
  project_id: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  factual_review: boolean;
  rights_review: boolean;
  ai_disclosure_review: boolean;
  audio_review: boolean;
  visual_review: boolean;
  subtitle_review: boolean;
  reviewer_notes: string;
  decided_at?: string | null;
}

export interface VoiceOption {
  id: string;
  display_name: string;
  language_code: LanguageCode;
  engine: 'piper' | 'espeak-ng';
  natural: boolean;
  recommended: boolean;
  installed: boolean;
  model_source: string;
  license_review_required: boolean;
}

export interface VoiceList {
  voices: VoiceOption[];
  defaults: Record<LanguageCode, string>;
  notice: string;
}

export interface ContentDerivative {
  id: string;
  project_id: string;
  production_job_id: string;
  kind: 'SHORT' | 'REEL' | 'TIKTOK' | 'THUMBNAIL';
  variant_label: string;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  output_url?: string | null;
  error_message?: string | null;
}

export interface YouTubeStatus {
  configured: boolean;
  connected: boolean;
  account_id?: string | null;
  account_name?: string | null;
  status: string;
  upload_policy: 'private-only';
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

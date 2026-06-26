create table if not exists media_assets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references app_users(id) on delete cascade,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  project_id uuid references projects(id) on delete cascade,
  file_name text not null,
  stored_name text not null,
  media_type text not null check (media_type in ('IMAGE', 'VIDEO', 'AUDIO', 'DOCUMENT')),
  mime_type text not null,
  file_size bigint not null check (file_size >= 0),
  storage_path text not null,
  public_url text not null,
  license_status text not null default 'UNKNOWN'
    check (license_status in ('OWNED', 'LICENSED', 'PUBLIC_DOMAIN', 'UNKNOWN')),
  license_source text not null default '',
  attribution text not null default '',
  notes text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists approval_reviews (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references app_users(id) on delete cascade,
  project_id uuid not null references projects(id) on delete cascade,
  status text not null default 'PENDING'
    check (status in ('PENDING', 'APPROVED', 'REJECTED')),
  factual_review boolean not null default false,
  rights_review boolean not null default false,
  ai_disclosure_review boolean not null default false,
  audio_review boolean not null default false,
  visual_review boolean not null default false,
  subtitle_review boolean not null default false,
  reviewer_notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  decided_at timestamptz,
  unique (project_id)
);

create table if not exists oauth_states (
  state text primary key,
  user_id uuid not null references app_users(id) on delete cascade,
  platform text not null,
  redirect_after text not null default 'http://localhost:3000',
  expires_at timestamptz not null,
  created_at timestamptz not null default now()
);

create table if not exists platform_connections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references app_users(id) on delete cascade,
  platform text not null,
  encrypted_credentials text not null,
  account_id text,
  account_name text,
  scopes text[] not null default '{}',
  status text not null default 'CONNECTED'
    check (status in ('CONNECTED', 'EXPIRED', 'DISCONNECTED', 'ERROR')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, platform)
);

create table if not exists platform_uploads (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references app_users(id) on delete cascade,
  project_id uuid not null references projects(id) on delete cascade,
  production_job_id uuid not null references production_jobs(id) on delete cascade,
  platform text not null,
  status text not null default 'QUEUED'
    check (status in ('QUEUED', 'UPLOADING', 'COMPLETED', 'FAILED')),
  privacy_status text not null default 'private'
    check (privacy_status in ('private', 'unlisted', 'public')),
  external_id text,
  external_url text,
  upload_title text not null,
  upload_description text not null default '',
  error_message text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create table if not exists content_derivatives (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references app_users(id) on delete cascade,
  project_id uuid not null references projects(id) on delete cascade,
  production_job_id uuid not null references production_jobs(id) on delete cascade,
  kind text not null check (kind in ('SHORT', 'REEL', 'TIKTOK', 'THUMBNAIL')),
  variant_label text not null,
  status text not null default 'QUEUED'
    check (status in ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED')),
  output_url text,
  error_message text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists idx_media_assets_project on media_assets(project_id, created_at desc);
create index if not exists idx_approval_reviews_project on approval_reviews(project_id);
create index if not exists idx_platform_uploads_project on platform_uploads(project_id, created_at desc);
create index if not exists idx_derivatives_project on content_derivatives(project_id, created_at desc);
create index if not exists idx_oauth_states_expiry on oauth_states(expires_at);

alter table approval_reviews drop constraint if exists approval_requires_checklist;
alter table approval_reviews add constraint approval_requires_checklist check (
  status <> 'APPROVED' or (
    factual_review and rights_review and ai_disclosure_review and
    audio_review and visual_review and subtitle_review
  )
);

drop trigger if exists approval_reviews_set_updated_at on approval_reviews;
drop trigger if exists platform_connections_set_updated_at on platform_connections;
create trigger approval_reviews_set_updated_at before update on approval_reviews for each row execute function set_updated_at();
create trigger platform_connections_set_updated_at before update on platform_connections for each row execute function set_updated_at();

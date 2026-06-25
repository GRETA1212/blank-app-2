create table if not exists production_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references app_users(id) on delete cascade,
  project_id uuid not null references projects(id) on delete cascade,
  status text not null default 'QUEUED'
    check (status in ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')),
  worker text not null default 'LOCAL_FFMPEG',
  output_url text,
  subtitle_url text,
  error_message text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz
);

create index if not exists idx_production_jobs_project_created
  on production_jobs(project_id, created_at desc);
create index if not exists idx_production_jobs_status
  on production_jobs(status, created_at desc);

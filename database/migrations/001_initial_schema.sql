create extension if not exists pgcrypto;

create table if not exists app_users (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  password_hash text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists workspaces (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references app_users(id) on delete cascade,
  name text not null default 'My Studio',
  niche text not null default '',
  audience text not null default '',
  primary_platform text not null default 'YouTube',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists research_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references app_users(id) on delete cascade,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  query text not null,
  research_date date not null default current_date,
  landscape_summary text not null default '',
  verified_observations jsonb not null default '[]'::jsonb,
  content_gaps jsonb not null default '[]'::jsonb,
  sources jsonb not null default '[]'::jsonb,
  raw_result jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists ideas (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references app_users(id) on delete cascade,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  research_run_id uuid references research_runs(id) on delete set null,
  topic text not null,
  angle text not null default '',
  hook text not null default '',
  rationale text not null default '',
  audience text not null default '',
  format text not null default 'long_video' check (format in ('long_video', 'short_video')),
  estimated_duration text not null default '',
  evidence_level text not null default 'creative_hypothesis' check (evidence_level in ('verified', 'inference', 'creative_hypothesis')),
  supporting_source_ids jsonb not null default '[]'::jsonb,
  status text not null default 'IDEA' check (status in ('IDEA', 'SELECTED', 'ARCHIVED')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references app_users(id) on delete cascade,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  idea_id uuid references ideas(id) on delete set null,
  title text not null,
  topic text not null,
  hook text not null default '',
  narration text not null default '',
  description text not null default '',
  hashtags text[] not null default '{}',
  scenes jsonb not null default '[]'::jsonb,
  quality_report jsonb not null default '{}'::jsonb,
  status text not null default 'QUEUE' check (status in ('QUEUE', 'SCRIPTED', 'IN_PRODUCTION', 'RENDERING', 'REVIEW', 'PUBLISHED')),
  platform_targets text[] not null default '{}',
  sample boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  published_at timestamptz
);

create table if not exists simulation_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references app_users(id) on delete cascade,
  project_id uuid not null references projects(id) on delete cascade,
  provider text not null default 'MIROFISH',
  status text not null default 'DRAFT' check (status in ('DRAFT', 'READY', 'RUNNING', 'COMPLETED', 'FAILED')),
  scenario_question text not null default '',
  seed_payload jsonb not null default '{}'::jsonb,
  raw_report text,
  structured_result jsonb,
  error_message text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz
);

create table if not exists simulation_findings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references app_users(id) on delete cascade,
  simulation_run_id uuid not null references simulation_runs(id) on delete cascade,
  audience_segments jsonb not null default '[]'::jsonb,
  hook_comparison jsonb not null default '[]'::jsonb,
  objections jsonb not null default '[]'::jsonb,
  predicted_comments jsonb not null default '[]'::jsonb,
  risks jsonb not null default '[]'::jsonb,
  recommended_changes jsonb not null default '[]'::jsonb,
  confidence_notes text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists performance_entries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references app_users(id) on delete cascade,
  project_id uuid not null references projects(id) on delete cascade,
  platform text not null,
  recorded_on date not null default current_date,
  views bigint not null default 0 check (views >= 0),
  likes bigint not null default 0 check (likes >= 0),
  comments bigint not null default 0 check (comments >= 0),
  shares bigint not null default 0 check (shares >= 0),
  watch_time_minutes numeric(14,2) not null default 0 check (watch_time_minutes >= 0),
  revenue numeric(14,2) not null default 0 check (revenue >= 0),
  currency char(3) not null default 'EUR',
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, platform, recorded_on)
);

create index if not exists idx_workspaces_user on workspaces(user_id);
create index if not exists idx_research_workspace_date on research_runs(workspace_id, created_at desc);
create index if not exists idx_ideas_workspace_status on ideas(workspace_id, status);
create index if not exists idx_projects_workspace_status on projects(workspace_id, status);
create index if not exists idx_simulations_project_status on simulation_runs(project_id, status);
create index if not exists idx_performance_project_date on performance_entries(project_id, recorded_on desc);

create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists app_users_set_updated_at on app_users;
drop trigger if exists workspaces_set_updated_at on workspaces;
drop trigger if exists ideas_set_updated_at on ideas;
drop trigger if exists projects_set_updated_at on projects;
drop trigger if exists performance_entries_set_updated_at on performance_entries;

create trigger app_users_set_updated_at before update on app_users for each row execute function set_updated_at();
create trigger workspaces_set_updated_at before update on workspaces for each row execute function set_updated_at();
create trigger ideas_set_updated_at before update on ideas for each row execute function set_updated_at();
create trigger projects_set_updated_at before update on projects for each row execute function set_updated_at();
create trigger performance_entries_set_updated_at before update on performance_entries for each row execute function set_updated_at();

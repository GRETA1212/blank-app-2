create table if not exists content_variants (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references app_users(id) on delete cascade,
  project_id uuid not null references projects(id) on delete cascade,
  language_code text not null check (language_code in ('en', 'it', 'sq', 'mk')),
  language_name text not null,
  title text not null,
  hook text not null default '',
  narration text not null default '',
  description text not null default '',
  hashtags text[] not null default '{}',
  scenes jsonb not null default '[]'::jsonb,
  voice_id text,
  translation_notes text not null default '',
  review_status text not null default 'NEEDS_REVIEW'
    check (review_status in ('NEEDS_REVIEW', 'APPROVED', 'REJECTED')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, language_code)
);

alter table production_jobs add column if not exists content_variant_id uuid references content_variants(id) on delete set null;
alter table production_jobs add column if not exists language_code text;
alter table production_jobs add column if not exists voice_id text;
alter table production_jobs add column if not exists voice_engine text;
alter table production_jobs add column if not exists transcript_url text;
alter table production_jobs add column if not exists subtitle_verification jsonb not null default '{}'::jsonb;

create index if not exists idx_content_variants_project_language
  on content_variants(project_id, language_code);
create index if not exists idx_production_jobs_variant
  on production_jobs(content_variant_id, created_at desc);

drop trigger if exists content_variants_set_updated_at on content_variants;
create trigger content_variants_set_updated_at
  before update on content_variants
  for each row execute function set_updated_at();

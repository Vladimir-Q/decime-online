-- Persisted dictionary export/import jobs for n8n + Google Sheets integration.

create table if not exists dictionary_sheets_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references app_users(id) on delete cascade,
  list_id uuid not null references training_lists(id) on delete cascade,
  kind text not null check (kind in ('export', 'import')),
  status text not null check (status in ('queued', 'running', 'completed', 'failed')),
  spreadsheet_id text,
  sheet_name text,
  source_spreadsheet_id text,
  source_sheet_name text,
  report jsonb not null default '{}'::jsonb,
  error_message text,
  accepted_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists dictionary_sheets_jobs_user_created_idx
  on dictionary_sheets_jobs (user_id, created_at desc);

create index if not exists dictionary_sheets_jobs_status_updated_idx
  on dictionary_sheets_jobs (status, updated_at);

-- At most one active export per user (serialize writes to the shared user sheet).
create unique index if not exists dictionary_sheets_jobs_one_active_export_idx
  on dictionary_sheets_jobs (user_id)
  where kind = 'export' and status in ('queued', 'running');

create table if not exists dictionary_sheets_import_rows (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references dictionary_sheets_jobs(id) on delete cascade,
  source_row_number int not null,
  status text not null check (status in ('created', 'skipped_duplicate', 'error')),
  item_id uuid references training_items(id) on delete set null,
  message text,
  created_at timestamptz not null default now(),
  unique (job_id, source_row_number)
);

create index if not exists dictionary_sheets_import_rows_job_idx
  on dictionary_sheets_import_rows (job_id);

-- App language preference + translation ratings + LLM usage for admin dashboard.

alter table if exists app_users
  add column if not exists app_language text;

create table if not exists translation_ratings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references app_users(id) on delete set null,
  feature text not null,
  rating smallint not null,
  source_text text,
  result_text text,
  direction text,
  created_at timestamptz not null default now(),
  constraint translation_ratings_feature_check check (feature in ('quick_reply', 'live_chat')),
  constraint translation_ratings_rating_check check (rating in (-1, 0, 1))
);

create index if not exists idx_translation_ratings_created
  on translation_ratings (created_at desc);
create index if not exists idx_translation_ratings_rating
  on translation_ratings (rating, created_at desc);

create table if not exists llm_usage (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references app_users(id) on delete set null,
  operation text not null,
  provider text not null default 'openai',
  model text not null,
  prompt_tokens integer not null default 0,
  completion_tokens integer not null default 0,
  total_tokens integer not null default 0,
  estimated_cost_usd numeric(12, 6) not null default 0,
  created_at timestamptz not null default now()
);

create index if not exists idx_llm_usage_created on llm_usage (created_at desc);
create index if not exists idx_llm_usage_user_created on llm_usage (user_id, created_at desc);

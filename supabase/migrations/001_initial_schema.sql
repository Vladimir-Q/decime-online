-- Decime UY initial schema (Phase 1+)
-- Apply with Supabase CLI: supabase db push

create extension if not exists "pgcrypto";

create table profiles (
  id uuid primary key,
  email text,
  display_name text,
  native_language text default 'ru',
  secondary_language text default 'en',
  target_locale text default 'es-UY-montevideo',
  user_level text default 'A2',
  created_at timestamptz default now()
);

create table locale_variants (
  id text primary key,
  country text not null,
  region text,
  label text not null,
  is_active boolean default true,
  default_formality text,
  pronoun_policy text,
  notes text
);

create table situations (
  id uuid primary key default gen_random_uuid(),
  code text unique not null,
  label_ru text not null,
  label_en text not null,
  label_es text,
  default_channel text,
  created_at timestamptz default now()
);

create table audio_files (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  source_type text not null,
  storage_path text not null,
  public_url text,
  mime_type text,
  duration_ms int,
  provider text,
  model text,
  voice text,
  text_hash text,
  created_at timestamptz default now()
);

create table transcripts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  audio_id uuid references audio_files(id),
  language text,
  transcript text not null,
  provider text,
  model text,
  raw_payload jsonb,
  created_at timestamptz default now()
);

create table reply_requests (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  source_language text,
  source_text text,
  incoming_text text,
  incoming_audio_id uuid references audio_files(id),
  transcript_id uuid references transcripts(id),
  situation_id uuid references situations(id),
  situation_code text,
  channel text,
  tone text,
  target_locale text default 'es-UY-montevideo',
  user_level text,
  source_type text,
  created_at timestamptz default now()
);

create table reply_outputs (
  id uuid primary key default gen_random_uuid(),
  request_id uuid references reply_requests(id) on delete cascade,
  recommended_reply text not null,
  simple_reply text,
  short_reply text,
  more_formal_reply text,
  intent_summary_ru text,
  intent_summary_en text,
  notes_ru jsonb,
  notes_en jsonb,
  warnings jsonb,
  dialect_stamp text,
  raw_json jsonb,
  provider text,
  model text,
  latency_ms int,
  created_at timestamptz default now()
);

create table training_lists (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  name text not null,
  source text default 'manual',
  locale_variant text references locale_variants(id),
  is_base boolean default false,
  created_at timestamptz default now()
);

create table training_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  list_id uuid references training_lists(id),
  item_type text not null,
  surface_text text not null,
  display_text text not null,
  lemma text,
  locale_variant text references locale_variants(id),
  translations_ru jsonb not null default '[]'::jsonb,
  translations_en jsonb not null default '[]'::jsonb,
  context_translation_ru text,
  context_translation_en text,
  grammar jsonb not null default '{}'::jsonb,
  governance jsonb not null default '[]'::jsonb,
  example_es text,
  example_ru text,
  example_en text,
  audio_id uuid references audio_files(id),
  source_type text,
  source_language text,
  source_original_text text,
  source_transcript_id uuid references transcripts(id),
  source_reply_output_id uuid references reply_outputs(id),
  status text default 'approved',
  canonical_key text,
  next_review_at timestamptz default now(),
  review_stage int default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create unique index training_items_user_canonical_key_idx
  on training_items(user_id, canonical_key)
  where canonical_key is not null and status in ('approved', 'known');

create table extraction_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  source_type text not null,
  source_language text,
  source_original_text text,
  spanish_text text not null,
  target_locale text default 'es-UY-montevideo',
  raw_candidates jsonb,
  provider text,
  model text,
  created_at timestamptz default now()
);

create table training_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  item_id uuid references training_items(id),
  review_mode text not null,
  grade text not null,
  response_latency_ms int,
  used_hint boolean default false,
  user_answer_text text,
  attempt_audio_id uuid references audio_files(id),
  transcript_id uuid references transcripts(id),
  created_at timestamptz default now()
);

create table event_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz default now()
);

create index reply_outputs_request_id_idx on reply_outputs(request_id);
create index reply_outputs_created_at_idx on reply_outputs(created_at desc);

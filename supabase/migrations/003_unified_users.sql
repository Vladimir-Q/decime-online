-- Unified identity: app_users is canonical; drop unused profiles FKs.

-- Re-point user_id columns from profiles to app_users (002 must exist).

alter table if exists audio_files drop constraint if exists audio_files_user_id_fkey;
alter table if exists transcripts drop constraint if exists transcripts_user_id_fkey;
alter table if exists reply_requests drop constraint if exists reply_requests_user_id_fkey;
alter table if exists training_lists drop constraint if exists training_lists_user_id_fkey;
alter table if exists training_items drop constraint if exists training_items_user_id_fkey;
alter table if exists extraction_runs drop constraint if exists extraction_runs_user_id_fkey;
alter table if exists training_attempts drop constraint if exists training_attempts_user_id_fkey;
alter table if exists event_log drop constraint if exists event_log_user_id_fkey;

alter table if exists audio_files
  add constraint audio_files_user_id_fkey
  foreign key (user_id) references app_users(id) on delete cascade;

alter table if exists transcripts
  add constraint transcripts_user_id_fkey
  foreign key (user_id) references app_users(id) on delete cascade;

alter table if exists reply_requests
  add constraint reply_requests_user_id_fkey
  foreign key (user_id) references app_users(id) on delete cascade;

alter table if exists training_lists
  add constraint training_lists_user_id_fkey
  foreign key (user_id) references app_users(id) on delete cascade;

alter table if exists training_items
  add constraint training_items_user_id_fkey
  foreign key (user_id) references app_users(id) on delete cascade;

alter table if exists extraction_runs
  add constraint extraction_runs_user_id_fkey
  foreign key (user_id) references app_users(id) on delete cascade;

alter table if exists training_attempts
  add constraint training_attempts_user_id_fkey
  foreign key (user_id) references app_users(id) on delete cascade;

alter table if exists event_log
  add constraint event_log_user_id_fkey
  foreign key (user_id) references app_users(id) on delete set null;

drop table if exists profiles;

insert into locale_variants (id, country, region, label, default_formality, pronoun_policy, notes)
values (
  'es-UY-montevideo',
  'Uruguay',
  'Montevideo',
  'Uruguayan Spanish / Montevideo',
  'polite_neutral',
  'vos default where natural; ustedes plural',
  'MVP default locale. Avoid Spain-specific output and excessive Buenos Aires slang.'
)
on conflict (id) do nothing;

create index if not exists idx_training_items_user_list on training_items(user_id, list_id);
create index if not exists idx_training_items_next_review on training_items(user_id, next_review_at);
create index if not exists idx_reply_requests_user_created on reply_requests(user_id, created_at desc);
create index if not exists idx_event_log_user_created on event_log(user_id, created_at desc);
create index if not exists idx_event_log_type_created on event_log(event_type, created_at desc);

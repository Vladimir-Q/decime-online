-- Price status for LLM usage. Existing rows keep their stored dollar amount and
-- are marked legacy_unverified so a new catalog does not silently reprice history.

alter table llm_usage
  add column if not exists price_status text not null default 'legacy_unverified',
  add column if not exists pricing_version text,
  add column if not exists usage_raw jsonb;

alter table llm_usage
  drop constraint if exists llm_usage_price_status_check;

alter table llm_usage
  add constraint llm_usage_price_status_check
  check (price_status in ('known', 'unknown_price', 'legacy_unverified'));

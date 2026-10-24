-- Auth users for self-hosted / VM (SQLite uses the same shape in apps/api).
-- When using Supabase Auth later, link profiles.id to auth.users.id.

create table if not exists app_users (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  password_hash text not null,
  display_name text,
  role text not null default 'user' check (role in ('admin', 'user')),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_app_users_email on app_users (lower(email));

-- Optional: tie existing profile rows to app_users when migrating from single-user MVP
-- alter table profiles add column if not exists app_user_id uuid references app_users(id);

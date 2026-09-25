-- ============================================================================
-- Mock exam platform – Supabase schema
--
-- Run this once in the Supabase dashboard: SQL Editor → New query → paste → Run.
-- It is safe to run again (every statement is idempotent).
--
-- Security model
--   * Row Level Security is ON for every table and NO policies are defined, so
--     the public "anon" key cannot read or write anything – in particular it
--     can never see answer keys.
--   * Only the server uses the "service_role" key (which bypasses RLS). Keep that
--     key secret: set it as an environment variable on your host, never in
--     frontend code or in git.
-- ============================================================================

-- Test content (reading and writing). The full test, including answer keys and
-- model answers, is stored as JSON in `content`. The server strips private
-- fields before sending a test to candidates.
create table if not exists public.tests (
  id            text primary key,
  module        text not null check (module in ('reading', 'writing')),
  variant       text not null default 'academic',
  title         text not null,
  sort_order    integer not null default 999,
  is_published  boolean not null default true,
  content       jsonb not null,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index if not exists tests_module_sort_idx on public.tests (module, sort_order);

-- Keep updated_at current on every update.
create or replace function public.touch_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists tests_touch_updated_at on public.tests;
create trigger tests_touch_updated_at before update on public.tests
  for each row execute function public.touch_updated_at();

-- One row per submitted reading test.
create table if not exists public.reading_attempts (
  id                  bigint generated always as identity primary key,
  test_id             text not null,
  client_id           uuid,
  candidate_name      text,
  mode                text check (mode in ('exam', 'practice')),
  raw_score           integer not null check (raw_score between 0 and 40),
  total_questions     integer not null,
  band_score          numeric(2,1) not null,
  time_spent_seconds  integer,
  answers             jsonb,
  breakdown           jsonb,
  created_at          timestamptz not null default now()
);

create index if not exists reading_attempts_client_idx on public.reading_attempts (client_id, created_at desc);
create index if not exists reading_attempts_test_idx on public.reading_attempts (test_id);

-- One row per submitted writing test (both tasks).
create table if not exists public.writing_submissions (
  id                  bigint generated always as identity primary key,
  test_id             text not null,
  client_id           uuid,
  candidate_name      text,
  task1_text          text,
  task2_text          text,
  task1_words         integer,
  task2_words         integer,
  time_spent_seconds  integer,
  analysis            jsonb,
  assessment          jsonb,
  overall_band        numeric(2,1),
  created_at          timestamptz not null default now()
);

create index if not exists writing_submissions_client_idx on public.writing_submissions (client_id, created_at desc);
create index if not exists writing_submissions_test_idx on public.writing_submissions (test_id);

-- Lock everything down: RLS on, no policies → no access with the anon key.
alter table public.tests               enable row level security;
alter table public.reading_attempts    enable row level security;
alter table public.writing_submissions enable row level security;

-- ============================================================================
-- Mock exam platform – Supabase schema
--
-- Run this once in the Supabase dashboard: SQL Editor → New query → paste → Run.
-- It is safe to run again (every statement is idempotent).
--
-- Security model
--   * Row Level Security is ON for every table and NO policies are defined, so
--     the public publishable/anon key cannot read or write any table directly –
--     in particular it can never see answer keys, transcripts or essays.
--   * The server works only through the app_* functions at the end of this
--     file. Each one checks a server secret (SUPABASE_APP_SECRET) whose SHA-256
--     hash is kept in the private schema. Keep the secret out of frontend code
--     and git; set it as an environment variable on your host.
-- ============================================================================

-- Test content (reading, listening and writing). The full test, including
-- answer keys, transcripts and model answers, is stored as JSON in `content`.
-- The server strips private fields before sending a test to candidates.
create table if not exists public.tests (
  id            text primary key,
  module        text not null check (module in ('reading', 'listening', 'writing')),
  variant       text not null default 'academic',
  title         text not null,
  sort_order    integer not null default 999,
  is_published  boolean not null default true,
  content       jsonb not null,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index if not exists tests_module_sort_idx on public.tests (module, sort_order);

-- Databases created before the Listening module allowed only reading/writing.
alter table public.tests drop constraint if exists tests_module_check;
alter table public.tests add constraint tests_module_check check (module in ('reading', 'listening', 'writing'));

-- Keep updated_at current on every update.
create or replace function public.touch_updated_at() returns trigger
language plpgsql set search_path = '' as $$
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

-- One row per submitted listening test (same shape as reading attempts).
create table if not exists public.listening_attempts (
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

create index if not exists listening_attempts_client_idx on public.listening_attempts (client_id, created_at desc);
create index if not exists listening_attempts_test_idx on public.listening_attempts (test_id);

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
alter table public.listening_attempts  enable row level security;
alter table public.writing_submissions enable row level security;

-- ============================================================================
-- Server API (Postgres functions called through Supabase's REST /rpc endpoint)
--
-- The server talks to the database only through these functions, using the
-- public "publishable"/anon key plus a server secret. The secret itself is
-- never stored: only its SHA-256 hash lives in the private schema, which the
-- REST API does not expose. Every function checks the secret first, so the
-- public key alone cannot read answer keys or anyone's essays.
--
-- Set the secret once (replace the value, keep it identical to the
-- SUPABASE_APP_SECRET environment variable on your server):
--   insert into private.app_secrets (name, secret_hash)
--   values ('server', encode(sha256(convert_to('YOUR-LONG-RANDOM-SECRET', 'UTF8')), 'hex'))
--   on conflict (name) do update set secret_hash = excluded.secret_hash;
-- ============================================================================

create schema if not exists private;
revoke all on schema private from public;
revoke all on schema private from anon, authenticated;

create table if not exists private.app_secrets (
  name        text primary key,
  secret_hash text not null,
  created_at  timestamptz not null default now()
);
alter table private.app_secrets enable row level security;

create or replace function private.check_app_key(p_key text) returns void
language plpgsql security definer set search_path = '' as $$
begin
  if p_key is null or length(p_key) < 32 or not exists (
    select 1 from private.app_secrets s
    where s.name = 'server'
      and s.secret_hash = encode(sha256(convert_to(p_key, 'UTF8')), 'hex')
  ) then
    raise exception 'invalid app key' using errcode = '28000';
  end if;
end;
$$;
revoke all on function private.check_app_key(text) from public, anon, authenticated;

create or replace function public.app_list_tests(p_key text) returns setof jsonb
language plpgsql security definer set search_path = '' as $$
begin
  perform private.check_app_key(p_key);
  return query
    select t.content from public.tests t
    where t.is_published
    order by t.module, t.sort_order, t.id;
end;
$$;

create or replace function public.app_upsert_test(p_key text, p_test jsonb) returns void
language plpgsql security definer set search_path = '' as $$
begin
  perform private.check_app_key(p_key);
  insert into public.tests (id, module, variant, title, sort_order, is_published, content)
  values (
    p_test->>'id', p_test->>'module', coalesce(p_test->>'variant', 'academic'), p_test->>'title',
    coalesce((p_test->>'sortOrder')::int, 999), true, p_test
  )
  on conflict (id) do update set
    module = excluded.module, variant = excluded.variant, title = excluded.title,
    sort_order = excluded.sort_order, is_published = true, content = excluded.content;
end;
$$;

create or replace function public.app_save_reading_attempt(p_key text, p_row jsonb) returns bigint
language plpgsql security definer set search_path = '' as $$
declare v_id bigint;
begin
  perform private.check_app_key(p_key);
  insert into public.reading_attempts (test_id, client_id, user_id, candidate_name, mode, raw_score,
    total_questions, band_score, time_spent_seconds, answers, breakdown)
  values (
    p_row->>'test_id', nullif(p_row->>'client_id', '')::uuid, nullif(p_row->>'user_id', '')::uuid,
    left(p_row->>'candidate_name', 80), p_row->>'mode', (p_row->>'raw_score')::int, (p_row->>'total_questions')::int,
    (p_row->>'band_score')::numeric, (p_row->>'time_spent_seconds')::int, p_row->'answers', p_row->'breakdown'
  )
  returning id into v_id;
  return v_id;
end;
$$;

create or replace function public.app_save_listening_attempt(p_key text, p_row jsonb) returns bigint
language plpgsql security definer set search_path = '' as $$
declare v_id bigint;
begin
  perform private.check_app_key(p_key);
  insert into public.listening_attempts (test_id, client_id, user_id, candidate_name, mode, raw_score,
    total_questions, band_score, time_spent_seconds, answers, breakdown)
  values (
    p_row->>'test_id', nullif(p_row->>'client_id', '')::uuid, nullif(p_row->>'user_id', '')::uuid,
    left(p_row->>'candidate_name', 80), p_row->>'mode', (p_row->>'raw_score')::int, (p_row->>'total_questions')::int,
    (p_row->>'band_score')::numeric, (p_row->>'time_spent_seconds')::int, p_row->'answers', p_row->'breakdown'
  )
  returning id into v_id;
  return v_id;
end;
$$;

create or replace function public.app_save_writing_submission(p_key text, p_row jsonb) returns bigint
language plpgsql security definer set search_path = '' as $$
declare v_id bigint;
begin
  perform private.check_app_key(p_key);
  insert into public.writing_submissions (test_id, client_id, user_id, candidate_name, task1_text, task2_text,
    task1_words, task2_words, time_spent_seconds, analysis, assessment, overall_band)
  values (
    p_row->>'test_id', nullif(p_row->>'client_id', '')::uuid, nullif(p_row->>'user_id', '')::uuid,
    left(p_row->>'candidate_name', 80), p_row->>'task1_text', p_row->>'task2_text', (p_row->>'task1_words')::int,
    (p_row->>'task2_words')::int, (p_row->>'time_spent_seconds')::int,
    p_row->'analysis', nullif(p_row->'assessment', 'null'::jsonb), (p_row->>'overall_band')::numeric
  )
  returning id into v_id;
  return v_id;
end;
$$;

create or replace function public.app_history(p_key text, p_client uuid, p_limit int default 20) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare v_limit int := least(greatest(coalesce(p_limit, 20), 1), 50);
begin
  perform private.check_app_key(p_key);
  return jsonb_build_object(
    'reading', coalesce((
      select jsonb_agg(r) from (
        select a.id, a.test_id, a.raw_score, a.total_questions, a.band_score,
               a.time_spent_seconds, a.mode, a.created_at
        from public.reading_attempts a
        where a.client_id = p_client
        order by a.created_at desc limit v_limit
      ) r), '[]'::jsonb),
    'listening', coalesce((
      select jsonb_agg(l) from (
        select a.id, a.test_id, a.raw_score, a.total_questions, a.band_score,
               a.time_spent_seconds, a.mode, a.created_at
        from public.listening_attempts a
        where a.client_id = p_client
        order by a.created_at desc limit v_limit
      ) l), '[]'::jsonb),
    'writing', coalesce((
      select jsonb_agg(w) from (
        select s.id, s.test_id, s.task1_words, s.task2_words, s.overall_band,
               s.time_spent_seconds, s.created_at
        from public.writing_submissions s
        where s.client_id = p_client
        order by s.created_at desc limit v_limit
      ) w), '[]'::jsonb)
  );
end;
$$;

create or replace function public.app_stats(p_key text) returns jsonb
language plpgsql security definer set search_path = '' as $$
begin
  perform private.check_app_key(p_key);
  return jsonb_build_object(
    'readingAttempts', (select count(*) from public.reading_attempts),
    'readingAvgBand', (select round(avg(band_score), 2) from public.reading_attempts),
    'listeningAttempts', (select count(*) from public.listening_attempts),
    'listeningAvgBand', (select round(avg(band_score), 2) from public.listening_attempts),
    'writingSubmissions', (select count(*) from public.writing_submissions),
    'writingAvgBand', (select round(avg(overall_band), 2) from public.writing_submissions)
  );
end;
$$;

-- Only these functions are callable with the public key (and each checks the secret).
revoke all on function public.app_list_tests(text) from public, anon, authenticated;
revoke all on function public.app_upsert_test(text, jsonb) from public, anon, authenticated;
revoke all on function public.app_save_reading_attempt(text, jsonb) from public, anon, authenticated;
revoke all on function public.app_save_listening_attempt(text, jsonb) from public, anon, authenticated;
revoke all on function public.app_save_writing_submission(text, jsonb) from public, anon, authenticated;
revoke all on function public.app_history(text, uuid, int) from public, anon, authenticated;
revoke all on function public.app_stats(text) from public, anon, authenticated;
grant execute on function public.app_list_tests(text) to anon, service_role;
grant execute on function public.app_upsert_test(text, jsonb) to anon, service_role;
grant execute on function public.app_save_reading_attempt(text, jsonb) to anon, service_role;
grant execute on function public.app_save_listening_attempt(text, jsonb) to anon, service_role;
grant execute on function public.app_save_writing_submission(text, jsonb) to anon, service_role;
grant execute on function public.app_history(text, uuid, int) to anon, service_role;
grant execute on function public.app_stats(text) to anon, service_role;

-- ============================================================================
-- Accounts, the monthly plan, payments and examiner checks
--
-- The server reads and writes these tables through the normal REST endpoints.
-- Each request carries the server secret in an `x-app-key` header, and the
-- Row Level Security policies below only let such requests through. Requests
-- with just the public key see nothing.
-- ============================================================================

create or replace function private.request_has_app_key() returns boolean
language plpgsql stable security definer set search_path = '' as $$
declare v_key text;
begin
  v_key := nullif(current_setting('request.headers', true), '')::json->>'x-app-key';
  if v_key is null or length(v_key) < 32 then
    return false;
  end if;
  return exists (
    select 1 from private.app_secrets s
    where s.name = 'server'
      and s.secret_hash = encode(sha256(convert_to(v_key, 'UTF8')), 'hex')
  );
end;
$$;
revoke all on function private.request_has_app_key() from public;
grant usage on schema private to anon;
grant execute on function private.request_has_app_key() to anon;

create table if not exists public.profiles (
  id             uuid primary key,
  email          text not null unique,
  name           text,
  role           text not null default 'student' check (role in ('student', 'examiner', 'admin')),
  created_at     timestamptz not null default now(),
  last_login_at  timestamptz
);

create table if not exists public.orders (
  id             bigint generated always as identity primary key,
  user_id        uuid not null references public.profiles(id),
  kind           text not null check (kind in ('plan', 'writing_check', 'speaking_check')),
  amount         integer not null check (amount > 0),
  status         text not null default 'pending'
                 check (status in ('pending', 'awaiting_confirmation', 'paid', 'cancelled', 'refunded')),
  provider       text check (provider in ('payme', 'click', 'manual', 'admin')),
  examiner_id    uuid references public.profiles(id),
  submission_id  bigint,
  note           text,
  created_at     timestamptz not null default now(),
  paid_at        timestamptz,
  cancelled_at   timestamptz
);
create index if not exists orders_user_idx on public.orders (user_id, created_at desc);
create index if not exists orders_status_idx on public.orders (status, created_at desc);

create table if not exists public.subscription_periods (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references public.profiles(id),
  order_id    bigint unique references public.orders(id),
  starts_at   timestamptz not null,
  ends_at     timestamptz not null,
  source      text not null check (source in ('payment', 'admin')),
  note        text,
  created_at  timestamptz not null default now()
);
create index if not exists subscription_periods_user_idx on public.subscription_periods (user_id, ends_at desc);

-- Payme Merchant API transactions (amounts in tiyin, times in milliseconds).
create table if not exists public.payme_transactions (
  id            text primary key,
  order_id      bigint not null references public.orders(id),
  amount        bigint not null,
  state         smallint not null,
  payme_time    bigint not null,
  create_time   bigint not null,
  perform_time  bigint not null default 0,
  cancel_time   bigint not null default 0,
  reason        smallint
);
create index if not exists payme_transactions_order_idx on public.payme_transactions (order_id);
create index if not exists payme_transactions_time_idx on public.payme_transactions (payme_time);

-- Click SHOP API transactions.
create table if not exists public.click_transactions (
  id              bigint generated always as identity primary key,
  click_trans_id  bigint not null unique,
  order_id        bigint not null references public.orders(id),
  amount          numeric(14, 2) not null,
  status          text not null check (status in ('prepared', 'completed', 'cancelled')),
  created_at      timestamptz not null default now(),
  completed_at    timestamptz
);

create table if not exists public.examiners (
  user_id        uuid primary key references public.profiles(id),
  display_name   text not null,
  headline       text,
  bio            text,
  does_writing   boolean not null default true,
  does_speaking  boolean not null default true,
  accepting      boolean not null default true,
  approved       boolean not null default false,
  created_at     timestamptz not null default now()
);

create table if not exists public.checks (
  id             bigint generated always as identity primary key,
  order_id       bigint not null unique references public.orders(id),
  kind           text not null check (kind in ('writing', 'speaking')),
  student_id     uuid not null references public.profiles(id),
  examiner_id    uuid not null references public.profiles(id),
  submission_id  bigint not null,
  status         text not null default 'waiting' check (status in ('waiting', 'in_progress', 'completed', 'cancelled')),
  result         jsonb,
  overall_band   numeric(2, 1),
  created_at     timestamptz not null default now(),
  started_at     timestamptz,
  completed_at   timestamptz,
  rating         smallint check (rating between 1 and 5),
  review         text,
  reviewed_at    timestamptz
);
create index if not exists checks_examiner_idx on public.checks (examiner_id, status, created_at);
create index if not exists checks_student_idx on public.checks (student_id, created_at desc);

-- Attempts remember the signed-in user (null for anonymous practice).
alter table public.reading_attempts    add column if not exists user_id uuid;
alter table public.listening_attempts  add column if not exists user_id uuid;
alter table public.writing_submissions add column if not exists user_id uuid;
create index if not exists reading_attempts_user_idx    on public.reading_attempts (user_id, created_at desc);
create index if not exists listening_attempts_user_idx  on public.listening_attempts (user_id, created_at desc);
create index if not exists writing_submissions_user_idx on public.writing_submissions (user_id, created_at desc);

do $$
declare t text;
begin
  foreach t in array array['profiles', 'orders', 'subscription_periods', 'payme_transactions', 'click_transactions',
                           'examiners', 'checks', 'reading_attempts', 'listening_attempts', 'writing_submissions']
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists server_access on public.%I', t);
    execute format('create policy server_access on public.%I for all to anon using ((select private.request_has_app_key())) with check ((select private.request_has_app_key()))', t);
  end loop;
end $$;

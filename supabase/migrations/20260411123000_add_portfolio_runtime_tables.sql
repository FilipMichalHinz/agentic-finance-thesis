create table if not exists public.portfolio_runs (
    run_id text primary key,
    config_name text,
    universe_name text not null default 'DJIA30',
    base_currency text not null default 'USD',
    initial_cash numeric,
    metadata jsonb not null default '{}'::jsonb,
    started_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now()
);

create table if not exists public.portfolio_state (
    run_id text primary key references public.portfolio_runs(run_id) on delete cascade,
    as_of_date date not null,
    cash numeric not null,
    gross_market_value numeric not null default 0,
    total_value numeric not null,
    positions jsonb not null default '[]'::jsonb,
    recent_actions jsonb not null default '[]'::jsonb,
    metrics jsonb not null default '{}'::jsonb,
    updated_at timestamp with time zone not null default now()
);

create table if not exists public.portfolio_history (
    id uuid primary key default gen_random_uuid(),
    run_id text not null references public.portfolio_runs(run_id) on delete cascade,
    trade_date date not null,
    as_of_timestamp timestamp with time zone,
    cash numeric not null,
    gross_market_value numeric not null default 0,
    total_value numeric not null,
    positions jsonb not null default '[]'::jsonb,
    recent_actions jsonb not null default '[]'::jsonb,
    metrics jsonb not null default '{}'::jsonb,
    created_at timestamp with time zone not null default now(),
    unique (run_id, trade_date)
);

create table if not exists public.portfolio_decisions (
    id uuid primary key default gen_random_uuid(),
    run_id text not null references public.portfolio_runs(run_id) on delete cascade,
    decision_date date not null,
    execution_date date,
    as_of_timestamp timestamp with time zone,
    target_weights jsonb not null default '{}'::jsonb,
    action_plan jsonb not null default '[]'::jsonb,
    rationale text,
    analyst_inputs jsonb not null default '{}'::jsonb,
    compliance_summary jsonb not null default '{}'::jsonb,
    created_at timestamp with time zone not null default now(),
    unique (run_id, decision_date)
);

create index if not exists portfolio_history_run_trade_date_idx
    on public.portfolio_history (run_id, trade_date desc);

create index if not exists portfolio_decisions_run_decision_date_idx
    on public.portfolio_decisions (run_id, decision_date desc);

alter table public.portfolio_runs enable row level security;
alter table public.portfolio_state enable row level security;
alter table public.portfolio_history enable row level security;
alter table public.portfolio_decisions enable row level security;

grant all on table public.portfolio_runs to anon;
grant all on table public.portfolio_runs to authenticated;
grant all on table public.portfolio_runs to service_role;

grant all on table public.portfolio_state to anon;
grant all on table public.portfolio_state to authenticated;
grant all on table public.portfolio_state to service_role;

grant all on table public.portfolio_history to anon;
grant all on table public.portfolio_history to authenticated;
grant all on table public.portfolio_history to service_role;

grant all on table public.portfolio_decisions to anon;
grant all on table public.portfolio_decisions to authenticated;
grant all on table public.portfolio_decisions to service_role;

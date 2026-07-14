create table if not exists workout_logs (
    id bigint generated always as identity primary key,
    telegram_user_id bigint not null,
    exercise text not null,
    sets int,
    reps int,
    weight_kg numeric,
    duration_min numeric,
    distance_km numeric,
    raw_text text not null,
    logged_at timestamptz not null default now()
);

create index if not exists workout_logs_user_exercise_idx
    on workout_logs (telegram_user_id, exercise, logged_at);

create table if not exists body_weight_logs (
    id bigint generated always as identity primary key,
    telegram_user_id bigint not null,
    weight_kg numeric not null,
    raw_text text not null,
    logged_at timestamptz not null default now()
);

create index if not exists body_weight_logs_user_idx
    on body_weight_logs (telegram_user_id, logged_at);

create table if not exists bot_state (
    key text primary key,
    value text not null
);

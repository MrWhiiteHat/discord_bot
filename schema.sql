CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    xp INT DEFAULT 0,
    level INT DEFAULT 0,
    coins INT DEFAULT 0,
    faction TEXT DEFAULT NULL,
    last_daily TIMESTAMP,
    message_count INT DEFAULT 0,
    last_attack TIMESTAMP,
    special_power_cooldown TIMESTAMP,
    active_power TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS boss (
    boss_id SERIAL PRIMARY KEY,
    boss_name TEXT,
    hp INT,
    max_hp INT,
    shield_active BOOLEAN DEFAULT false,
    rage_mode BOOLEAN DEFAULT false,
    defense_mode TEXT DEFAULT 'Normal',
    phase INT DEFAULT 1,
    last_activity TIMESTAMP,
    attacks_taken INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS boss_logs (
    log_id SERIAL PRIMARY KEY,
    user_id BIGINT,
    attack_type TEXT,
    damage INT,
    timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shop (
    item_id SERIAL PRIMARY KEY,
    name TEXT,
    price INT,
    role_id BIGINT
);

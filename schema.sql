CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    xp INT DEFAULT 0,
    level INT DEFAULT 0,
    coins INT DEFAULT 0,
    faction TEXT DEFAULT NULL,
    last_daily TIMESTAMP,
    message_count INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS boss (
    boss_id SERIAL PRIMARY KEY,
    boss_name TEXT,
    hp INT,
    max_hp INT
);

CREATE TABLE IF NOT EXISTS shop (
    item_id SERIAL PRIMARY KEY,
    name TEXT,
    price INT,
    role_id BIGINT
);

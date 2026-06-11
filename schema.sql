CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL,
    api_key TEXT
);

CREATE TABLE IF NOT EXISTS ingredients (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    amount NUMERIC,
    metric TEXT,
    expiry_date DATE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
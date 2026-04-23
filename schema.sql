PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER,
    user_id_hash TEXT NOT NULL UNIQUE,
    language TEXT NOT NULL DEFAULT 'en',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS charities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_ar TEXT NOT NULL,
    name_en TEXT NOT NULL,
    category TEXT NOT NULL,
    website TEXT NOT NULL,
    wallet_address TEXT,
    verification_status TEXT NOT NULL,
    added_date TEXT NOT NULL,
    added_by TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS donations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id_hash TEXT NOT NULL,
    charity_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL,
    campaign_tag TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (charity_id) REFERENCES charities(id)
);

CREATE TABLE IF NOT EXISTS ledger (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    type TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL,
    from_user_hash TEXT,
    to_charity_id INTEGER,
    campaign_tag TEXT,
    notes TEXT,
    previous_signature TEXT,
    signature TEXT NOT NULL,
    FOREIGN KEY (to_charity_id) REFERENCES charities(id)
);

CREATE TABLE IF NOT EXISTS polls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    options_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    closes_at TEXT
);

CREATE TABLE IF NOT EXISTS poll_votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poll_id INTEGER NOT NULL,
    user_id_hash TEXT NOT NULL,
    option_index INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (poll_id, user_id_hash),
    FOREIGN KEY (poll_id) REFERENCES polls(id)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT,
    details TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_donations_user_id_hash ON donations(user_id_hash);
CREATE INDEX IF NOT EXISTS idx_donations_charity_id ON donations(charity_id);
CREATE INDEX IF NOT EXISTS idx_ledger_type ON ledger(type);
CREATE INDEX IF NOT EXISTS idx_ledger_to_charity_id ON ledger(to_charity_id);
CREATE INDEX IF NOT EXISTS idx_poll_votes_poll_id ON poll_votes(poll_id);

CREATE TABLE IF NOT EXISTS analysis_sessions (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    filename    TEXT NOT NULL,
    xml_hash    TEXT NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    summary     TEXT
);

CREATE TABLE IF NOT EXISTS rule_findings (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    rule_id         TEXT NOT NULL,
    rule_name       TEXT NOT NULL,
    severity        TEXT NOT NULL,
    shape_id        TEXT,
    shape_label     TEXT,
    description     TEXT NOT NULL,
    recommendation  TEXT NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS message_embeddings (
    id          TEXT PRIMARY KEY REFERENCES chat_messages(id) ON DELETE CASCADE,
    embedding   BLOB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_findings_session ON rule_findings(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_session_hash ON analysis_sessions(xml_hash);

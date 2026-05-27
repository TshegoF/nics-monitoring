-- ============================================================
-- NICS Time Monitoring - Feature update
-- Safe to run on a fresh Supabase project or an existing one
-- ============================================================

CREATE TABLE IF NOT EXISTS attendance (
    id            BIGSERIAL PRIMARY KEY,
    date          TEXT NOT NULL,
    agent         TEXT NOT NULL,
    book          TEXT DEFAULT '',
    clock_in      TEXT DEFAULT '',
    tea_start     TEXT DEFAULT '',
    tea_end       TEXT DEFAULT '',
    lunch_start   TEXT DEFAULT '',
    lunch_end     TEXT DEFAULT '',
    clock_out     TEXT DEFAULT '',
    late_minutes  INTEGER DEFAULT 0,
    tea_extra     INTEGER DEFAULT 0,
    lunch_extra   INTEGER DEFAULT 0,
    new_knockoff  TEXT DEFAULT '',
    status        TEXT DEFAULT 'Dialing',
    reason        TEXT DEFAULT '',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agents (
    username      TEXT PRIMARY KEY,
    display_name  TEXT DEFAULT '',
    pin           TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS books (
    book_name     TEXT PRIMARY KEY,
    supervisors   TEXT DEFAULT '[]',
    agents        TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS settings (
    key           TEXT PRIMARY KEY,
    value         TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS receptionists (
    username      TEXT PRIMARY KEY,
    display_name  TEXT DEFAULT '',
    pin           TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id           BIGSERIAL PRIMARY KEY,
    actor        TEXT DEFAULT '',
    action       TEXT NOT NULL,
    target_user  TEXT DEFAULT '',
    details      TEXT DEFAULT '',
    ip_address   TEXT DEFAULT '',
    device_id    TEXT DEFAULT '',
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trusted_devices (
    id             BIGSERIAL PRIMARY KEY,
    username       TEXT NOT NULL,
    device_id      TEXT NOT NULL,
    label          TEXT DEFAULT '',
    approved       BOOLEAN DEFAULT FALSE,
    approved_by    TEXT DEFAULT '',
    approved_at    TIMESTAMPTZ,
    first_seen_at  TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(username, device_id)
);

ALTER TABLE agents ADD COLUMN IF NOT EXISTS pin TEXT DEFAULT '';

ALTER TABLE attendance ADD COLUMN IF NOT EXISTS bathroom_start   TEXT DEFAULT '';
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS bathroom_end     TEXT DEFAULT '';
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS bathroom_extra   INTEGER DEFAULT 0;
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS bathroom_reason  TEXT DEFAULT '';
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS reception_start  TEXT DEFAULT '';
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS reception_end    TEXT DEFAULT '';
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS reception_reason TEXT DEFAULT '';
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS meeting_start    TEXT DEFAULT '';
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS meeting_end      TEXT DEFAULT '';
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS meeting_extra    INTEGER DEFAULT 0;
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS meeting_reason   TEXT DEFAULT '';
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS worked_minutes   INTEGER DEFAULT 0;

INSERT INTO receptionists (username, display_name, pin) VALUES
    ('mramahlo', 'Maggy Ramahlo', '0000')
ON CONFLICT (username) DO UPDATE SET display_name = EXCLUDED.display_name;

INSERT INTO settings (key, value) VALUES
    ('admin_password', 'Admin@2025')
ON CONFLICT (key) DO NOTHING;

INSERT INTO settings (key, value) VALUES
    ('supervisor_password', 'nics1068')
ON CONFLICT (key) DO NOTHING;

INSERT INTO settings (key, value) VALUES ('extra_admins', 'edgart,mabokop,caleb')
ON CONFLICT (key) DO UPDATE SET value = 'edgart,mabokop,caleb';

ALTER TABLE attendance DISABLE ROW LEVEL SECURITY;
ALTER TABLE agents     DISABLE ROW LEVEL SECURITY;
ALTER TABLE books      DISABLE ROW LEVEL SECURITY;
ALTER TABLE settings   DISABLE ROW LEVEL SECURITY;
ALTER TABLE receptionists DISABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE trusted_devices DISABLE ROW LEVEL SECURITY;

SELECT 'Feature update complete: PINs, receptionists, bathroom, meeting, working hours, audit logs, and trusted devices ready.' AS result;

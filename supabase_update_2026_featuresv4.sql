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

CREATE TABLE IF NOT EXISTS correction_requests (
    id              BIGSERIAL PRIMARY KEY,
    username        TEXT NOT NULL,
    date            TEXT NOT NULL,
    request_type    TEXT NOT NULL,
    current_value   TEXT DEFAULT '',
    requested_value TEXT DEFAULT '',
    reason          TEXT DEFAULT '',
    status          TEXT DEFAULT 'Pending',
    reviewer        TEXT DEFAULT '',
    review_note     TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS daily_signoffs (
    id          BIGSERIAL PRIMARY KEY,
    date        TEXT NOT NULL,
    supervisor  TEXT NOT NULL,
    book        TEXT NOT NULL,
    note        TEXT DEFAULT '',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, supervisor, book)
);

CREATE TABLE IF NOT EXISTS calendar_exceptions (
    id              BIGSERIAL PRIMARY KEY,
    date            TEXT NOT NULL,
    title           TEXT NOT NULL,
    exception_type  TEXT DEFAULT '',
    notes           TEXT DEFAULT '',
    created_by      TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS supervisor_notes (
    id          BIGSERIAL PRIMARY KEY,
    date        TEXT NOT NULL,
    agent       TEXT NOT NULL,
    supervisor  TEXT NOT NULL,
    note        TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications (
    id           BIGSERIAL PRIMARY KEY,
    username     TEXT DEFAULT '',
    role_target  TEXT DEFAULT '',
    message      TEXT NOT NULL,
    severity     TEXT DEFAULT 'Info',
    is_read      BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMPTZ DEFAULT NOW()
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

INSERT INTO settings (key, value) VALUES
    ('work_start_time', '08:00'),
    ('work_end_time', '16:30'),
    ('tea_limit_minutes', '15'),
    ('lunch_limit_minutes', '60'),
    ('bathroom_limit_minutes', '5'),
    ('reception_limit_minutes', '60'),
    ('meeting_limit_minutes', '30'),
    ('auto_clockout_warning_time', '17:00'),
    ('agent_reception_reasons', 'Moved to reception'),
    ('late_reasons', 'Traffic delay
Public transport delay
Load shedding or power outage
Family responsibility
Medical appointment
School drop-off delay
Car trouble
Weather-related delay
Security/access delay
System or network issue'),
    ('tea_reasons', 'Work-related delay
Customer call ran over
System issue
Supervisor discussion
Queue pressure
Medical reason
Bathroom emergency
Reception query
HR query
Other approved workplace reason'),
    ('lunch_reasons', 'Work-related delay
Customer call ran over
System issue
Supervisor discussion
Queue pressure
Medical reason
Reception query
HR query
Meeting ran over
Other approved workplace reason'),
    ('bathroom_reasons', 'Bathroom emergency
Medical reason
Queue handover delay
Supervisor approved delay
Other approved workplace reason'),
    ('reception_reasons', 'At reception
Moved to reception
Visitor query
Document collection
HR/admin query
Management request
Supervisor approved reception matter'),
    ('meeting_reasons', 'Team meeting
Supervisor meeting
Training session
HR meeting
Management meeting
Performance discussion
Client escalation meeting
System/process briefing'),
    ('workplace_reasons', 'Customer call ran over
System issue
Network issue
Supervisor discussion
Management request
HR/admin query
Training session
Medical reason
Queue pressure
Approved operational matter')
ON CONFLICT (key) DO NOTHING;

ALTER TABLE attendance DISABLE ROW LEVEL SECURITY;
ALTER TABLE agents     DISABLE ROW LEVEL SECURITY;
ALTER TABLE books      DISABLE ROW LEVEL SECURITY;
ALTER TABLE settings   DISABLE ROW LEVEL SECURITY;
ALTER TABLE receptionists DISABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE trusted_devices DISABLE ROW LEVEL SECURITY;
ALTER TABLE correction_requests DISABLE ROW LEVEL SECURITY;
ALTER TABLE daily_signoffs DISABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_exceptions DISABLE ROW LEVEL SECURITY;
ALTER TABLE supervisor_notes DISABLE ROW LEVEL SECURITY;
ALTER TABLE notifications DISABLE ROW LEVEL SECURITY;

SELECT 'Feature update complete: top-tier settings, corrections, sign-offs, exceptions, notes, notifications, health, and backup tables ready.' AS result;

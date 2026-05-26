
-- ============================================================
-- NICS Employee Time Monitoring System
-- Run this ONCE in Supabase SQL Editor to set up all tables
-- ============================================================

-- 1. ATTENDANCE TABLE
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

-- 2. AGENTS TABLE
CREATE TABLE IF NOT EXISTS agents (
    username      TEXT PRIMARY KEY,
    display_name  TEXT DEFAULT ''
);

-- 3. BOOKS TABLE
CREATE TABLE IF NOT EXISTS books (
    book_name     TEXT PRIMARY KEY,
    supervisors   TEXT DEFAULT '[]',
    agents        TEXT DEFAULT '[]'
);

-- 4. SETTINGS TABLE (for passwords)
CREATE TABLE IF NOT EXISTS settings (
    key           TEXT PRIMARY KEY,
    value         TEXT DEFAULT ''
);

-- 5. Default settings
INSERT INTO settings (key, value) VALUES ('admin_password', 'Admin@2025')
    ON CONFLICT (key) DO NOTHING;
INSERT INTO settings (key, value) VALUES ('supervisor_password', 'nics1068')
    ON CONFLICT (key) DO NOTHING;

-- 6. Default agents
INSERT INTO agents (username, display_name) VALUES
    ('cyounis',      'C Younis'),
    ('maggyt',       'Maggy T'),
    ('sibongilem',   'Sibongile M'),
    ('moiponem',     'Moipone M'),
    ('mpeggy',       'M Peggy'),
    ('msharon',      'M Sharon'),
    ('mzanele',      'M Zanele'),
    ('puseletsoh',   'Puseletsoh'),
    ('ntomikayisem', 'Ntomikayise M'),
    ('dimakatsop',   'Dimakatso P'),
    ('carolins',     'Carolin S'),
    ('phindilev',    'Phindile V'),
    ('sibusisiwes',  'Sibusiwe S'),
    ('preciousm',    'Precious M'),
    ('basetsanan',   'Basetsana N'),
    ('monamat',      'Monama T'),
    ('pearlm',       'Pearl M'),
    ('lesegos',      'Lesego S'),
    ('tshepisod',    'Tsepiso D'),
    ('gabotsalwep',  'Gabotsalwe P'),
    ('tsholofelom',  'Tsholofelom'),
    ('sherlym',      'Sherly M'),
    ('pontshom',     'Pontsho M'),
    ('abegailm',     'Abegail M'),
    ('fikilet',      'Fikile T'),
    ('koketsom',     'Koketso M'),
    ('boitshokom',   'Boitshoko M'),
    ('bathandey',    'Bathande Y'),
    ('simoned',      'Simone D'),
    ('busisiwes',    'Busisiwe S'),
    ('Nthabisengm',  'Nthabiseng M'),
    ('nokwandan',    'Nokwanda Ntuli'),
    ('leboganqm',    'Lebogang Msweli')
ON CONFLICT (username) DO NOTHING;

-- 7. Default book
INSERT INTO books (book_name, supervisors, agents) VALUES (
    'Unassigned',
    '[]',
    '["cyounis","maggyt","sibongilem","moiponem","mpeggy","msharon","mzanele","puseletsoh","ntomikayisem","dimakatsop","carolins","phindilev","sibusisiwes","preciousm","basetsanan","monamat","pearlm","lesegos","tshepisod","gabotsalwep","tsholofelom","sherlym","pontshom","abegailm","fikilet","koketsom","boitshokom","bathandey","simoned","busisiwes","Nthabisengm","nokwandan","leboganqm"]'
) ON CONFLICT (book_name) DO NOTHING;

-- 8. Enable Row Level Security (RLS) - disable for simplicity with anon key
ALTER TABLE attendance DISABLE ROW LEVEL SECURITY;
ALTER TABLE agents     DISABLE ROW LEVEL SECURITY;
ALTER TABLE books      DISABLE ROW LEVEL SECURITY;
ALTER TABLE settings   DISABLE ROW LEVEL SECURITY;

-- Done! All tables are ready.
SELECT 'Setup complete! Tables created: attendance, agents, books, settings' AS result;

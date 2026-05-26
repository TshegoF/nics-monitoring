-- ============================================================
-- NICS Time Monitoring System — Database Update v2
-- Run this in Supabase SQL Editor
-- ============================================================

-- 1. Add new columns to attendance table
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS bathroom_start  TEXT DEFAULT '';
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS bathroom_end    TEXT DEFAULT '';
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS bathroom_extra  INTEGER DEFAULT 0;
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS meeting_start   TEXT DEFAULT '';
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS meeting_end     TEXT DEFAULT '';
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS meeting_extra   INTEGER DEFAULT 0;
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS reception_start TEXT DEFAULT '';
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS reception_end   TEXT DEFAULT '';
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS worked_minutes  INTEGER DEFAULT 0;

-- 2. Add PIN column to agents table
ALTER TABLE agents ADD COLUMN IF NOT EXISTS pin TEXT DEFAULT '';

-- 3. Add receptionists table
CREATE TABLE IF NOT EXISTS receptionists (
    username     TEXT PRIMARY KEY,
    display_name TEXT DEFAULT '',
    pin          TEXT DEFAULT ''
);

-- 4. Seed Maggy Ramahlo as receptionist
INSERT INTO receptionists (username, display_name, pin)
VALUES ('mramahlo', 'Maggy Ramahlo', '0000')
ON CONFLICT (username) DO NOTHING;

-- 5. Add Caleb as admin in settings
INSERT INTO settings (key, value) VALUES ('extra_admins', 'caleb')
ON CONFLICT (key) DO UPDATE SET value = 'edgart,mabokop,caleb';

-- 6. Disable RLS on new table
ALTER TABLE receptionists DISABLE ROW LEVEL SECURITY;

SELECT 'Database update v2 complete!' AS result;

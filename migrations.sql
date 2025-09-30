-- Add role to user table (idempotent if already added)
ALTER TABLE user ADD COLUMN role TEXT DEFAULT 'member';

-- Optional: add is_active to enable/disable login
ALTER TABLE user ADD COLUMN is_active INTEGER DEFAULT 1;

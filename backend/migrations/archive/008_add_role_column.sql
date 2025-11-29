
-- Migration: Add role column back to users and sync with role_id

-- 1. Add the role column (string) back to users table
ALTER TABLE users ADD COLUMN role VARCHAR(20);

-- 2. Populate role column based on existing role_id
UPDATE users u
SET role = r.name
FROM roles r
WHERE r.id = u.role_id;

-- 3. Ensure future inserts/updates set both role and role_id (handled in application code)

-- 4. Add a NOT NULL constraint if desired (optional, after data backfill)
-- ALTER TABLE users ALTER COLUMN role SET NOT NULL;

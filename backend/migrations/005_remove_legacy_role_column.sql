-- Migration: Remove legacy role column from users table
-- This migration removes the string-based role field and relies solely on role_id

ALTER TABLE users DROP COLUMN IF EXISTS role;

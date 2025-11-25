-- Migration: Update existing users with 'member' role to 'field_agent'

-- Update users table - change 'member' to 'field_agent'
UPDATE users 
SET role = 'field_agent' 
WHERE role = 'member';

-- Update invitations table - change 'member' to 'field_agent'
UPDATE invitations 
SET role = 'field_agent' 
WHERE role = 'member';

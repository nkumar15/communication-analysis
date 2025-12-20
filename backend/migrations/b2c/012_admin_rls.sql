-- Migration: 012_admin_rls.sql
-- Purpose: Add platform admin bypass policies to key tables for verification/testing/admin tools.

-- Users
CREATE POLICY admin_all_users ON b2c.users
    USING (current_setting('app.is_platform_admin', true) = 'true');

-- Workspaces
CREATE POLICY admin_all_workspaces ON b2c.workspaces
    USING (current_setting('app.is_platform_admin', true) = 'true');

-- Workspace Members
CREATE POLICY admin_all_workspace_members ON b2c.workspace_members
    USING (current_setting('app.is_platform_admin', true) = 'true');

-- Workspace Invitations (if needed, though recipient/workspace policies usually cover it)
CREATE POLICY admin_all_workspace_invitations ON b2c.workspace_invitations
    USING (current_setting('app.is_platform_admin', true) = 'true');

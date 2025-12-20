-- ============================================================================
-- PLATFORM CORE SCHEMA
-- ============================================================================
-- Single-Tenant Platform Administration System
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS platform;

-- 1. PLATFORM TENANT (Singleton)
CREATE TABLE IF NOT EXISTS platform.platform_tenant (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL DEFAULT 'SaaS Platform',
    firebase_tenant_id VARCHAR(255) UNIQUE NOT NULL,
    oidc_provider_id VARCHAR(255),
    email_domain VARCHAR(255),
    support_email VARCHAR(255),
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

CREATE UNIQUE INDEX idx_platform_tenant_singleton ON platform.platform_tenant ((true));

-- 2. PLATFORM ROLES (System Level, No Tenant FK)
CREATE TABLE IF NOT EXISTS platform.platform_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

-- 3. PLATFORM USERS
CREATE TABLE IF NOT EXISTS platform.platform_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_tenant_id UUID REFERENCES platform.platform_tenant(id) ON DELETE CASCADE NOT NULL,
    platform_role_id UUID REFERENCES platform.platform_roles(id) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    firebase_uid VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true NOT NULL,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

CREATE OR REPLACE FUNCTION update_platform_users_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER platform_users_updated_at BEFORE UPDATE ON platform.platform_users FOR EACH ROW EXECUTE FUNCTION update_platform_users_updated_at();

-- 4. PLATFORM AUDIT LOG
CREATE TABLE IF NOT EXISTS platform.platform_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_tenant_id UUID REFERENCES platform.platform_tenant(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES platform.platform_users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

-- 5. PLATFORM AUTH PROVIDERS
CREATE TABLE IF NOT EXISTS platform.auth_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_tenant_id UUID NOT NULL REFERENCES platform.platform_tenant(id) ON DELETE CASCADE,
    provider_type VARCHAR(50) NOT NULL,
    provider_id VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    is_primary BOOLEAN DEFAULT false NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    config_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    CONSTRAINT unique_platform_provider_id UNIQUE(platform_tenant_id, provider_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_auth_providers_one_primary 
    ON platform.auth_providers(platform_tenant_id) 
    WHERE is_primary = true AND is_active = true;

CREATE OR REPLACE FUNCTION platform.update_auth_providers_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auth_providers_updated_at BEFORE UPDATE ON platform.auth_providers FOR EACH ROW EXECUTE FUNCTION platform.update_auth_providers_updated_at();

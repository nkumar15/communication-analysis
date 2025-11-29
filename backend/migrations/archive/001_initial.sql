-- Create tenants table
CREATE TABLE IF NOT EXISTS tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL UNIQUE,
    firebase_tenant_id VARCHAR(255) NOT NULL UNIQUE,
    oidc_provider_id VARCHAR(255) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    firebase_uid VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, email),
    UNIQUE(tenant_id, firebase_uid)
);

-- Create indexes
CREATE INDEX idx_tenants_domain ON tenants(domain);
CREATE INDEX idx_tenants_firebase_id ON tenants(firebase_tenant_id);
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_firebase_uid ON users(firebase_uid);

-- Insert sample tenant for testing
-- NOTE: You need to create this tenant in Firebase Identity Platform first
-- then use the tenant ID from Firebase here
-- INSERT INTO tenants (name, domain, firebase_tenant_id) VALUES (
--     'First Company',
--     'firstcompany.net',
--     'firstcompany-99oyw'
-- ) ON CONFLICT (domain) DO NOTHING;

-- Instructions:
-- 1. Go to Firebase Console → Authentication → Settings → Multi-tenancy
-- 2. Enable multi-tenancy and create a tenant
-- 3. Configure OIDC provider for the tenant in Firebase Console
-- 4. Copy the tenant ID and update the INSERT statement above

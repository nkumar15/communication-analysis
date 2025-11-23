-- Create invitations table for user invitation workflow
-- Separates invitation state from actual users

CREATE TABLE invitations (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    
    -- Invitation token for acceptance link
    invitation_token VARCHAR(64) UNIQUE NOT NULL,
    
    -- Metadata
    invited_by INTEGER REFERENCES users(id),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_tenant_email_invitation UNIQUE(tenant_id, email)
);

-- Indexes for performance
CREATE INDEX idx_invitations_tenant_id ON invitations(tenant_id);
CREATE INDEX idx_invitations_token ON invitations(invitation_token);
CREATE INDEX idx_invitations_email ON invitations(email);
CREATE INDEX idx_invitations_expires_at ON invitations(expires_at);

-- Comments
COMMENT ON TABLE invitations IS 'User invitations for tenant onboarding and team member invites';
COMMENT ON COLUMN invitations.invitation_token IS 'Secure token for invitation acceptance link';
COMMENT ON COLUMN invitations.invited_by IS 'User ID who sent the invitation (NULL for admin onboarding)';
COMMENT ON COLUMN invitations.accepted_at IS 'Timestamp when invitation was accepted (NULL if pending)';

import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import platformApiService from '../../../../core/api/platformClient';
import { formatDateTime } from '../../../../utils/dateUtils';
import { TenantDetailsSkeleton } from '../components/LoadingSkeletons';

function TenantDetailsPage() {
    const { tenantId } = useParams();
    const navigate = useNavigate();
    const [tenant, setTenant] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchTenantDetails();
    }, [tenantId]);

    const fetchTenantDetails = async () => {
        try {
            const data = await platformApiService.getTenantDetails(tenantId);
            setTenant(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleImpersonate = async () => {
        if (!window.confirm('Login as this tenant admin? You will be redirected to their dashboard.')) {
            return;
        }

        try {
            const response = await platformApiService.impersonateTenant(tenantId);
            localStorage.setItem('impersonating', 'true');
            localStorage.setItem('impersonation_token', response.token);
            localStorage.setItem('impersonation_tenant', response.tenant_name);
            window.location.href = '/dashboard';
        } catch (error) {
            alert('Failed to impersonate: ' + error.message);
        }
    };

    const handleDeactivate = async () => {
        if (!window.confirm('Are you sure you want to deactivate this tenant? Users will not be able to login.')) {
            return;
        }

        try {
            await platformApiService.deactivateTenant(tenantId);
            fetchTenantDetails(); // Refresh
        } catch (error) {
            alert('Failed to deactivate: ' + error.message);
        }
    };

    const handleResendInvite = async () => {
        try {
            await platformApiService.resendActivation(tenantId);
            alert('Activation email resent successfully!');
            fetchTenantDetails(); // Refresh
        } catch (error) {
            alert('Failed to resend invite: ' + error.message);
        }
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
        alert('Copied to clipboard!');
    };

    if (loading) {
        return <TenantDetailsSkeleton />;
    }

    if (error) {
        return (
            <div style={{ padding: '2rem', color: '#ef4444' }}>
                Error: {error}
                <br />
                <Link to="/platform/tenants" style={{ color: '#a78bfa', marginTop: '1rem', display: 'inline-block' }}>
                    &larr; Back to Tenants
                </Link>
            </div>
        );
    }

    if (!tenant) return null;

    const isActive = tenant.activation_status === 'active';

    return (
        <div>
            <div className="platform-page-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <Link to="/platform/tenants" style={{ color: '#9ca3af', textDecoration: 'none', fontSize: '1.5rem' }}>
                        &larr;
                    </Link>
                    <div>
                        <h1 className="platform-page-title" style={{ marginBottom: '0.25rem' }}>{tenant.name}</h1>
                        <div style={{ color: '#9ca3af', fontSize: '0.9rem' }}>{tenant.domain}</div>
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '0.75rem' }}>
                    {isActive ? (
                        <>
                            <button
                                className="platform-btn platform-btn-primary"
                                onClick={handleImpersonate}
                            >
                                Login As Admin
                            </button>
                            <button
                                className="platform-btn"
                                onClick={handleDeactivate}
                                style={{
                                    background: 'rgba(239, 68, 68, 0.2)',
                                    color: '#fca5a5',
                                    border: '1px solid rgba(239, 68, 68, 0.3)'
                                }}
                            >
                                Deactivate
                            </button>
                        </>
                    ) : (
                        <button
                            className="platform-btn"
                            onClick={handleResendInvite}
                            style={{
                                background: 'rgba(245, 158, 11, 0.2)',
                                color: '#fcd34d',
                                border: '1px solid rgba(245, 158, 11, 0.3)'
                            }}
                        >
                            Resend Activation Email
                        </button>
                    )}
                </div>
            </div>

            <div className="platform-stats-grid" style={{ marginBottom: '2rem' }}>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Status</div>
                    <div className="platform-stat-value" style={{
                        fontSize: '1.5rem',
                        color: isActive ? '#34d399' : '#fbbf24'
                    }}>
                        {tenant.activation_status}
                    </div>
                </div>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Total Users</div>
                    <div className="platform-stat-value">{tenant.user_count}</div>
                </div>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Total Teams</div>
                    <div className="platform-stat-value">{tenant.team_count}</div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem' }}>
                {/* Main Info */}
                <div className="platform-card">
                    <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', color: '#e5e7eb' }}>Tenant Information</h2>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                        <div>
                            <label style={{ display: 'block', color: '#9ca3af', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                                Tenant ID
                            </label>
                            <div style={{ fontFamily: 'monospace', color: '#e5e7eb' }}>{tenant.id}</div>
                        </div>
                        <div>
                            <label style={{ display: 'block', color: '#9ca3af', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                                Firebase Tenant ID
                            </label>
                            <div style={{ fontFamily: 'monospace', color: '#e5e7eb' }}>{tenant.firebase_tenant_id}</div>
                        </div>
                        <div>
                            <label style={{ display: 'block', color: '#9ca3af', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                                Created At
                            </label>
                            <div style={{ color: '#e5e7eb' }}>{formatDateTime(tenant.created_at)}</div>
                        </div>
                        <div>
                            <label style={{ display: 'block', color: '#9ca3af', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                                Last Updated
                            </label>
                            <div style={{ color: '#e5e7eb' }}>{formatDateTime(tenant.updated_at)}</div>
                        </div>
                    </div>

                    {!isActive && tenant.activation_token && (
                        <div style={{ marginTop: '2rem', padding: '1.5rem', background: 'rgba(245, 158, 11, 0.1)', borderRadius: '8px', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
                            <h3 style={{ fontSize: '1rem', color: '#fbbf24', marginBottom: '1rem' }}>Pending Activation</h3>

                            <div style={{ marginBottom: '1rem' }}>
                                <label style={{ display: 'block', color: '#fbbf24', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                                    Activation URL
                                </label>
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    <input
                                        type="text"
                                        readOnly
                                        value={`${window.location.origin}/activate/${tenant.activation_token}`}
                                        style={{
                                            flex: 1,
                                            background: 'rgba(0,0,0,0.2)',
                                            border: '1px solid rgba(255,255,255,0.1)',
                                            color: '#e5e7eb',
                                            padding: '0.5rem',
                                            borderRadius: '4px'
                                        }}
                                    />
                                    <button
                                        onClick={() => copyToClipboard(`${window.location.origin}/activate/${tenant.activation_token}`)}
                                        className="platform-btn"
                                    >
                                        Copy
                                    </button>
                                </div>
                            </div>

                            <div>
                                <label style={{ display: 'block', color: '#fbbf24', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                                    Expires At
                                </label>
                                <div style={{ color: '#e5e7eb' }}>{formatDateTime(tenant.activation_expires_at)}</div>
                            </div>
                        </div>
                    )}
                </div>

                {/* SSO Config */}
                <div className="platform-card">
                    <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', color: '#e5e7eb' }}>SSO Configuration</h2>

                    {tenant.auth_provider ? (
                        <div>
                            <div style={{ marginBottom: '1rem' }}>
                                <label style={{ display: 'block', color: '#9ca3af', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                                    Provider Type
                                </label>
                                <div style={{
                                    display: 'inline-block',
                                    padding: '0.25rem 0.75rem',
                                    background: '#4f46e5',
                                    color: 'white',
                                    borderRadius: '9999px',
                                    fontSize: '0.85rem',
                                    textTransform: 'uppercase'
                                }}>
                                    {tenant.auth_provider.provider_type}
                                </div>
                            </div>

                            <div style={{ marginBottom: '1rem' }}>
                                <label style={{ display: 'block', color: '#9ca3af', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                                    Provider ID
                                </label>
                                <div style={{ fontFamily: 'monospace', color: '#e5e7eb', wordBreak: 'break-all' }}>
                                    {tenant.auth_provider.provider_id}
                                </div>
                            </div>

                            <div style={{ marginBottom: '1rem' }}>
                                <label style={{ display: 'block', color: '#9ca3af', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                                    Status
                                </label>
                                <div style={{ color: tenant.auth_provider.is_active ? '#34d399' : '#9ca3af' }}>
                                    {tenant.auth_provider.is_active ? 'Active' : 'Inactive'}
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div style={{ color: '#9ca3af', fontStyle: 'italic' }}>
                            No SSO provider configured.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default TenantDetailsPage;

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import platformApiService from '../../../core/api/platformClient';
import { formatDateTime } from '../../../utils/dateUtils';
import CreateTenantModal from '../components/CreateTenantModal';

function TenantList() {
    const [tenants, setTenants] = useState([]);
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState(null);
    const [showModal, setShowModal] = useState(false);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [tenantsData, statsData] = await Promise.all([
                platformApiService.getTenants(),
                platformApiService.getStats()
            ]);
            setTenants(tenantsData);
            setStats(statsData);
        } catch (error) {
            console.error('Error fetching platform data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleImpersonate = async (tenantId) => {
        if (!window.confirm('Login as this tenant admin? You will be redirected to their dashboard.')) {
            return;
        }

        setLoading(true);
        try {
            const response = await platformApiService.impersonateTenant(tenantId);

            // Store impersonation state
            localStorage.setItem('impersonating', 'true');
            localStorage.setItem('impersonation_token', response.token);
            localStorage.setItem('impersonation_tenant', response.tenant_name);

            // Redirect to tenant dashboard
            window.location.href = '/dashboard';
        } catch (error) {
            alert('Failed to impersonate: ' + error.message);
            setLoading(false);
        }
    };

    const handleDeactivate = async (tenantId, tenantName) => {
        if (!window.confirm(`Are you sure you want to deactivate ${tenantName}? Users will not be able to login.`)) {
            return;
        }

        try {
            await platformApiService.deactivateTenant(tenantId);
            fetchData(); // Refresh list
        } catch (error) {
            alert('Failed to deactivate: ' + error.message);
        }
    };

    const handleResendInvite = async (tenantId) => {
        try {
            await platformApiService.resendActivation(tenantId);
            alert('Activation email resent successfully!');
        } catch (error) {
            alert('Failed to resend invite: ' + error.message);
        }
    };

    const getStatusBadge = (status) => {
        const styles = {
            active: { bg: '#d1fae5', color: '#065f46', border: '#10b981' },
            pending: { bg: '#fef3c7', color: '#92400e', border: '#f59e0b' },
            inactive: { bg: '#e5e7eb', color: '#374151', border: '#9ca3af' }
        };

        const style = styles[status] || styles.inactive;

        return (
            <span style={{
                padding: '0.35rem 0.85rem',
                borderRadius: '9999px',
                fontSize: '0.75rem',
                fontWeight: '600',
                backgroundColor: style.bg,
                color: style.color,
                border: `1px solid ${style.border}`,
                textTransform: 'capitalize'
            }}>
                {status}
            </span>
        );
    };

    if (loading && !tenants.length) {
        return (
            <div className="loading-container">
                <div className="spinner large"></div>
            </div>
        );
    }

    return (
        <div>
            <div className="platform-page-header">
                <h1 className="platform-page-title">Tenant Management</h1>
                <button
                    className="platform-btn platform-btn-primary"
                    onClick={() => setShowModal(true)}
                >
                    + Onboard Tenant
                </button>
            </div>

            {stats && (
                <div className="platform-stats-grid">
                    <div className="platform-stat-card">
                        <div className="platform-stat-label">Total Tenants</div>
                        <div className="platform-stat-value">{stats.total_tenants}</div>
                    </div>
                    <div className="platform-stat-card">
                        <div className="platform-stat-label">Active Tenants</div>
                        <div className="platform-stat-value">{stats.active_tenants}</div>
                    </div>
                    <div className="platform-stat-card">
                        <div className="platform-stat-label">Total Users</div>
                        <div className="platform-stat-value">{stats.total_users}</div>
                    </div>
                </div>
            )}

            <div className="platform-table-container">
                <table className="platform-table">
                    <thead>
                        <tr>
                            <th>Tenant Name</th>
                            <th>Domain</th>
                            <th>Status</th>
                            <th>Users</th>
                            <th>Created At</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tenants.map((tenant) => (
                            <tr key={tenant.id}>
                                <td>
                                    <Link
                                        to={`/platform/tenants/${tenant.id}`}
                                        style={{
                                            color: '#3b82f6',
                                            textDecoration: 'none',
                                            fontWeight: '600',
                                            transition: 'color 0.2s'
                                        }}
                                        onMouseEnter={(e) => e.target.style.color = '#2563eb'}
                                        onMouseLeave={(e) => e.target.style.color = '#3b82f6'}
                                    >
                                        {tenant.name}
                                    </Link>
                                </td>
                                <td>{tenant.domain}</td>
                                <td>{getStatusBadge(tenant.status)}</td>
                                <td>{tenant.user_count}</td>
                                <td>{formatDateTime(tenant.created_at)}</td>
                                <td>
                                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                                        <Link
                                            to={`/platform/tenants/${tenant.id}`}
                                            className="platform-btn"
                                            style={{
                                                fontSize: '0.75rem',
                                                padding: '0.3rem 0.6rem',
                                                background: 'rgba(255,255,255,0.1)',
                                                textDecoration: 'none',
                                                color: 'white'
                                            }}
                                        >
                                            Details
                                        </Link>

                                        {tenant.status === 'active' ? (
                                            <>
                                                <button
                                                    className="platform-btn platform-btn-primary"
                                                    onClick={() => handleImpersonate(tenant.id)}
                                                    style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}
                                                    title="Login as Admin"
                                                >
                                                    Login As
                                                </button>
                                                <button
                                                    className="platform-btn"
                                                    onClick={() => handleDeactivate(tenant.id, tenant.name)}
                                                    style={{
                                                        fontSize: '0.75rem',
                                                        padding: '0.3rem 0.6rem',
                                                        background: 'rgba(239, 68, 68, 0.2)',
                                                        color: '#fca5a5',
                                                        border: '1px solid rgba(239, 68, 68, 0.3)'
                                                    }}
                                                    title="Deactivate Tenant"
                                                >
                                                    Deactivate
                                                </button>
                                            </>
                                        ) : (
                                            <button
                                                className="platform-btn"
                                                onClick={() => handleResendInvite(tenant.id)}
                                                style={{
                                                    fontSize: '0.75rem',
                                                    padding: '0.3rem 0.6rem',
                                                    background: '#f97316',
                                                    color: 'white',
                                                    border: '1px solid #ea580c',
                                                    fontWeight: '500'
                                                }}
                                                title="Resend Activation Email"
                                            >
                                                📧 Resend Invite
                                            </button>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        ))}
                        {tenants.length === 0 && (
                            <tr>
                                <td colSpan="6" style={{ textAlign: 'center', padding: '2rem', color: '#9ca3af' }}>
                                    No tenants found. Click "Onboard Tenant" to create one.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {showModal && (
                <CreateTenantModal
                    onClose={() => setShowModal(false)}
                    onCreated={fetchData}
                />
            )}
        </div>
    );
}

export default TenantList;

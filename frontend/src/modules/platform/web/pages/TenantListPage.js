import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import platformApiService from '../../../../core/api/platformClient';
import { formatDateTime } from '../../../../utils/dateUtils';
import CreateTenantModal from '../components/CreateTenantModal';

function TenantList() {
    // Data State
    const [tenants, setTenants] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    // Query State
    const [page, setPage] = useState(1);
    const [limit] = useState(10);
    const [total, setTotal] = useState(0);
    const [search, setSearch] = useState('');
    const [debouncedSearch, setDebouncedSearch] = useState('');

    // UI State
    const [showModal, setShowModal] = useState(false);

    // Debounce search input
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(search);
            setPage(1); // Reset to page 1 on search
        }, 500);
        return () => clearTimeout(timer);
    }, [search]);

    // Fetch data when deps change
    useEffect(() => {
        fetchData();
    }, [page, debouncedSearch]);

    // Initial stats fetch
    useEffect(() => {
        fetchStats();
    }, []);

    const fetchStats = async () => {
        try {
            const statsData = await platformApiService.getStats();
            setStats(statsData);
        } catch (error) {
            console.error('Error fetching stats:', error);
        }
    };

    const fetchData = async () => {
        setLoading(true);
        try {
            const skip = (page - 1) * limit;
            const response = await platformApiService.getTenants(skip, limit, debouncedSearch);

            // Backend now returns { items, total, page, limit }
            setTenants(response.items || []);
            setTotal(response.total || 0);
        } catch (error) {
            console.error('Error fetching tenants:', error);
            setTenants([]);
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

    const totalPages = Math.ceil(total / limit);

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

    return (
        <div>
            <div className="platform-page-header">
                <div>
                    <h1 className="platform-page-title">Tenant Management</h1>
                    <p style={{ color: '#6b7280', marginTop: '0.25rem' }}>
                        Manage all SaaS tenants, onboarding, and subscriptions.
                    </p>
                </div>
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

            {/* Search and Filters Bar */}
            <div style={{
                marginBottom: '1rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                backgroundColor: 'white',
                padding: '1rem',
                borderRadius: '0.5rem',
                border: '1px solid #e5e7eb',
                boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'
            }}>
                <div style={{ position: 'relative', width: '300px' }}>
                    <input
                        type="text"
                        placeholder="Search tenants..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        style={{
                            width: '100%',
                            padding: '0.5rem 0.75rem 0.5rem 2rem',
                            borderRadius: '0.375rem',
                            border: '1px solid #d1d5db',
                            fontSize: '0.875rem'
                        }}
                    />
                    <span style={{
                        position: 'absolute',
                        left: '0.75rem',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        color: '#9ca3af',
                        fontSize: '1rem'
                    }}>
                        🔍
                    </span>
                </div>
                <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                    Showing {tenants.length} of {total} tenants
                </div>
            </div>

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
                        {loading ? (
                            <tr>
                                <td colSpan="6" style={{ textAlign: 'center', padding: '3rem' }}>
                                    <div className="spinner large" style={{ margin: '0 auto' }}></div>
                                </td>
                            </tr>
                        ) : tenants.length > 0 ? (
                            tenants.map((tenant) => (
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
                                                    color: '#374151',
                                                    border: '1px solid #d1d5db'
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
                                                            background: 'rgba(239, 68, 68, 0.1)',
                                                            color: '#dc2626',
                                                            border: '1px solid #fecaca'
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
                                                        background: '#fff7ed',
                                                        color: '#ea580c',
                                                        border: '1px solid #fdba74',
                                                        fontWeight: '500'
                                                    }}
                                                    title="Resend Activation Email"
                                                >
                                                    Resend Invite
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="6" style={{ textAlign: 'center', padding: '2rem', color: '#9ca3af' }}>
                                    {search ? 'No tenants found matching your search.' : 'No tenants found. Click "Onboard Tenant" to create one.'}
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
                <div style={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    gap: '1rem',
                    marginTop: '1.5rem',
                    padding: '1rem',
                    backgroundColor: 'white',
                    borderRadius: '0.5rem',
                    boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'
                }}>
                    <button
                        className="platform-btn"
                        disabled={page === 1}
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        style={{
                            background: page === 1 ? '#f3f4f6' : 'white',
                            color: page === 1 ? '#9ca3af' : '#374151',
                            border: '1px solid #d1d5db',
                            cursor: page === 1 ? 'not-allowed' : 'pointer'
                        }}
                    >
                        Previous
                    </button>

                    <span style={{ fontSize: '0.875rem', color: '#4b5563' }}>
                        Page <span style={{ fontWeight: '600' }}>{page}</span> of <span style={{ fontWeight: '600' }}>{totalPages}</span>
                    </span>

                    <button
                        className="platform-btn"
                        disabled={page === totalPages}
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                        style={{
                            background: page === totalPages ? '#f3f4f6' : 'white',
                            color: page === totalPages ? '#9ca3af' : '#374151',
                            border: '1px solid #d1d5db',
                            cursor: page === totalPages ? 'not-allowed' : 'pointer'
                        }}
                    >
                        Next
                    </button>
                </div>
            )}

            {showModal && (
                <CreateTenantModal
                    onClose={() => setShowModal(false)}
                    onCreated={() => {
                        fetchData();
                        fetchStats();
                    }}
                />
            )}
        </div>
    );
}

export default TenantList;

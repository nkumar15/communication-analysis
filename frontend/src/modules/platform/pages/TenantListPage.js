import { useState, useEffect } from 'react';
import apiService from '../../../core/api/b2bClient';
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
                apiService.get('/api/platform/tenants'),
                apiService.get('/api/platform/stats')
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
            const response = await apiService.post(`/api/platform/tenants/${tenantId}/impersonate`);

            // Store impersonation state
            localStorage.setItem('impersonating', 'true');
            localStorage.setItem('impersonation_token', response.token);
            localStorage.setItem('impersonation_tenant', response.tenant_name);

            // Redirect to tenant dashboard
            window.location.href = '/dashboard';
        } catch (error) {
            alert('Failed to impersonate: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="loading-container">
                <div className="spinner large"></div>
            </div>
        );
    }

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h1 style={{ margin: 0 }}>Tenant Management</h1>
                <button
                    className="saas-btn saas-btn-primary"
                    onClick={() => setShowModal(true)}
                >
                    + Create Tenant
                </button>
            </div>

            {stats && (
                <div className="saas-stats-grid">
                    <div className="saas-stat-card">
                        <div className="saas-stat-label">Total Tenants</div>
                        <div className="saas-stat-value">{stats.total_tenants}</div>
                    </div>
                    <div className="saas-stat-card">
                        <div className="saas-stat-label">Active Tenants</div>
                        <div className="saas-stat-value">{stats.active_tenants}</div>
                    </div>
                    <div className="saas-stat-card">
                        <div className="saas-stat-label">Total Users</div>
                        <div className="saas-stat-value">{stats.total_users}</div>
                    </div>
                </div>
            )}

            <div className="saas-table-container">
                <table className="saas-table">
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
                                <td>{tenant.name}</td>
                                <td>{tenant.domain}</td>
                                <td>
                                    <span className={`saas-badge ${tenant.status === 'active' ? 'active' : 'pending'}`}>
                                        {tenant.status}
                                    </span>
                                </td>
                                <td>{tenant.user_count}</td>
                                <td>{new Date(tenant.created_at).toLocaleDateString()}</td>
                                <td>
                                    <button
                                        className="saas-btn saas-btn-primary"
                                        onClick={() => handleImpersonate(tenant.id)}
                                        style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem' }}
                                    >
                                        Login As
                                    </button>
                                </td>
                            </tr>
                        ))}
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

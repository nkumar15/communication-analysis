import { useState, useEffect } from 'react';
import platformApiService from '../../../../core/api/platformClient';
import { useProduct } from '../layouts/SuperAdminLayout';

function Dashboard() {
    const { selectedProduct } = useProduct();
    const [b2bStats, setB2bStats] = useState(null);
    const [b2cStats, setB2cStats] = useState(null);
    const [tenants, setTenants] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);

            if (selectedProduct === 'b2b') {
                try {
                    const [stats, tenantsData] = await Promise.all([
                        platformApiService.getB2BStats(),
                        platformApiService.getTenants(0, 5)
                    ]);
                    setB2bStats(stats);
                    setTenants(tenantsData.items || []);
                } catch (error) {
                    console.error('B2B data error:', error);
                }
            } else {
                try {
                    const stats = await platformApiService.getB2CStats();
                    setB2cStats(stats);
                } catch (error) {
                    console.error('B2C data error:', error);
                }
            }

            setLoading(false);
        };

        fetchData();
    }, [selectedProduct]);

    if (loading) {
        return (
            <div className="loading-container">
                <div className="spinner large"></div>
            </div>
        );
    }

    return (
        <div>
            <div className="platform-page-header">
                <h1 className="platform-page-title">
                    {selectedProduct === 'b2b' ? '🏢 B2B Dashboard' : '👤 B2C Dashboard'}
                </h1>
            </div>

            {selectedProduct === 'b2b' && b2bStats && (
                <B2BDashboard stats={b2bStats} tenants={tenants} />
            )}

            {selectedProduct === 'b2c' && b2cStats && (
                <B2CDashboard stats={b2cStats} />
            )}
        </div>
    );
}

// B2B Dashboard View
function B2BDashboard({ stats, tenants }) {
    return (
        <div>
            <div className="platform-stats-grid">
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Total Tenants</div>
                    <div className="platform-stat-value">{stats.total_tenants}</div>
                </div>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Active Tenants</div>
                    <div className="platform-stat-value" style={{ color: '#10b981' }}>{stats.active_tenants}</div>
                </div>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Pending Activation</div>
                    <div className="platform-stat-value" style={{ color: '#f59e0b' }}>{stats.pending_tenants}</div>
                </div>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Total Users</div>
                    <div className="platform-stat-value">{stats.total_users}</div>
                </div>
            </div>

            <div className="platform-card" style={{ marginTop: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h3 style={styles.cardTitle}>Recent Tenants</h3>
                    <a href="/tenants" style={styles.viewAllLink}>View All →</a>
                </div>

                {tenants.length === 0 ? (
                    <p style={{ color: '#6b7280' }}>No tenants found.</p>
                ) : (
                    <table style={styles.table}>
                        <thead>
                            <tr>
                                <th style={styles.th}>Name</th>
                                <th style={styles.th}>Domain</th>
                                <th style={styles.th}>Status</th>
                                <th style={styles.th}>Users</th>
                            </tr>
                        </thead>
                        <tbody>
                            {tenants.map(tenant => (
                                <tr key={tenant.id}>
                                    <td style={styles.td}>{tenant.name}</td>
                                    <td style={styles.td}>{tenant.domain}</td>
                                    <td style={styles.td}>
                                        <span style={{
                                            ...styles.statusBadge,
                                            background: tenant.status === 'active' ? '#d1fae5' : '#fef3c7',
                                            color: tenant.status === 'active' ? '#065f46' : '#92400e'
                                        }}>
                                            {tenant.status}
                                        </span>
                                    </td>
                                    <td style={styles.td}>{tenant.user_count}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}

// B2C Dashboard View
function B2CDashboard({ stats }) {
    return (
        <div>
            <div className="platform-stats-grid">
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Total Workspaces</div>
                    <div className="platform-stat-value">{stats.total_workspaces}</div>
                </div>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Personal Workspaces</div>
                    <div className="platform-stat-value">{stats.personal_workspaces}</div>
                </div>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Team Workspaces</div>
                    <div className="platform-stat-value">{stats.team_workspaces}</div>
                </div>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Total Users</div>
                    <div className="platform-stat-value">{stats.total_users}</div>
                </div>
            </div>

            <div className="platform-card" style={{ marginTop: '1.5rem' }}>
                <h3 style={styles.cardTitle}>Recent Workspaces</h3>
                <p style={{ color: '#6b7280' }}>Workspace management coming soon.</p>
            </div>
        </div>
    );
}

const styles = {
    cardTitle: {
        fontSize: '1rem',
        fontWeight: '600',
        marginBottom: '0',
        color: '#1f2937'
    },
    table: {
        width: '100%',
        borderCollapse: 'collapse'
    },
    th: {
        textAlign: 'left',
        padding: '0.75rem',
        borderBottom: '2px solid #e5e7eb',
        fontSize: '0.75rem',
        fontWeight: '600',
        color: '#6b7280',
        textTransform: 'uppercase'
    },
    td: {
        padding: '0.75rem',
        borderBottom: '1px solid #e5e7eb',
        fontSize: '0.875rem',
        color: '#374151'
    },
    statusBadge: {
        padding: '0.25rem 0.5rem',
        borderRadius: '9999px',
        fontSize: '0.75rem',
        fontWeight: '500'
    },
    viewAllLink: {
        color: '#6366f1',
        textDecoration: 'none',
        fontSize: '0.875rem',
        fontWeight: '500'
    }
};

export default Dashboard;

import { useState, useEffect } from 'react';
import platformApiService from '../../../../core/api/platformClient';

function Dashboard() {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const data = await platformApiService.getStats();
                setStats(data);
            } catch (error) {
                console.error('Error fetching stats:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchStats();
    }, []);

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
                <h1 className="platform-page-title">Dashboard</h1>
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

            <div className="platform-card">
                <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: '#1f2937' }}>Recent Activity</h2>
                <p style={{ color: '#6b7280' }}>No recent activity to show.</p>
            </div>
        </div>
    );
}

export default Dashboard;

import { useState, useEffect } from 'react';
import platformApiService from '../../../core/api/platformClient';

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
            <h1 style={{ marginBottom: '2rem' }}>Dashboard</h1>

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

            <div className="content-card">
                <h2>Recent Activity</h2>
                <p style={{ color: '#a0a0b0' }}>No recent activity to show.</p>
            </div>
        </div>
    );
}

export default Dashboard;

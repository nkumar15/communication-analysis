import { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import platformApiService from '../../../../core/api/platformClient';
import { useProduct } from '../layouts/SuperAdminLayout';

function AnalyticsPage() {
    const { selectedProduct } = useProduct();

    return (
        <div>
            <div className="platform-page-header">
                <h1 className="platform-page-title">
                    {selectedProduct === 'b2b' ? '🏢 B2B Analytics' : '👤 B2C Analytics'}
                </h1>
                <p className="platform-page-subtitle">
                    Business metrics and insights
                </p>
            </div>

            {selectedProduct === 'b2b' && <B2BAnalytics />}
            {selectedProduct === 'b2c' && <B2CAnalytics />}
        </div>
    );
}

// B2B Analytics Component
function B2BAnalytics() {
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [timeRange, setTimeRange] = useState('30d');

    useEffect(() => {
        fetchB2BMetrics();
    }, [timeRange]);

    const fetchB2BMetrics = async () => {
        setLoading(true);
        try {
            // TODO: Replace with real API
            // const data = await platformApiService.getB2BAnalytics(timeRange);

            // Mock data
            const mockData = {
                overview: {
                    total_tenants: 45,
                    active_tenants: 42,
                    trial_tenants: 8,
                    paid_tenants: 34,
                    mrr: 15420,
                    arr: 185040,
                    total_users: 892
                },
                tenant_growth: [
                    { month: 'Jul', tenants: 28 },
                    { month: 'Aug', tenants: 32 },
                    { month: 'Sep', tenants: 36 },
                    { month: 'Oct', tenants: 39 },
                    { month: 'Nov', tenants: 42 },
                    { month: 'Dec', tenants: 45 }
                ],
                revenue_trend: [
                    { month: 'Jul', revenue: 10200 },
                    { month: 'Aug', revenue: 11500 },
                    { month: 'Sep', revenue: 12800 },
                    { month: 'Oct', revenue: 13900 },
                    { month: 'Nov', revenue: 14600 },
                    { month: 'Dec', revenue: 15420 }
                ],
                tier_distribution: [
                    { name: 'Starter', value: 18, color: '#3B82F6' },
                    { name: 'Professional', value: 15, color: '#8B5CF6' },
                    { name: 'Enterprise', value: 12, color: '#D97706' }
                ],
                sso_adoption: {
                    oidc: 28,
                    saml: 10,
                    none: 7
                }
            };

            setMetrics(mockData);
        } catch (error) {
            console.error('Failed to fetch B2B analytics:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return <div style={{ padding: '40px', textAlign: 'center', color: '#9CA3AF' }}>Loading analytics...</div>;
    }

    return (
        <div>
            {/* Time Range Selector */}
            <div style={{ display: 'flex', gap: '12px', marginBottom: '24px' }}>
                {['7d', '30d', '90d', '1y'].map((range) => (
                    <button
                        key={range}
                        onClick={() => setTimeRange(range)}
                        style={{
                            padding: '8px 16px',
                            borderRadius: '6px',
                            border: timeRange === range ? '2px solid #6366F1' : '1px solid #374151',
                            backgroundColor: timeRange === range ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                            color: timeRange === range ? '#A78BFA' : '#9CA3AF',
                            fontSize: '14px',
                            fontWeight: '500',
                            cursor: 'pointer'
                        }}
                    >
                        {range === '7d' ? 'Last 7 Days' : range === '30d' ? 'Last 30 Days' : range === '90d' ? 'Last 90 Days' : 'Last Year'}
                    </button>
                ))}
            </div>

            {/* Overview Stats */}
            <div className="platform-stats-grid" style={{ marginBottom: '32px' }}>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Total Tenants</div>
                    <div className="platform-stat-value">{metrics.overview.total_tenants}</div>
                    <div style={{ fontSize: '12px', color: '#10B981', marginTop: '4px' }}>
                        +3 this month
                    </div>
                </div>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Active Tenants</div>
                    <div className="platform-stat-value" style={{ color: '#10B981' }}>
                        {metrics.overview.active_tenants}
                    </div>
                    <div style={{ fontSize: '12px', color: '#9CA3AF', marginTop: '4px' }}>
                        {Math.round((metrics.overview.active_tenants / metrics.overview.total_tenants) * 100)}% active
                    </div>
                </div>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Monthly Revenue</div>
                    <div className="platform-stat-value" style={{ color: '#6366F1' }}>
                        ${metrics.overview.mrr.toLocaleString()}
                    </div>
                    <div style={{ fontSize: '12px', color: '#10B981', marginTop: '4px' }}>
                        +5.6% from last month
                    </div>
                </div>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Total Users</div>
                    <div className="platform-stat-value">{metrics.overview.total_users}</div>
                    <div style={{ fontSize: '12px', color: '#9CA3AF', marginTop: '4px' }}>
                        Across all tenants
                    </div>
                </div>
            </div>

            {/* Charts Row 1 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
                {/* Tenant Growth Chart */}
                <div className="platform-card">
                    <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '20px', color: '#E5E7EB' }}>
                        Tenant Growth
                    </h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <LineChart data={metrics.tenant_growth}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis dataKey="month" stroke="#9CA3AF" />
                            <YAxis stroke="#9CA3AF" />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
                                labelStyle={{ color: '#E5E7EB' }}
                            />
                            <Line type="monotone" dataKey="tenants" stroke="#6366F1" strokeWidth={2} dot={{ fill: '#6366F1', r: 4 }} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>

                {/* Revenue Trend */}
                <div className="platform-card">
                    <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '20px', color: '#E5E7EB' }}>
                        Revenue Trend (MRR)
                    </h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <AreaChart data={metrics.revenue_trend}>
                            <defs>
                                <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis dataKey="month" stroke="#9CA3AF" />
                            <YAxis stroke="#9CA3AF" />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
                                labelStyle={{ color: '#E5E7EB' }}
                                formatter={(value) => `$${value.toLocaleString()}`}
                            />
                            <Area type="monotone" dataKey="revenue" stroke="#10B981" fillOpacity={1} fill="url(#colorRevenue)" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Charts Row 2 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                {/* Subscription Tiers */}
                <div className="platform-card">
                    <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '20px', color: '#E5E7EB' }}>
                        Subscription Tier Distribution
                    </h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <PieChart>
                            <Pie
                                data={metrics.tier_distribution}
                                cx="50%"
                                cy="50%"
                                labelLine={false}
                                label={(entry) => `${entry.name}: ${entry.value}`}
                                outerRadius={80}
                                fill="#8884d8"
                                dataKey="value"
                            >
                                {metrics.tier_distribution.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                </div>

                {/* SSO Adoption */}
                <div className="platform-card">
                    <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '20px', color: '#E5E7EB' }}>
                        SSO Adoption
                    </h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={[
                            { name: 'OIDC', count: metrics.sso_adoption.oidc },
                            { name: 'SAML', count: metrics.sso_adoption.saml },
                            { name: 'None', count: metrics.sso_adoption.none }
                        ]}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis dataKey="name" stroke="#9CA3AF" />
                            <YAxis stroke="#9CA3AF" />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
                                labelStyle={{ color: '#E5E7EB' }}
                            />
                            <Bar dataKey="count" fill="#8B5CF6" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
}

// B2C Analytics Component
function B2CAnalytics() {
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [timeRange, setTimeRange] = useState('30d');

    useEffect(() => {
        fetchB2CMetrics();
    }, [timeRange]);

    const fetchB2CMetrics = async () => {
        setLoading(true);
        try {
            // TODO: Replace with real API
            // const data = await platformApiService.getB2CAnalytics(timeRange);

            // Mock data
            const mockData = {
                overview: {
                    total_users: 1245,
                    active_users: 982,
                    total_workspaces: 892,
                    personal_workspaces: 645,
                    team_workspaces: 247,
                    mrr: 8730,
                    total_projects: 3456
                },
                user_signups: [
                    { month: 'Jul', users: 156 },
                    { month: 'Aug', users: 189 },
                    { month: 'Sep', users: 210 },
                    { month: 'Oct', users: 243 },
                    { month: 'Nov', users: 278 },
                    { month: 'Dec', users: 312 }
                ],
                workspace_creation: [
                    { month: 'Jul', count: 120 },
                    { month: 'Aug', count: 145 },
                    { month: 'Sep', count: 168 },
                    { month: 'Oct', count: 192 },
                    { month: 'Nov', count: 215 },
                    { month: 'Dec', count: 238 }
                ],
                subscription_tiers: [
                    { name: 'Free', value: 756, color: '#6B7280' },
                    { name: 'Premium', value: 389, color: '#6366F1' },
                    { name: 'Ultimate', value: 100, color: '#8B5CF6' }
                ]
            };

            setMetrics(mockData);
        } catch (error) {
            console.error('Failed to fetch B2C analytics:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return <div style={{ padding: '40px', textAlign: 'center', color: '#9CA3AF' }}>Loading analytics...</div>;
    }

    return (
        <div>
            {/* Time Range Selector */}
            <div style={{ display: 'flex', gap: '12px', marginBottom: '24px' }}>
                {['7d', '30d', '90d', '1y'].map((range) => (
                    <button
                        key={range}
                        onClick={() => setTimeRange(range)}
                        style={{
                            padding: '8px 16px',
                            borderRadius: '6px',
                            border: timeRange === range ? '2px solid #10B981' : '1px solid #374151',
                            backgroundColor: timeRange === range ? 'rgba(16, 185, 129, 0.2)' : 'transparent',
                            color: timeRange === range ? '#10B981' : '#9CA3AF',
                            fontSize: '14px',
                            fontWeight: '500',
                            cursor: 'pointer'
                        }}
                    >
                        {range === '7d' ? 'Last 7 Days' : range === '30d' ? 'Last 30 Days' : range === '90d' ? 'Last 90 Days' : 'Last Year'}
                    </button>
                ))}
            </div>

            {/* Overview Stats */}
            <div className="platform-stats-grid" style={{ marginBottom: '32px' }}>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Total Users</div>
                    <div className="platform-stat-value">{metrics.overview.total_users.toLocaleString()}</div>
                    <div style={{ fontSize: '12px', color: '#10B981', marginTop: '4px' }}>
                        +87 this month
                    </div>
                </div>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Total Workspaces</div>
                    <div className="platform-stat-value" style={{ color: '#10B981' }}>
                        {metrics.overview.total_workspaces}
                    </div>
                    <div style={{ fontSize: '12px', color: '#9CA3AF', marginTop: '4px' }}>
                        {metrics.overview.personal_workspaces} personal, {metrics.overview.team_workspaces} team
                    </div>
                </div>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Monthly Revenue</div>
                    <div className="platform-stat-value" style={{ color: '#6366F1' }}>
                        ${metrics.overview.mrr.toLocaleString()}
                    </div>
                    <div style={{ fontSize: '12px', color: '#10B981', marginTop: '4px' }}>
                        +8.2% from last month
                    </div>
                </div>
                <div className="platform-stat-card">
                    <div className="platform-stat-label">Total Projects</div>
                    <div className="platform-stat-value">{metrics.overview.total_projects.toLocaleString()}</div>
                    <div style={{ fontSize: '12px', color: '#9CA3AF', marginTop: '4px' }}>
                        Across all workspaces
                    </div>
                </div>
            </div>

            {/* Charts Row 1 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
                {/* User Signups */}
                <div className="platform-card">
                    <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '20px', color: '#E5E7EB' }}>
                        User Signups
                    </h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <AreaChart data={metrics.user_signups}>
                            <defs>
                                <linearGradient id="colorUsers" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#6366F1" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#6366F1" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis dataKey="month" stroke="#9CA3AF" />
                            <YAxis stroke="#9CA3AF" />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
                                labelStyle={{ color: '#E5E7EB' }}
                            />
                            <Area type="monotone" dataKey="users" stroke="#6366F1" fillOpacity={1} fill="url(#colorUsers)" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>

                {/* Workspace Creation */}
                <div className="platform-card">
                    <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '20px', color: '#E5E7EB' }}>
                        Workspace Creation
                    </h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <LineChart data={metrics.workspace_creation}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis dataKey="month" stroke="#9CA3AF" />
                            <YAxis stroke="#9CA3AF" />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
                                labelStyle={{ color: '#E5E7EB' }}
                            />
                            <Line type="monotone" dataKey="count" stroke="#10B981" strokeWidth={2} dot={{ fill: '#10B981', r: 4 }} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Charts Row 2 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                {/* Subscription Tiers */}
                <div className="platform-card">
                    <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '20px', color: '#E5E7EB' }}>
                        Subscription Distribution
                    </h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <PieChart>
                            <Pie
                                data={metrics.subscription_tiers}
                                cx="50%"
                                cy="50%"
                                labelLine={false}
                                label={(entry) => `${entry.name}: ${entry.value}`}
                                outerRadius={80}
                                fill="#8884d8"
                                dataKey="value"
                            >
                                {metrics.subscription_tiers.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                </div>

                {/* Workspace Types */}
                <div className="platform-card">
                    <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '20px', color: '#E5E7EB' }}>
                        Workspace Types
                    </h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={[
                            { name: 'Personal', count: metrics.overview.personal_workspaces },
                            { name: 'Team', count: metrics.overview.team_workspaces }
                        ]}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis dataKey="name" stroke="#9CA3AF" />
                            <YAxis stroke="#9CA3AF" />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
                                labelStyle={{ color: '#E5E7EB' }}
                            />
                            <Bar dataKey="count" fill="#10B981" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
}

export default AnalyticsPage;

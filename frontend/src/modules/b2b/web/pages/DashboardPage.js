import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import b2bClient from '../../../../core/api/b2bClient';
import StatCard from '../../../../core/components/StatCard';
import AdminLayout from '../layouts/AdminLayout';
import useAuth from '../../../../core/hooks/useAuth';
import { TENANT_ROLES } from '../../constants/roles';
import MyTeamsWidget from '../components/widgets/MyTeamsWidget';

import QuickActionsWidget from '../components/widgets/QuickActionsWidget';
import { DashboardSkeleton } from '../../../../core/components/LoadingSkeleton';

const DashboardPage = () => {
    const [dashboardData, setDashboardData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const { user, loading: authLoading } = useAuth();
    const navigate = useNavigate();

    useEffect(() => {
        loadDashboard();
    }, []);

    const loadDashboard = async () => {
        try {
            setLoading(true);
            const data = await b2bClient.getDashboardStats();
            setDashboardData(data);
        } catch (err) {
            console.error('Failed to load dashboard:', err);
            setError('Failed to load dashboard data');
        } finally {
            setLoading(false);
        }
    };

    // Show loading while auth is checking
    if (authLoading || loading) {
        return (
            <AdminLayout title="Dashboard" subtitle="Your workspace overview">
                <DashboardSkeleton />
            </AdminLayout>
        );
    }

    const role = user?.role || TENANT_ROLES.VIEWER;
    const isAdminScope = [TENANT_ROLES.OWNER, TENANT_ROLES.ADMIN].includes(role);

    // Get greeting based on role
    const getRoleGreeting = () => {
        switch (role) {
            case TENANT_ROLES.OWNER: return '👑 Organization Owner';
            case TENANT_ROLES.ADMIN: return '🛡️ Administrator';
            case TENANT_ROLES.MEMBER: return '👤 Team Member';
            default: return '👁️ Viewer';
        }
    };

    return (
        <>
            <AdminLayout title="Dashboard" subtitle={getRoleGreeting()}>
                <div style={{ padding: '32px', maxWidth: '1400px', margin: '0 auto' }}>

                    {/* Error State */}
                    {error && (
                        <div style={{
                            backgroundColor: '#FEF2F2',
                            border: '1px solid #FCA5A5',
                            borderRadius: '8px',
                            padding: '12px 16px',
                            marginBottom: '24px',
                            color: '#DC2626'
                        }}>
                            {error}
                        </div>
                    )}

                    {loading ? (
                        <div style={{ textAlign: 'center', padding: '60px' }}>
                            <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</div>
                            <p style={{ color: '#6B7280' }}>Loading dashboard...</p>
                        </div>
                    ) : dashboardData && (
                        <>
                            {/* Org Stats - Visible to all roles */}
                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                                gap: '20px',
                                marginBottom: '24px'
                            }}>
                                <StatCard
                                    icon="👥"
                                    label="Total Users"
                                    value={dashboardData.total_users}
                                    color="#4F46E5"
                                />
                                <StatCard
                                    icon="✅"
                                    label="Active Users"
                                    value={dashboardData.active_users}
                                    color="#10B981"
                                />
                                <StatCard
                                    icon="🏢"
                                    label="Teams"
                                    value={dashboardData.total_teams}
                                    color="#8B5CF6"
                                />
                                {/* Pending invitations only for admin/owner */}
                                {isAdminScope && (
                                    <StatCard
                                        icon="📨"
                                        label="Pending Invites"
                                        value={dashboardData.pending_invitations}
                                        color="#F59E0B"
                                    />
                                )}
                            </div>

                            {/* Two column layout for widgets */}
                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
                                gap: '24px',
                                marginBottom: '24px'
                            }}>
                                {/* My Teams Widget - All roles */}
                                <MyTeamsWidget
                                    teams={dashboardData.my_teams || []}
                                    loading={loading}
                                />

                                {/* Quick Actions Widget - Replaces My Work */}
                                <QuickActionsWidget
                                    actions={dashboardData.quick_actions || []}
                                    role={role}
                                />
                            </div>


                        </>
                    )}
                </div>
            </AdminLayout>
        </>
    );
};

export default DashboardPage;

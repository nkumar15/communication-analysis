import React, { useState, useEffect } from 'react';
import invitationApi from '../services/invitationApi';
import StatCard from './StatCard';
import AdminLayout from './layout/AdminLayout';

const DashboardPage = () => {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadStats();
    }, []);

    const loadStats = async () => {
        try {
            const data = await invitationApi.getUserStats();
            setStats(data);
        } catch (err) {
            console.error('Failed to load stats:', err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <AdminLayout title="Dashboard" subtitle="Welcome to your SSO admin panel">
            <div style={{ padding: '32px', maxWidth: '1400px', margin: '0 auto' }}>
                {/* Statistics */}
                {loading ? (
                    <div style={{ textAlign: 'center', padding: '60px' }}>
                        <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</div>
                        <p style={{ color: '#6B7280' }}>Loading statistics...</p>
                    </div>
                ) : stats && (
                    <>
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                            gap: '20px',
                            marginBottom: '32px'
                        }}>
                            <StatCard icon="👥" label="Total Users" value={stats.total_users} color="#4F46E5" />
                            <StatCard icon="✅" label="Active Users" value={stats.active_users} color="#10B981" />
                            <StatCard icon="📨" label="Pending Invitations" value={stats.pending_invitations} color="#F59E0B" />
                            <StatCard icon="👔" label="Managers" value={stats.managers_count} color="#8B5CF6" />
                        </div>

                        {/* Welcome Card */}
                        <div style={{
                            backgroundColor: 'white',
                            borderRadius: '12px',
                            padding: '32px',
                            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                            border: '1px solid #E5E7EB',
                            marginBottom: '24px'
                        }}>
                            <h2 style={{ margin: '0 0 16px 0', fontSize: '24px', color: '#111827' }}>
                                🎉 Welcome to SSO Admin Portal
                            </h2>
                            <p style={{ color: '#6B7280', lineHeight: '1.6', marginBottom: '24px' }}>
                                Manage your organization's users, invitations, and SSO configuration from this central dashboard.
                                Use the sidebar navigation to access different sections.
                            </p>

                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                                gap: '16px'
                            }}>
                                <div style={{
                                    padding: '20px',
                                    backgroundColor: '#F9FAFB',
                                    borderRadius: '8px',
                                    border: '1px solid #E5E7EB'
                                }}>
                                    <div style={{ fontSize: '24px', marginBottom: '12px' }}>🔐</div>
                                    <h3 style={{ margin: '0 0 8px 0', fontSize: '16px', fontWeight: '600', color: '#111827' }}>
                                        Firebase SSO
                                    </h3>
                                    <p style={{ margin: 0, fontSize: '14px', color: '#6B7280', lineHeight: '1.5' }}>
                                        Secure authentication with Firebase GCIP and OIDC multi-tenant support
                                    </p>
                                </div>

                                <div style={{
                                    padding: '20px',
                                    backgroundColor: '#F9FAFB',
                                    borderRadius: '8px',
                                    border: '1px solid #E5E7EB'
                                }}>
                                    <div style={{ fontSize: '24px', marginBottom: '12px' }}>👥</div>
                                    <h3 style={{ margin: '0 0 8px 0', fontSize: '16px', fontWeight: '600', color: '#111827' }}>
                                        User Management
                                    </h3>
                                    <p style={{ margin: 0, fontSize: '14px', color: '#6B7280', lineHeight: '1.5' }}>
                                        Invite users, manage roles, and track team members
                                    </p>
                                </div>

                                <div style={{
                                    padding: '20px',
                                    backgroundColor: '#F9FAFB',
                                    borderRadius: '8px',
                                    border: '1px solid #E5E7EB'
                                }}>
                                    <div style={{ fontSize: '24px', marginBottom: '12px' }}>📊</div>
                                    <h3 style={{ margin: '0 0 8px 0', fontSize: '16px', fontWeight: '600', color: '#111827' }}>
                                        Real-time Stats
                                    </h3>
                                    <p style={{ margin: 0, fontSize: '14px', color: '#6B7280', lineHeight: '1.5' }}>
                                        Monitor user activity and invitation status at a glance
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Quick Actions */}
                        <div style={{
                            backgroundColor: 'white',
                            borderRadius: '12px',
                            padding: '24px',
                            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                            border: '1px solid #E5E7EB'
                        }}>
                            <h3 style={{ margin: '0 0 16px 0', fontSize: '18px', fontWeight: '600', color: '#111827' }}>
                                Quick Actions
                            </h3>
                            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                                <button
                                    onClick={() => window.location.href = '/invitations'}
                                    style={{
                                        padding: '12px 24px',
                                        backgroundColor: '#4F46E5',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        fontSize: '14px',
                                        fontWeight: '500',
                                        cursor: 'pointer',
                                        transition: 'background-color 0.2s'
                                    }}
                                    onMouseEnter={(e) => e.target.style.backgroundColor = '#4338CA'}
                                    onMouseLeave={(e) => e.target.style.backgroundColor = '#4F46E5'}
                                >
                                    👥 Manage Users
                                </button>

                                <button
                                    onClick={() => window.location.href = '/invitations'}
                                    style={{
                                        padding: '12px 24px',
                                        backgroundColor: 'white',
                                        color: '#374151',
                                        border: '1px solid #D1D5DB',
                                        borderRadius: '6px',
                                        fontSize: '14px',
                                        fontWeight: '500',
                                        cursor: 'pointer',
                                        transition: 'background-color 0.2s'
                                    }}
                                    onMouseEnter={(e) => e.target.style.backgroundColor = '#F9FAFB'}
                                    onMouseLeave={(e) => e.target.style.backgroundColor = 'white'}
                                >
                                    📧 Send Invitation
                                </button>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </AdminLayout>
    );
};

export default DashboardPage;

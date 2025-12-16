import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth } from '../../../../core/firebase/b2c-config';
import B2CLayout from '../layouts/B2CLayout';
import WorkspaceCard from '../components/WorkspaceCard';
import EmptyState from '../components/EmptyState';
import CreateWorkspaceModal from '../components/CreateWorkspaceModal';
import { B2CDashboardSkeleton } from '../components/LoadingSkeletons';
import { mockApi } from '../services/mockData';

const DashboardPage = () => {
    const navigate = useNavigate();
    const [workspaces, setWorkspaces] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);

    useEffect(() => {
        const unsubscribe = auth.onAuthStateChanged(async (firebaseUser) => {
            if (!firebaseUser) {
                navigate('/login');
                return;
            }

            // Fetch workspaces
            try {
                const data = await mockApi.getWorkspaces();
                setWorkspaces(data);
            } catch (error) {
                console.error('Failed to fetch workspaces:', error);
            } finally {
                setLoading(false);
            }
        });

        return () => unsubscribe();
    }, [navigate]);

    const handleWorkspaceCreated = (newWorkspace) => {
        setWorkspaces([...workspaces, newWorkspace]);
    };

    if (loading) {
        return (
            <B2CLayout>
                <B2CDashboardSkeleton />
            </B2CLayout>
        );
    }

    return (
        <B2CLayout>
            {/* Welcome Header */}
            <div style={{ marginBottom: '32px' }}>
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    marginBottom: '12px',
                    flexWrap: 'wrap',
                    gap: '16px'
                }}>
                    <div>
                        <h1 style={{
                            fontSize: '32px',
                            fontWeight: '700',
                            color: '#111827',
                            margin: '0 0 8px 0'
                        }}>
                            Welcome back, {auth.currentUser?.displayName?.split(' ')[0] || 'User'}!
                        </h1>
                        <p style={{
                            fontSize: '16px',
                            color: '#6B7280',
                            margin: 0
                        }}>
                            Manage your workspaces and projects all in one place
                        </p>
                    </div>

                    {/* Create Workspace Button */}
                    <button
                        onClick={() => setShowCreateModal(true)}
                        style={{
                            padding: '14px 24px',
                            borderRadius: '10px',
                            border: 'none',
                            background: 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)',
                            color: 'white',
                            fontSize: '15px',
                            fontWeight: '600',
                            cursor: 'pointer',
                            boxShadow: '0 4px 12px rgba(99, 102, 241, 0.4)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            transition: 'transform 0.2s, box-shadow 0.2s'
                        }}
                        onMouseEnter={(e) => {
                            e.target.style.transform = 'translateY(-2px)';
                            e.target.style.boxShadow = '0 6px 16px rgba(99, 102, 241, 0.5)';
                        }}
                        onMouseLeave={(e) => {
                            e.target.style.transform = 'translateY(0)';
                            e.target.style.boxShadow = '0 4px 12px rgba(99, 102, 241, 0.4)';
                        }}
                    >
                        <span style={{ fontSize: '18px' }}>✨</span>
                        <span>New Workspace</span>
                    </button>
                </div>
            </div>

            {/* Workspaces Section */}
            {workspaces.length > 0 ? (
                <>
                    <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '20px'
                    }}>
                        <h2 style={{
                            fontSize: '20px',
                            fontWeight: '600',
                            color: '#111827',
                            margin: 0
                        }}>
                            Your Workspaces
                        </h2>
                        <span style={{
                            fontSize: '14px',
                            color: '#6B7280',
                            fontWeight: '500'
                        }}>
                            {workspaces.length} {workspaces.length === 1 ? 'workspace' : 'workspaces'}
                        </span>
                    </div>

                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
                        gap: '20px'
                    }}>
                        {workspaces.map((workspace) => (
                            <WorkspaceCard
                                key={workspace.id}
                                workspace={workspace}
                            />
                        ))}
                    </div>

                    {/* Quick Stats */}
                    <div style={{
                        marginTop: '40px',
                        padding: '24px',
                        backgroundColor: 'white',
                        borderRadius: '12px',
                        border: '1px solid #E5E7EB'
                    }}>
                        <h3 style={{
                            fontSize: '18px',
                            fontWeight: '600',
                            color: '#111827',
                            margin: '0 0 20px 0'
                        }}>
                            Quick Stats
                        </h3>
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                            gap: '20px'
                        }}>
                            <div style={{
                                padding: '16px',
                                backgroundColor: '#F9FAFB',
                                borderRadius: '8px'
                            }}>
                                <div style={{
                                    fontSize: '28px',
                                    fontWeight: '700',
                                    color: '#6366F1',
                                    marginBottom: '4px'
                                }}>
                                    {workspaces.length}
                                </div>
                                <div style={{
                                    fontSize: '14px',
                                    color: '#6B7280',
                                    fontWeight: '500'
                                }}>
                                    Total Workspaces
                                </div>
                            </div>
                            <div style={{
                                padding: '16px',
                                backgroundColor: '#F9FAFB',
                                borderRadius: '8px'
                            }}>
                                <div style={{
                                    fontSize: '28px',
                                    fontWeight: '700',
                                    color: '#10B981',
                                    marginBottom: '4px'
                                }}>
                                    {workspaces.reduce((sum, w) => sum + (w.project_count || 0), 0)}
                                </div>
                                <div style={{
                                    fontSize: '14px',
                                    color: '#6B7280',
                                    fontWeight: '500'
                                }}>
                                    Total Projects
                                </div>
                            </div>
                            <div style={{
                                padding: '16px',
                                backgroundColor: '#F9FAFB',
                                borderRadius: '8px'
                            }}>
                                <div style={{
                                    fontSize: '28px',
                                    fontWeight: '700',
                                    color: '#F59E0B',
                                    marginBottom: '4px'
                                }}>
                                    {workspaces.filter(w => w.type === 'team').length}
                                </div>
                                <div style={{
                                    fontSize: '14px',
                                    color: '#6B7280',
                                    fontWeight: '500'
                                }}>
                                    Team Workspaces
                                </div>
                            </div>
                        </div>
                    </div>
                </>
            ) : (
                <EmptyState
                    icon="🚀"
                    title="No workspaces yet"
                    description="Create your first workspace to start organizing your projects and tasks"
                    actionLabel="Create Your First Workspace"
                    onAction={() => setShowCreateModal(true)}
                />
            )}

            {/* Create Workspace Modal */}
            <CreateWorkspaceModal
                isOpen={showCreateModal}
                onClose={() => setShowCreateModal(false)}
                onSuccess={handleWorkspaceCreated}
            />
        </B2CLayout>
    );
};

export default DashboardPage;

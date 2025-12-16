import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import B2CLayout from '../layouts/B2CLayout';
import WorkspaceCard from '../components/WorkspaceCard';
import CreateWorkspaceModal from '../components/CreateWorkspaceModal';
import { B2CDashboardSkeleton } from '../components/LoadingSkeletons';
import { mockApi } from '../services/mockData';

const WorkspacesListPage = () => {
    const navigate = useNavigate();
    const [workspaces, setWorkspaces] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [filter, setFilter] = useState('all'); // all, personal, team

    useEffect(() => {
        loadWorkspaces();
    }, []);

    const loadWorkspaces = async () => {
        setLoading(true);
        try {
            const data = await mockApi.getWorkspaces();
            setWorkspaces(data);
        } catch (error) {
            console.error('Failed to load workspaces:', error);
        } finally {
            setLoading(false);
        }
    };

    const filteredWorkspaces = workspaces.filter(w => {
        if (filter === 'all') return true;
        return w.type === filter;
    });

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
            {/* Header */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '32px',
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
                        All Workspaces
                    </h1>
                    <p style={{
                        fontSize: '16px',
                        color: '#6B7280',
                        margin: 0
                    }}>
                        {filteredWorkspaces.length} workspace{filteredWorkspaces.length !== 1 ? 's' : ''}
                    </p>
                </div>

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
                        gap: '8px'
                    }}
                >
                    <span>✨</span>
                    <span>New Workspace</span>
                </button>
            </div>

            {/* Filters */}
            <div style={{
                display: 'flex',
                gap: '12px',
                marginBottom: '28px',
                flexWrap: 'wrap'
            }}>
                {['all', 'personal', 'team'].map((type) => (
                    <button
                        key={type}
                        onClick={() => setFilter(type)}
                        style={{
                            padding: '10px 20px',
                            borderRadius: '8px',
                            border: filter === type ? '2px solid #6366F1' : '2px solid #E5E7EB',
                            backgroundColor: filter === type ? '#EEF2FF' : '#FFFFFF',
                            color: filter === type ? '#6366F1' : '#6B7280',
                            fontSize: '14px',
                            fontWeight: filter === type ? '600' : '500',
                            cursor: 'pointer',
                            textTransform: 'capitalize',
                            transition: 'all 0.2s'
                        }}
                    >
                        {type}
                        {type !== 'all' && (
                            <span style={{
                                marginLeft: '8px',
                                padding: '2px 8px',
                                borderRadius: '9999px',
                                backgroundColor: filter === type ? '#6366F1' : '#E5E7EB',
                                color: filter === type ? 'white' : '#6B7280',
                                fontSize: '12px',
                                fontWeight: '600'
                            }}>
                                {workspaces.filter(w => w.type === type).length}
                            </span>
                        )}
                    </button>
                ))}
            </div>

            {/* Workspaces Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
                gap: '20px'
            }}>
                {filteredWorkspaces.map((workspace) => (
                    <WorkspaceCard
                        key={workspace.id}
                        workspace={workspace}
                    />
                ))}
            </div>

            {/* Create Workspace Modal */}
            <CreateWorkspaceModal
                isOpen={showCreateModal}
                onClose={() => setShowCreateModal(false)}
                onSuccess={handleWorkspaceCreated}
            />
        </B2CLayout>
    );
};

export default WorkspacesListPage;

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import B2CLayout from '../layouts/B2CLayout';
import ProjectCard from '../components/ProjectCard';
import EmptyState from '../components/EmptyState';
import CreateProjectModal from '../components/CreateProjectModal';
import { WorkspaceCardSkeleton } from '../components/LoadingSkeletons';
import { mockApi } from '../services/mockData';

const WorkspacePage = () => {
    const { workspaceId } = useParams();
    const navigate = useNavigate();
    const [workspace, setWorkspace] = useState(null);
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateProjectModal, setShowCreateProjectModal] = useState(false);
    const [activeTab, setActiveTab] = useState('projects');

    useEffect(() => {
        loadWorkspace();
    }, [workspaceId]);

    const loadWorkspace = async () => {
        setLoading(true);
        try {
            const data = await mockApi.getWorkspace(workspaceId);
            setWorkspace(data);
            setProjects(data.projects || []);
        } catch (error) {
            console.error('Failed to load workspace:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleProjectCreated = (newProject) => {
        setProjects([...projects, newProject]);
    };

    if (loading) {
        return (
            <B2CLayout>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
                    <WorkspaceCardSkeleton />
                    <WorkspaceCardSkeleton />
                    <WorkspaceCardSkeleton />
                </div>
            </B2CLayout>
        );
    }

    if (!workspace) {
        return (
            <B2CLayout>
                <EmptyState
                    icon="❌"
                    title="Workspace not found"
                    description="The workspace you're looking for doesn't exist or you don't have access to it."
                    actionLabel="Back to Dashboard"
                    onAction={() => navigate('/')}
                />
            </B2CLayout>
        );
    }

    return (
        <B2CLayout>
            {/* Workspace Header */}
            <div style={{
                backgroundColor: 'white',
                borderRadius: '16px',
                padding: '32px',
                marginBottom: '32px',
                border: '1px solid #E5E7EB'
            }}>
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    flexWrap: 'wrap',
                    gap: '20px'
                }}>
                    <div style={{ flex: 1, minWidth: '300px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                            <h1 style={{
                                fontSize: '32px',
                                fontWeight: '700',
                                color: '#111827',
                                margin: 0
                            }}>
                                {workspace.name}
                            </h1>
                            <span style={{
                                padding: '4px 12px',
                                borderRadius: '9999px',
                                fontSize: '12px',
                                fontWeight: '600',
                                backgroundColor: workspace.type === 'personal' ? '#10B98120' : '#6366F120',
                                color: workspace.type === 'personal' ? '#10B981' : '#6366F1'
                            }}>
                                {workspace.type === 'personal' ? 'Personal' : 'Team'}
                            </span>
                        </div>
                        <p style={{
                            fontSize: '16px',
                            color: '#6B7280',
                            margin: '0 0 16px 0',
                            lineHeight: '1.6'
                        }}>
                            {workspace.description || 'No description provided'}
                        </p>
                        <div style={{
                            display: 'flex',
                            gap: '24px',
                            fontSize: '14px',
                            color: '#6B7280'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span>👥</span>
                                <span>{workspace.member_count} {workspace.member_count === 1 ? 'member' : 'members'}</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span>📁</span>
                                <span>{projects.length} {projects.length === 1 ? 'project' : 'projects'}</span>
                            </div>
                        </div>
                    </div>

                    <button
                        onClick={() => setShowCreateProjectModal(true)}
                        style={{
                            padding: '12px 24px',
                            borderRadius: '10px',
                            border: 'none',
                            background: 'linear-gradient(135deg, #10B981 0%, #059 669 100%)',
                            color: 'white',
                            fontSize: '14px',
                            fontWeight: '600',
                            cursor: 'pointer',
                            boxShadow: '0 4px 12px rgba(16, 185, 129, 0.4)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                        }}
                    >
                        <span>➕</span>
                        <span>New Project</span>
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div style={{
                borderBottom: '2px solid #E5E7EB',
                marginBottom: '28px'
            }}>
                <div style={{ display: 'flex', gap: '8px' }}>
                    {['projects', 'tasks', 'members', 'settings'].map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            style={{
                                padding: '12px 24px',
                                border: 'none',
                                borderBottom: activeTab === tab ? '3px solid #6366F1' : '3px solid transparent',
                                backgroundColor: 'transparent',
                                color: activeTab === tab ? '#6366F1' : '#6B7280',
                                fontSize: '15px',
                                fontWeight: activeTab === tab ? '600' : '500',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                textTransform: 'capitalize'
                            }}
                        >
                            {tab}
                        </button>
                    ))}
                </div>
            </div>

            {/* Tab Content */}
            {activeTab === 'projects' && (
                projects.length > 0 ? (
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
                        gap: '20px'
                    }}>
                        {projects.map((project) => (
                            <ProjectCard
                                key={project.id}
                                project={project}
                                workspaceId={workspaceId}
                            />
                        ))}
                    </div>
                ) : (
                    <EmptyState
                        icon="📁"
                        title="No projects yet"
                        description="Create your first project to start organizing your work"
                        actionLabel="Create Project"
                        onAction={() => setShowCreateProjectModal(true)}
                    />
                )
            )}

            {activeTab === 'tasks' && (
                <EmptyState
                    icon="✓"
                    title="Tasks view"
                    description="Task management coming soon"
                />
            )}

            {activeTab === 'members' && (
                <EmptyState
                    icon="👥"
                    title="Members"
                    description="Member management coming soon"
                />
            )}

            {activeTab === 'settings' && (
                <div style={{
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    padding: '24px',
                    border: '1px solid #E5E7EB'
                }}>
                    <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px' }}>
                        Workspace Settings
                    </h3>
                    <p style={{ color: '#6B7280' }}>
                        Settings page coming soon
                    </p>
                </div>
            )}

            {/* Create Project Modal */}
            <CreateProjectModal
                isOpen={showCreateProjectModal}
                onClose={() => setShowCreateProjectModal(false)}
                workspaceId={workspaceId}
                onSuccess={handleProjectCreated}
            />
        </B2CLayout>
    );
};

export default WorkspacePage;

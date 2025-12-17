import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import B2CLayout from '../layouts/B2CLayout';
import TodoItem from '../components/TodoItem';
import EmptyState from '../components/EmptyState';
import CreateTodoModal from '../components/CreateTodoModal';
import WorkspaceMembersTab from '../components/WorkspaceMembersTab';
import { WorkspaceCardSkeleton } from '../components/LoadingSkeletons';
import b2cWorkspaceClient from '../../../../core/api/b2cWorkspaceClient';

const WorkspacePage = () => {
    const { workspaceId } = useParams();
    const navigate = useNavigate();
    const [workspace, setWorkspace] = useState(null);
    const [todos, setTodos] = useState([]);
    const [members, setMembers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateTodoModal, setShowCreateTodoModal] = useState(false);
    const [activeTab, setActiveTab] = useState('tasks');

    useEffect(() => {
        loadWorkspace();
    }, [workspaceId]);

    const loadWorkspace = async () => {
        setLoading(true);
        try {
            const data = await b2cWorkspaceClient.getWorkspaceDetails(workspaceId);
            setWorkspace(data);
            setMembers(data.members || []);

            // Fetch todos
            try {
                const todosData = await b2cWorkspaceClient.getTodos(workspaceId);
                setTodos(todosData || []);
            } catch (err) {
                console.error('Failed to load tasks:', err);
            }
        } catch (error) {
            console.error('Failed to load workspace:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleTodoCreated = (newTodo) => {
        setTodos([newTodo, ...todos]);
    };

    const handleToggleTodo = async (todo) => {
        // Optimistic update
        const updatedTodos = todos.map(t =>
            t.id === todo.id ? { ...t, is_completed: !t.is_completed } : t
        );
        setTodos(updatedTodos);

        try {
            await b2cWorkspaceClient.toggleTodo(workspaceId, todo.id, !todo.is_completed);
        } catch (error) {
            console.error('Failed to update task:', error);
            // Revert on error
            loadWorkspace();
        }
    };

    const handleDeleteTodo = async (todoId) => {
        if (!window.confirm('Are you sure you want to delete this task?')) return;

        // Optimistic update
        setTodos(todos.filter(t => t.id !== todoId));

        try {
            await b2cWorkspaceClient.deleteTodo(workspaceId, todoId);
        } catch (error) {
            console.error('Failed to delete task:', error);
            loadWorkspace();
        }
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
                                <span>✅</span>
                                <span>{todos.length} {todos.length === 1 ? 'task' : 'tasks'}</span>
                            </div>
                        </div>
                    </div>

                    <button
                        onClick={() => setShowCreateTodoModal(true)}
                        style={{
                            padding: '12px 24px',
                            borderRadius: '10px',
                            border: 'none',
                            background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
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
                        <span>New Task</span>
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div style={{
                borderBottom: '2px solid #E5E7EB',
                marginBottom: '28px'
            }}>
                <div style={{ display: 'flex', gap: '8px' }}>
                    {['tasks', 'members', 'settings'].map((tab) => (
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
            {activeTab === 'tasks' && (
                todos.length > 0 ? (
                    <div>
                        {todos.map((todo) => (
                            <TodoItem
                                key={todo.id}
                                todo={todo}
                                onToggle={handleToggleTodo}
                                onDelete={handleDeleteTodo}
                            />
                        ))}
                    </div>
                ) : (
                    <EmptyState
                        icon="✓"
                        title="No tasks yet"
                        description="Add your first task to get started"
                        actionLabel="Create Task"
                        onAction={() => setShowCreateTodoModal(true)}
                    />
                )
            )}

            {activeTab === 'members' && workspace && (
                <WorkspaceMembersTab
                    workspace={workspace}
                    members={members}
                    onMembersUpdated={loadWorkspace}
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

            {/* Create Todo Modal */}
            <CreateTodoModal
                isOpen={showCreateTodoModal}
                onClose={() => setShowCreateTodoModal(false)}
                workspaceId={workspaceId}
                onSuccess={handleTodoCreated}
            />
        </B2CLayout>
    );
};

export default WorkspacePage;

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AdminLayout from '../../../b2b/web/layouts/AdminLayout';
import { projectsApi, tasksApi } from '../../../../core/api/projectsClient';

const ProjectDetailPage = () => {
    const { projectId } = useParams();
    const navigate = useNavigate();
    const [project, setProject] = useState(null);
    const [tasks, setTasks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [showCreateModal, setShowCreateModal] = useState(false);

    useEffect(() => {
        loadData();
    }, [projectId]);

    const loadData = async () => {
        try {
            setLoading(true);
            const [projectData, tasksData] = await Promise.all([
                projectsApi.get(projectId),
                tasksApi.list({ project_id: projectId })
            ]);
            setProject(projectData);
            setTasks(tasksData);
        } catch (err) {
            setError('Failed to load project');
        } finally {
            setLoading(false);
        }
    };

    const filteredTasks = statusFilter === 'all'
        ? tasks
        : tasks.filter(t => t.status === statusFilter);

    const getStatusCounts = () => {
        return {
            todo: tasks.filter(t => t.status === 'todo').length,
            in_progress: tasks.filter(t => t.status === 'in_progress').length,
            done: tasks.filter(t => t.status === 'done').length
        };
    };

    if (loading) {
        return (
            <AdminLayout title="Project" subtitle="Loading...">
                <div style={{ padding: '48px', textAlign: 'center' }}>
                    <p style={{ color: '#666' }}>Loading project...</p>
                </div>
            </AdminLayout>
        );
    }

    if (!project) {
        return (
            <AdminLayout title="Project" subtitle="Not found">
                <div style={{ padding: '48px', textAlign: 'center' }}>
                    <p style={{ color: '#666' }}>Project not found</p>
                    <button onClick={() => navigate('/projects')} style={{
                        marginTop: '16px',
                        padding: '8px 16px',
                        backgroundColor: '#4f46e5',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer'
                    }}>
                        Back to Projects
                    </button>
                </div>
            </AdminLayout>
        );
    }

    const statusCounts = getStatusCounts();

    return (
        <AdminLayout title={project.name} subtitle={project.description || 'Project tasks'}>
            <div style={{ padding: '24px' }}>
                {error && (
                    <div style={{ padding: '12px', backgroundColor: '#fee2e2', color: '#b91c1c', borderRadius: '8px', marginBottom: '16px' }}>
                        {error}
                    </div>
                )}

                {/* Stats Cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
                    <div style={{ padding: '16px', backgroundColor: 'white', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                        <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Todo</div>
                        <div style={{ fontSize: '24px', fontWeight: '700', color: '#3b82f6' }}>{statusCounts.todo}</div>
                    </div>
                    <div style={{ padding: '16px', backgroundColor: 'white', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                        <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>In Progress</div>
                        <div style={{ fontSize: '24px', fontWeight: '700', color: '#f59e0b' }}>{statusCounts.in_progress}</div>
                    </div>
                    <div style={{ padding: '16px', backgroundColor: 'white', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                        <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Done</div>
                        <div style={{ fontSize: '24px', fontWeight: '700', color: '#10b981' }}>{statusCounts.done}</div>
                    </div>
                </div>

                {/* Task Controls */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <div style={{ display: 'flex', gap: '8px' }}>
                        {['all', 'todo', 'in_progress', 'done'].map(status => (
                            <button
                                key={status}
                                onClick={() => setStatusFilter(status)}
                                style={{
                                    padding: '8px 16px',
                                    borderRadius: '6px',
                                    border: '1px solid #d1d5db',
                                    backgroundColor: statusFilter === status ? '#4f46e5' : 'white',
                                    color: statusFilter === status ? 'white' : '#374151',
                                    fontSize: '14px',
                                    fontWeight: '500',
                                    cursor: 'pointer'
                                }}
                            >
                                {status === 'all' ? 'All' : status.replace('_', ' ')}
                            </button>
                        ))}
                    </div>
                    <button
                        onClick={() => setShowCreateModal(true)}
                        style={{
                            padding: '8px 16px',
                            backgroundColor: '#4f46e5',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            fontSize: '14px',
                            fontWeight: '500',
                            cursor: 'pointer'
                        }}
                    >
                        + New Task
                    </button>
                </div>

                {/* Tasks List */}
                {filteredTasks.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '48px', backgroundColor: '#f9fafb', borderRadius: '8px' }}>
                        <p style={{ color: '#6b7280' }}>
                            {statusFilter === 'all' ? 'No tasks yet. Create one to get started!' : `No ${statusFilter.replace('_', ' ')} tasks`}
                        </p>
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {filteredTasks.map(task => (
                            <div
                                key={task.id}
                                onClick={() => navigate(`/tasks/${task.id}`)}
                                style={{
                                    padding: '16px',
                                    backgroundColor: 'white',
                                    borderRadius: '8px',
                                    border: '1px solid #e5e7eb',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)'}
                                onMouseLeave={(e) => e.currentTarget.style.boxShadow = 'none'}
                            >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                                    <div style={{ flex: 1 }}>
                                        <h4 style={{ margin: '0 0 8px 0', fontSize: '16px', fontWeight: '600', color: '#111827' }}>
                                            {task.title}
                                        </h4>
                                        {task.description && (
                                            <p style={{ margin: 0, fontSize: '14px', color: '#6b7280' }}>
                                                {task.description}
                                            </p>
                                        )}
                                    </div>
                                    <span style={{
                                        padding: '4px 12px',
                                        borderRadius: '12px',
                                        fontSize: '12px',
                                        fontWeight: '500',
                                        whiteSpace: 'nowrap',
                                        marginLeft: '16px',
                                        backgroundColor:
                                            task.status === 'done' ? '#d1fae5' :
                                                task.status === 'in_progress' ? '#fef3c7' : '#dbeafe',
                                        color:
                                            task.status === 'done' ? '#047857' :
                                                task.status === 'in_progress' ? '#b45309' : '#1e40af'
                                    }}>
                                        {task.status.replace('_', ' ')}
                                    </span>
                                </div>
                                {task.due_date && (
                                    <div style={{ marginTop: '8px', fontSize: '12px', color: '#9ca3af' }}>
                                        Due: {new Date(task.due_date).toLocaleDateString()}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}

                {showCreateModal && (
                    <CreateTaskModal
                        projectId={projectId}
                        onClose={() => setShowCreateModal(false)}
                        onSuccess={() => {
                            setShowCreateModal(false);
                            loadData();
                        }}
                    />
                )}
            </div>
        </AdminLayout>
    );
};

const CreateTaskModal = ({ projectId, onClose, onSuccess }) => {
    const [formData, setFormData] = useState({ title: '', description: '', due_date: '' });
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            setSaving(true);
            setError('');
            await tasksApi.create({
                project_id: projectId,
                ...formData,
                due_date: formData.due_date || null
            });
            onSuccess();
        } catch (err) {
            setError(err.message);
        } finally {
            setSaving(false);
        }
    };

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
        }}>
            <div style={{
                backgroundColor: 'white',
                borderRadius: '8px',
                padding: '24px',
                width: '100%',
                maxWidth: '500px',
                boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)'
            }}>
                <h3 style={{ margin: '0 0 16px 0', fontSize: '18px', fontWeight: '600' }}>Create New Task</h3>

                {error && (
                    <div style={{ padding: '12px', backgroundColor: '#fee2e2', color: '#b91c1c', borderRadius: '6px', marginBottom: '16px', fontSize: '14px' }}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: '16px' }}>
                        <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                            Task Title
                        </label>
                        <input
                            type="text"
                            value={formData.title}
                            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                            required
                            placeholder="e.g., Design landing page"
                            style={{
                                width: '100%',
                                padding: '8px 12px',
                                borderRadius: '6px',
                                border: '1px solid #d1d5db',
                                fontSize: '14px'
                            }}
                        />
                    </div>

                    <div style={{ marginBottom: '16px' }}>
                        <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                            Description (optional)
                        </label>
                        <textarea
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            rows={3}
                            placeholder="Describe the task..."
                            style={{
                                width: '100%',
                                padding: '8px 12px',
                                borderRadius: '6px',
                                border: '1px solid #d1d5db',
                                fontSize: '14px',
                                fontFamily: 'inherit',
                                resize: 'vertical'
                            }}
                        />
                    </div>

                    <div style={{ marginBottom: '24px' }}>
                        <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                            Due Date (optional)
                        </label>
                        <input
                            type="date"
                            value={formData.due_date}
                            onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                            style={{
                                width: '100%',
                                padding: '8px 12px',
                                borderRadius: '6px',
                                border: '1px solid #d1d5db',
                                fontSize: '14px'
                            }}
                        />
                    </div>

                    <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                        <button
                            type="button"
                            onClick={onClose}
                            style={{
                                padding: '8px 16px',
                                borderRadius: '6px',
                                border: '1px solid #d1d5db',
                                backgroundColor: 'white',
                                color: '#374151',
                                fontSize: '14px',
                                fontWeight: '500',
                                cursor: 'pointer'
                            }}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={saving}
                            style={{
                                padding: '8px 16px',
                                borderRadius: '6px',
                                border: 'none',
                                backgroundColor: '#4f46e5',
                                color: 'white',
                                fontSize: '14px',
                                fontWeight: '500',
                                cursor: saving ? 'not-allowed' : 'pointer',
                                opacity: saving ? 0.7 : 1
                            }}
                        >
                            {saving ? 'Creating...' : 'Create Task'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default ProjectDetailPage;

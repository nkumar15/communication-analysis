import React from 'react';
import { useNavigate } from 'react-router-dom';

const ProjectCard = ({ project, workspaceId, onClick }) => {
    const navigate = useNavigate();

    const handleClick = () => {
        if (onClick) {
            onClick(project);
        } else {
            navigate(`/workspace/${workspaceId}/project/${project.id}`);
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'completed': return '#10B981';
            case 'in_progress': return '#6366F1';
            case 'planning': return '#F59E0B';
            case 'on_hold': return '#6B7280';
            default: return '#9CA3AF';
        }
    };

    const getStatusLabel = (status) => {
        return status.split('_').map(word =>
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    };

    return (
        <div
            onClick={handleClick}
            style={{
                backgroundColor: '#FFFFFF',
                borderRadius: '12px',
                padding: '20px',
                border: '1px solid #E5E7EB',
                cursor: 'pointer',
                transition: 'box-shadow 0.2s, border-color 0.2s',
                height: '100%',
                display: 'flex',
                flexDirection: 'column'
            }}
            onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
                e.currentTarget.style.borderColor = '#6366F1';
            }}
            onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = 'none';
                e.currentTarget.style.borderColor = '#E5E7EB';
            }}
        >
            {/* Header with Status */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '12px'
            }}>
                <span style={{
                    padding: '4px 12px',
                    borderRadius: '9999px',
                    fontSize: '11px',
                    fontWeight: '600',
                    backgroundColor: `${getStatusColor(project.status)}20`,
                    color: getStatusColor(project.status),
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                }}>
                    {getStatusLabel(project.status)}
                </span>
                {project.due_date && (
                    <span style={{
                        fontSize: '12px',
                        color: '#6B7280',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                    }}>
                        <span>📅</span>
                        {new Date(project.due_date).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric'
                        })}
                    </span>
                )}
            </div>

            {/* Project Info */}
            <div style={{ flex: 1 }}>
                <h3 style={{
                    fontSize: '17px',
                    fontWeight: '600',
                    color: '#111827',
                    margin: '0 0 8px 0'
                }}>
                    {project.name}
                </h3>
                <p style={{
                    fontSize: '14px',
                    color: '#6B7280',
                    margin: '0',
                    lineHeight: '1.5',
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden'
                }}>
                    {project.description || 'No description'}
                </p>
            </div>

            {/* Progress Bar */}
            {project.progress !== undefined && (
                <div style={{ marginTop: '16px' }}>
                    <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '6px'
                    }}>
                        <span style={{
                            fontSize: '12px',
                            color: '#6B7280',
                            fontWeight: '500'
                        }}>
                            Progress
                        </span>
                        <span style={{
                            fontSize: '13px',
                            color: '#111827',
                            fontWeight: '600'
                        }}>
                            {project.progress}%
                        </span>
                    </div>
                    <div style={{
                        width: '100%',
                        height: '6px',
                        backgroundColor: '#E5E7EB',
                        borderRadius: '9999px',
                        overflow: 'hidden'
                    }}>
                        <div style={{
                            width: `${project.progress}%`,
                            height: '100%',
                            backgroundColor: getStatusColor(project.status),
                            borderRadius: '9999px',
                            transition: 'width 0.3s ease'
                        }} />
                    </div>
                </div>
            )}

            {/* Footer Stats */}
            {(project.task_count !== undefined || project.completed_tasks !== undefined) && (
                <div style={{
                    marginTop: '12px',
                    paddingTop: '12px',
                    borderTop: '1px solid #F3F4F6',
                    fontSize: '13px',
                    color: '#6B7280',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                }}>
                    <span>✓</span>
                    <span>
                        {project.completed_tasks || 0} / {project.task_count || 0} tasks completed
                    </span>
                </div>
            )}
        </div>
    );
};

export default ProjectCard;

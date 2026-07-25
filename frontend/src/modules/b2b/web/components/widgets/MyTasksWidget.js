import React from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Widget showing user's tasks with overdue indicator
 */
const MyTasksWidget = ({ tasksCount = 0, overdueCount = 0, projectsCount = 0, loading = false }) => {
    const navigate = useNavigate();

    if (loading) {
        return (
            <div style={cardStyle}>
                <h3 style={headerStyle}>📋 My Work</h3>
                <div style={{ textAlign: 'center', padding: '20px', color: '#6B7280' }}>
                    Loading...
                </div>
            </div>
        );
    }

    return (
        <div style={cardStyle}>
            <h3 style={headerStyle}>📋 My Work</h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginTop: '16px' }}>
                {/* Projects */}
                <div
                    onClick={() => navigate('/projects')}
                    style={statBoxStyle}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#EEF2FF'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#F9FAFB'}
                >
                    <div style={{ fontSize: '28px', fontWeight: '700', color: '#4F46E5' }}>
                        {projectsCount}
                    </div>
                    <div style={{ fontSize: '13px', color: '#6B7280' }}>Projects</div>
                </div>

                {/* Tasks */}
                <div
                    onClick={() => navigate('/projects')}
                    style={statBoxStyle}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#EEF2FF'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#F9FAFB'}
                >
                    <div style={{ fontSize: '28px', fontWeight: '700', color: '#10B981' }}>
                        {tasksCount}
                    </div>
                    <div style={{ fontSize: '13px', color: '#6B7280' }}>Tasks</div>
                </div>

                {/* Overdue */}
                <div
                    onClick={() => navigate('/projects')}
                    style={{
                        ...statBoxStyle,
                        borderColor: overdueCount > 0 ? '#FCA5A5' : '#E5E7EB',
                        backgroundColor: overdueCount > 0 ? '#FEF2F2' : '#F9FAFB'
                    }}
                    onMouseEnter={(e) => {
                        if (overdueCount === 0) e.currentTarget.style.backgroundColor = '#EEF2FF';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = overdueCount > 0 ? '#FEF2F2' : '#F9FAFB';
                    }}
                >
                    <div style={{
                        fontSize: '28px',
                        fontWeight: '700',
                        color: overdueCount > 0 ? '#EF4444' : '#6B7280'
                    }}>
                        {overdueCount}
                    </div>
                    <div style={{ fontSize: '13px', color: overdueCount > 0 ? '#DC2626' : '#6B7280' }}>
                        Overdue
                    </div>
                </div>
            </div>
        </div>
    );
};

const cardStyle = {
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '24px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
    border: '1px solid #E5E7EB'
};

const headerStyle = {
    margin: 0,
    fontSize: '18px',
    fontWeight: '600',
    color: '#111827'
};

const statBoxStyle = {
    padding: '16px',
    backgroundColor: '#F9FAFB',
    borderRadius: '8px',
    border: '1px solid #E5E7EB',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s'
};

export default MyTasksWidget;

import React from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Quick actions widget based on user role
 */
const QuickActionsWidget = ({ actions = [], role = 'viewer' }) => {
    const navigate = useNavigate();

    const actionConfig = {
        invite_user: {
            label: 'Invite User',
            icon: '📧',
            path: '/invitations',
            primary: true
        },
        create_team: {
            label: 'Create Team',
            icon: '🏢',
            path: '/b2b/teams',
            primary: false
        },
        view_audit_logs: {
            label: 'Audit Logs',
            icon: '🔍',
            path: '/audit-logs',
            primary: false
        },
        view_teams: {
            label: 'View Teams',
            icon: '🏢',
            path: '/b2b/teams',
            primary: false
        }
    };

    const visibleActions = actions
        .filter(action => actionConfig[action])
        .map(action => ({ key: action, ...actionConfig[action] }));

    if (visibleActions.length === 0) return null;

    return (
        <div style={cardStyle}>
            <h3 style={headerStyle}>⚡ Quick Actions</h3>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '16px' }}>
                {visibleActions.map((action) => (
                    <button
                        key={action.key}
                        onClick={() => navigate(action.path)}
                        style={{
                            padding: '12px 20px',
                            borderRadius: '8px',
                            border: action.primary ? 'none' : '1px solid #E5E7EB',
                            backgroundColor: action.primary ? '#4F46E5' : 'white',
                            color: action.primary ? 'white' : '#374151',
                            fontSize: '14px',
                            fontWeight: '500',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                        }}
                        onMouseEnter={(e) => {
                            if (!action.primary) e.target.style.backgroundColor = '#F9FAFB';
                        }}
                        onMouseLeave={(e) => {
                            if (!action.primary) e.target.style.backgroundColor = 'white';
                        }}
                    >
                        <span>{action.icon}</span>
                        {action.label}
                    </button>
                ))}
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

export default QuickActionsWidget;

import React from 'react';
import { useNavigate } from 'react-router-dom';

const WorkspaceCard = ({ workspace, onClick }) => {
    const navigate = useNavigate();

    const handleClick = () => {
        if (onClick) {
            onClick(workspace);
        } else {
            navigate(`/workspace/${workspace.id}`);
        }
    };

    const getTypeColor = (type) => {
        return type === 'personal' ? '#10B981' : '#6366F1';
    };

    const getTypeLabel = (type) => {
        return type === 'personal' ? 'Personal' : 'Team';
    };

    return (
        <div
            onClick={handleClick}
            style={{
                backgroundColor: '#FFFFFF',
                borderRadius: '12px',
                padding: '24px',
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
            {/* Header */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '16px'
            }}>
                <span style={{
                    padding: '4px 12px',
                    borderRadius: '9999px',
                    fontSize: '12px',
                    fontWeight: '600',
                    backgroundColor: `${getTypeColor(workspace.type)}20`,
                    color: getTypeColor(workspace.type)
                }}>
                    {getTypeLabel(workspace.type)}
                </span>
                {workspace.role && (
                    <span style={{
                        fontSize: '12px',
                        color: '#6B7280',
                        fontWeight: '500'
                    }}>
                        {workspace.role}
                    </span>
                )}
            </div>

            {/* Workspace Info */}
            <div style={{ flex: 1 }}>
                <h3 style={{
                    fontSize: '18px',
                    fontWeight: '600',
                    color: '#111827',
                    margin: '0 0 8px 0'
                }}>
                    {workspace.name}
                </h3>
                <p style={{
                    fontSize: '14px',
                    color: '#6B7280',
                    margin: '0 0 16px 0',
                    lineHeight: '1.5'
                }}>
                    {workspace.description || 'No description provided'}
                </p>
            </div>

            {/* Footer Stats */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                paddingTop: '16px',
                borderTop: '1px solid #F3F4F6',
                fontSize: '13px',
                color: '#6B7280'
            }}>
                {workspace.member_count !== undefined && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>👥</span>
                        <span>{workspace.member_count} {workspace.member_count === 1 ? 'member' : 'members'}</span>
                    </div>
                )}

            </div>

            {/* Action Indicator */}
            <div style={{
                marginTop: '12px',
                display: 'flex',
                alignItems: 'center',
                color: '#6366F1',
                fontSize: '14px',
                fontWeight: '600'
            }}>
                <span>Open Workspace</span>
                <span style={{ marginLeft: '6px' }}>→</span>
            </div>
        </div>
    );
};

export default WorkspaceCard;

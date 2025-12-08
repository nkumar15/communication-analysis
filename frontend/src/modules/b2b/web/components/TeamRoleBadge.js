import React from 'react';

const TeamRoleBadge = ({ role }) => {
    const getRoleStyle = () => {
        switch (role.toLowerCase()) {
            case 'team_manager':
                return {
                    backgroundColor: '#EDE9FE',
                    color: '#7C3AED'
                };
            case 'team_member':
                return {
                    backgroundColor: '#DBEAFE',
                    color: '#2563EB'
                };
            case 'team_viewer':
                return {
                    backgroundColor: '#F3F4F6',
                    color: '#6B7280'
                };
            default:
                return {
                    backgroundColor: '#F3F4F6',
                    color: '#6B7280'
                };
        }
    };

    const getDisplayName = () => {
        switch (role.toLowerCase()) {
            case 'team_manager':
                return 'Manager';
            case 'team_member':
                return 'Member';
            case 'team_viewer':
                return 'Viewer';
            default:
                return role.replace('team_', '').charAt(0).toUpperCase() + role.replace('team_', '').slice(1);
        }
    };

    const style = getRoleStyle();

    return (
        <span style={{
            display: 'inline-block',
            padding: '2px 8px',
            borderRadius: '12px',
            fontSize: '12px',
            fontWeight: '500',
            ...style
        }}>
            {getDisplayName()}
        </span>
    );
};

export default TeamRoleBadge;

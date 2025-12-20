import React from 'react';

const RoleBadge = ({ role }) => {
    const getRoleStyle = () => {
        switch (role.toLowerCase()) {
            case 'owner':
                return {
                    backgroundColor: '#FEE2E2',
                    color: '#DC2626'
                };
            case 'admin':
                return {
                    backgroundColor: '#EDE9FE',
                    color: '#7C3AED'
                };
            case 'viewer':
                return {
                    backgroundColor: '#D1FAE5',
                    color: '#059669'
                };
            case 'field_manager':
            case 'manager': // Legacy support
                return {
                    backgroundColor: '#FEF3C7',
                    color: '#D97706'
                };
            case 'field_agent':
            case 'member': // Legacy support
                return {
                    backgroundColor: '#DBEAFE',
                    color: '#2563EB'
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
            case 'owner':
                return 'Owner';
            case 'admin':
                return 'Admin';
            case 'viewer':
                return 'Viewer';
            case 'field_manager':
            case 'manager':
                return 'Field Manager';
            case 'member':
                return 'Member';
            default:
                return role.charAt(0).toUpperCase() + role.slice(1);
        }
    };

    const style = getRoleStyle();

    return (
        <span style={{
            display: 'inline-block',
            padding: '4px 12px',
            borderRadius: '12px',
            fontSize: '13px',
            fontWeight: '500',
            ...style
        }}>
            {getDisplayName()}
        </span>
    );
};

export default RoleBadge;

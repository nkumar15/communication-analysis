import React from 'react';

const RoleBadge = ({ role }) => {
    const getRoleStyle = () => {
        switch (role.toLowerCase()) {
            case 'admin':
                return {
                    backgroundColor: '#EDE9FE',
                    color: '#7C3AED'
                };
            case 'manager':
                return {
                    backgroundColor: '#FEF3C7',
                    color: '#D97706'
                };
            case 'member':
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
            {role.charAt(0).toUpperCase() + role.slice(1)}
        </span>
    );
};

export default RoleBadge;

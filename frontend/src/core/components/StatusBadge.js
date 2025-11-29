import React from 'react';

const StatusBadge = ({ status, type = 'user' }) => {
    const getStatusStyle = () => {
        if (type === 'user') {
            // For users: status is boolean (is_active)
            const isActive = status === true || status === 'active';
            if (isActive) {
                return {
                    backgroundColor: '#D1FAE5',
                    color: '#059669',
                    text: 'Active'
                };
            } else {
                return {
                    backgroundColor: '#F3F4F6',
                    color: '#6B7280',
                    text: 'Inactive'
                };
            }
        } else {
            // For invitations: status is string (pending/accepted/expired)
            const statusStr = String(status).toLowerCase();
            switch (statusStr) {
                case 'pending':
                    return {
                        backgroundColor: '#FEF3C7',
                        color: '#D97706',
                        text: 'Pending'
                    };
                case 'accepted':
                    return {
                        backgroundColor: '#D1FAE5',
                        color: '#059669',
                        text: 'Accepted'
                    };
                case 'expired':
                    return {
                        backgroundColor: '#FEE2E2',
                        color: '#DC2626',
                        text: 'Expired'
                    };
                default:
                    return {
                        backgroundColor: '#F3F4F6',
                        color: '#6B7280',
                        text: status
                    };
            }
        }
    };

    const style = getStatusStyle();

    return (
        <span style={{
            display: 'inline-block',
            padding: '4px 12px',
            borderRadius: '12px',
            fontSize: '13px',
            fontWeight: '500',
            backgroundColor: style.backgroundColor,
            color: style.color
        }}>
            {style.text}
        </span>
    );
};

export default StatusBadge;

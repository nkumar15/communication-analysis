import React from 'react';

const StatCard = ({ icon, label, value, color = '#4F46E5' }) => {
    return (
        <div style={{
            backgroundColor: 'white',
            borderRadius: '8px',
            padding: '24px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            border: '1px solid #e5e7eb',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
        }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
            }}>
                <div style={{
                    width: '48px',
                    height: '48px',
                    borderRadius: '8px',
                    backgroundColor: `${color}15`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '24px'
                }}>
                    {icon}
                </div>
                <div style={{ flex: 1 }}>
                    <div style={{
                        fontSize: '28px',
                        fontWeight: '700',
                        color: '#111827',
                        lineHeight: '1'
                    }}>
                        {value}
                    </div>
                </div>
            </div>
            <div style={{
                fontSize: '14px',
                color: '#6B7280',
                fontWeight: '500'
            }}>
                {label}
            </div>
        </div>
    );
};

export default StatCard;

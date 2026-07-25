import React from 'react';

const EmptyState = ({ icon = '📭', title, description, actionLabel, onAction }) => {
    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '60px 24px',
            textAlign: 'center'
        }}>
            <div style={{
                fontSize: '64px',
                marginBottom: '16px',
                opacity: 0.8
            }}>
                {icon}
            </div>
            <h3 style={{
                fontSize: '20px',
                fontWeight: '600',
                color: '#111827',
                margin: '0 0 8px 0'
            }}>
                {title}
            </h3>
            <p style={{
                fontSize: '14px',
                color: '#6B7280',
                margin: '0 0 24px 0',
                maxWidth: '400px'
            }}>
                {description}
            </p>
            {onAction && actionLabel && (
                <button
                    onClick={onAction}
                    style={{
                        padding: '12px 24px',
                        borderRadius: '8px',
                        border: 'none',
                        backgroundColor: '#6366F1',
                        color: 'white',
                        fontSize: '14px',
                        fontWeight: '600',
                        cursor: 'pointer',
                        boxShadow: '0 2px 4px rgba(99, 102, 241, 0.3)',
                        transition: 'background-color 0.2s'
                    }}
                    onMouseEnter={(e) => e.target.style.backgroundColor = '#4F46E5'}
                    onMouseLeave={(e) => e.target.style.backgroundColor = '#6366F1'}
                >
                    {actionLabel}
                </button>
            )}
        </div>
    );
};

export default EmptyState;

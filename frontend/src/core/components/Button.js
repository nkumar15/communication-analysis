import React from 'react';

export const Button = ({
    children,
    onClick,
    disabled = false,
    variant = 'primary',
    size = 'md',
    className = '',
    style = {},
    type = 'button'
}) => {
    const baseStyle = {
        fontWeight: '600',
        borderRadius: '8px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        border: 'none',
        transition: 'background-color 0.2s',
        opacity: disabled ? 0.5 : 1,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
    };

    const variants = {
        primary: {
            backgroundColor: '#4f46e5',
            color: 'white',
        },
        outline: {
            backgroundColor: 'white',
            color: '#374151',
            border: '1px solid #d1d5db',
        },
        danger: {
            backgroundColor: '#dc2626',
            color: 'white',
        },
    };

    const sizes = {
        sm: { padding: '6px 12px', fontSize: '14px' },
        md: { padding: '8px 16px', fontSize: '16px' },
        lg: { padding: '12px 24px', fontSize: '18px' },
    };

    return (
        <button
            type={type}
            onClick={onClick}
            disabled={disabled}
            style={{
                ...baseStyle,
                ...variants[variant],
                ...sizes[size],
                ...style
            }}
            className={className}
        >
            {children}
        </button>
    );
};

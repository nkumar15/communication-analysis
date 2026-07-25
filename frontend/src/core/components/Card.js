import React from 'react';

export const Card = ({ children, className = '', style = {} }) => {
    return (
        <div style={{
            backgroundColor: 'white',
            borderRadius: '8px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
            ...style
        }} className={className}>
            {children}
        </div>
    );
};

export const CardHeader = ({ children, className = '', style = {} }) => {
    return (
        <div style={{
            padding: '24px',
            borderBottom: '1px solid #e5e7eb',
            ...style
        }} className={className}>
            {children}
        </div>
    );
};

export const CardTitle = ({ children, className = '', style = {} }) => {
    return (
        <h2 style={{
            fontSize: '24px',
            fontWeight: '700',
            color: '#111827',
            margin: 0,
            ...style
        }} className={className}>
            {children}
        </h2>
    );
};

export const CardContent = ({ children, className = '', style = {} }) => {
    return (
        <div style={{
            padding: '24px',
            ...style
        }} className={className}>
            {children}
        </div>
    );
};

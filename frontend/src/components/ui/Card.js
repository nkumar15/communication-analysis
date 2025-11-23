import React from 'react';

export const Card = ({ children, className = '' }) => {
    return (
        <div className={`bg-white rounded-lg shadow-lg ${className}`}>
            {children}
        </div>
    );
};

export const CardHeader = ({ children, className = '' }) => {
    return (
        <div className={`px-6 py-4 border-b border-gray-200 ${className}`}>
            {children}
        </div>
    );
};

export const CardTitle = ({ children, className = '' }) => {
    return (
        <h2 className={`text-2xl font-bold text-gray-900 ${className}`}>
            {children}
        </h2>
    );
};

export const CardContent = ({ children, className = '' }) => {
    return (
        <div className={`px-6 py-6 ${className}`}>
            {children}
        </div>
    );
};

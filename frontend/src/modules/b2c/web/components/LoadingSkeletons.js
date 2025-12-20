import React from 'react';

// Workspace Card Skeleton
export const WorkspaceCardSkeleton = () => {
    return (
        <div style={{
            backgroundColor: '#FFFFFF',
            borderRadius: '12px',
            padding: '24px',
            border: '1px solid #E5E7EB',
            height: '220px'
        }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginBottom: '16px'
            }}>
                <div style={{
                    width: '80px',
                    height: '24px',
                    backgroundColor: '#E5E7EB',
                    borderRadius: '9999px',
                    animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
                }} />
                <div style={{
                    width: '60px',
                    height: '16px',
                    backgroundColor: '#E5E7EB',
                    borderRadius: '4px',
                    animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                    animationDelay: '0.1s'
                }} />
            </div>
            <div style={{
                width: '70%',
                height: '24px',
                backgroundColor: '#E5E7EB',
                borderRadius: '4px',
                marginBottom: '12px',
                animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                animationDelay: '0.2s'
            }} />
            <div style={{
                width: '100%',
                height: '16px',
                backgroundColor: '#E5E7EB',
                borderRadius: '4px',
                marginBottom: '8px',
                animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                animationDelay: '0.3s'
            }} />
            <div style={{
                width: '85%',
                height: '16px',
                backgroundColor: '#E5E7EB',
                borderRadius: '4px',
                animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                animationDelay: '0.4s'
            }} />
        </div>
    );
};

// Dashboard Skeleton (B2C version)
export const B2CDashboardSkeleton = () => {
    return (
        <div>
            {/* Header skeleton */}
            <div style={{ marginBottom: '32px' }}>
                <div style={{
                    width: '200px',
                    height: '32px',
                    backgroundColor: '#E5E7EB',
                    borderRadius: '4px',
                    marginBottom: '12px',
                    animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
                }} />
                <div style={{
                    width: '300px',
                    height: '20px',
                    backgroundColor: '#E5E7EB',
                    borderRadius: '4px',
                    animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                    animationDelay: '0.1s'
                }} />
            </div>

            {/* Workspaces grid skeleton */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
                gap: '20px'
            }}>
                <WorkspaceCardSkeleton />
                <WorkspaceCardSkeleton />
                <WorkspaceCardSkeleton />
            </div>

            <style>{`
                @keyframes pulse {
                    0%, 100% {
                        opacity: 1;
                    }
                    50% {
                        opacity: 0.5;
                    }
                }
            `}</style>
        </div>
    );
};

// Project Card Skeleton
export const ProjectCardSkeleton = () => {
    return (
        <div style={{
            backgroundColor: '#FFFFFF',
            borderRadius: '12px',
            padding: '20px',
            border: '1px solid #E5E7EB'
        }}>
            <div style={{
                width: '60%',
                height: '20px',
                backgroundColor: '#E5E7EB',
                borderRadius: '4px',
                marginBottom: '12px',
                animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
            }} />
            <div style={{
                width: '100%',
                height: '16px',
                backgroundColor: '#E5E7EB',
                borderRadius: '4px',
                marginBottom: '8px',
                animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                animationDelay: '0.1s'
            }} />
            <div style={{
                width: '80%',
                height: '16px',
                backgroundColor: '#E5E7EB',
                borderRadius: '4px',
                animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                animationDelay: '0.2s'
            }} />
        </div>
    );
};

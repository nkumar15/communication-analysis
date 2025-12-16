import React from 'react';

// Platform-themed loading skeletons with purple pulse animation

export const StatCardSkeleton = () => {
    return (
        <div className="platform-stat-card" style={{ position: 'relative', overflow: 'hidden' }}>
            <div style={{
                width: '60%',
                height: '14px',
                backgroundColor: '#E5E7EB',
                borderRadius: '4px',
                marginBottom: '12px'
            }} className="skeleton-pulse" />
            <div style={{
                width: '40%',
                height: '32px',
                backgroundColor: '#E5E7EB',
                borderRadius: '4px'
            }} className="skeleton-pulse" />
        </div>
    );
};

export const TableSkeleton = ({ rows = 5 }) => {
    return (
        <div className="platform-card">
            {/* Table Header */}
            <div style={{
                display: 'flex',
                gap: '16px',
                padding: '12px 16px',
                borderBottom: '2px solid #E5E7EB'
            }}>
                {[1, 2, 3, 4].map((i) => (
                    <div
                        key={i}
                        style={{
                            flex: i === 1 ? 2 : 1,
                            height: '12px',
                            backgroundColor: '#E5E7EB',
                            borderRadius: '4px'
                        }}
                        className="skeleton-pulse"
                    />
                ))}
            </div>

            {/* Table Rows */}
            {Array.from({ length: rows }).map((_, idx) => (
                <div
                    key={idx}
                    style={{
                        display: 'flex',
                        gap: '16px',
                        padding: '16px',
                        borderBottom: '1px solid #F3F4F6'
                    }}
                >
                    {[1, 2, 3, 4].map((i) => (
                        <div
                            key={i}
                            style={{
                                flex: i === 1 ? 2 : 1,
                                height: '16px',
                                backgroundColor: '#E5E7EB',
                                borderRadius: '4px'
                            }}
                            className="skeleton-pulse"
                        />
                    ))}
                </div>
            ))}
        </div>
    );
};

export const DashboardSkeleton = () => {
    return (
        <div>
            {/* Stats Grid */}
            <div className="platform-stats-grid">
                <StatCardSkeleton />
                <StatCardSkeleton />
                <StatCardSkeleton />
                <StatCardSkeleton />
            </div>

            {/* Table */}
            <div style={{ marginTop: '24px' }}>
                <TableSkeleton rows={5} />
            </div>
        </div>
    );
};

export const TenantDetailsSkeleton = () => {
    return (
        <div>
            {/* Header */}
            <div className="platform-card" style={{ marginBottom: '24px' }}>
                <div style={{
                    width: '40%',
                    height: '32px',
                    backgroundColor: '#E5E7EB',
                    borderRadius: '4px',
                    marginBottom: '12px'
                }} className="skeleton-pulse" />
                <div style={{
                    width: '60%',
                    height: '16px',
                    backgroundColor: '#E5E7EB',
                    borderRadius: '4px'
                }} className="skeleton-pulse" />
            </div>

            {/* Stats */}
            <div className="platform-stats-grid">
                <StatCardSkeleton />
                <StatCardSkeleton />
                <StatCardSkeleton />
            </div>

            {/* Details */}
            <div className="platform-card" style={{ marginTop: '24px' }}>
                {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} style={{ marginBottom: '16px' }}>
                        <div style={{
                            width: '30%',
                            height: '12px',
                            backgroundColor: '#E5E7EB',
                            borderRadius: '4px',
                            marginBottom: '8px'
                        }} className="skeleton-pulse" />
                        <div style={{
                            width: '50%',
                            height: '16px',
                            backgroundColor: '#E5E7EB',
                            borderRadius: '4px'
                        }} className="skeleton-pulse" />
                    </div>
                ))}
            </div>
        </div>
    );
};

// Add CSS for pulse animation
const styles = `
@keyframes skeleton-pulse {
    0%, 100% {
        opacity: 1;
    }
    50% {
        opacity: 0.5;
    }
}

.skeleton-pulse {
    animation: skeleton-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
`;

// Inject styles
if (typeof document !== 'undefined') {
    const styleSheet = document.createElement('style');
    styleSheet.textContent = styles;
    document.head.appendChild(styleSheet);
}

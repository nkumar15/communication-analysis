import React from 'react';

// Base skeleton animation
const skeletonPulse = {
    animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
    '@keyframes pulse': {
        '0%, 100%': { opacity: 1 },
        '50%': { opacity: 0.5 }
    }
};

// Stat Card Skeleton
export const StatCardSkeleton = () => (
    <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '24px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        border: '1px solid #e5e7eb'
    }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
            <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '8px',
                backgroundColor: '#E5E7EB',
                animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
            }} />
            <div style={{
                width: '60px',
                height: '32px',
                borderRadius: '4px',
                backgroundColor: '#E5E7EB',
                animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
            }} />
        </div>
        <div style={{
            width: '100px',
            height: '16px',
            borderRadius: '4px',
            backgroundColor: '#E5E7EB',
            animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
        }} />
        <style>{`
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
        `}</style>
    </div>
);

// Table Row Skeleton
export const TableRowSkeleton = () => (
    <tr style={{ borderBottom: '1px solid #F3F4F6' }}>
        {[1, 2, 3, 4, 5, 6].map((col) => (
            <td key={col} style={{ padding: '16px 24px' }}>
                <div style={{
                    height: col === 1 ? '40px' : '16px',
                    width: col === 1 ? '200px' : col === 2 ? '180px' : col === 3 ? '80px' : col === 4 ? '70px' : col === 5 ? '130px' : '40px',
                    borderRadius: col === 1 ? '8px' : '4px',
                    backgroundColor: '#E5E7EB',
                    animation: `pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite ${col * 0.1}s`
                }} />
            </td>
        ))}
    </tr>
);

// Table Skeleton
export const TableSkeleton = ({ rows = 5 }) => (
    <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
                <tr style={{ borderTop: '1px solid #E5E7EB', borderBottom: '1px solid #E5E7EB', backgroundColor: '#F9FAFB' }}>
                    {['User', 'Email', 'Role', 'Status', 'Last Login', 'Actions'].map((header) => (
                        <th key={header} style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>
                            {header}
                        </th>
                    ))}
                </tr>
            </thead>
            <tbody>
                {Array.from({ length: rows }).map((_, idx) => (
                    <TableRowSkeleton key={idx} />
                ))}
            </tbody>
        </table>
        <style>{`
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
        `}</style>
    </div>
);

// Card Skeleton (for content areas)
export const CardSkeleton = () => (
    <div style={{
        backgroundColor: 'white',
        borderRadius: '12px',
        padding: '24px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        border: '1px solid #E5E7EB',
        marginBottom: '24px'
    }}>
        {/* Title */}
        <div style={{
            width: '200px',
            height: '24px',
            borderRadius: '4px',
            backgroundColor: '#E5E7EB',
            marginBottom: '16px',
            animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
        }} />

        {/* Content lines */}
        {[1, 2, 3].map((line) => (
            <div key={line} style={{
                width: line === 3 ? '60%' : '100%',
                height: '16px',
                borderRadius: '4px',
                backgroundColor: '#E5E7EB',
                marginBottom: '12px',
                animation: `pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite ${line * 0.1}s`
            }} />
        ))}

        <style>{`
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
        `}</style>
    </div>
);

// Dashboard Skeleton (complete page)
export const DashboardSkeleton = () => (
    <div style={{ padding: '32px', maxWidth: '1400px', margin: '0 auto' }}>
        {/* Stat Cards */}
        <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '20px',
            marginBottom: '32px'
        }}>
            {[1, 2, 3, 4].map((card) => (
                <StatCardSkeleton key={card} />
            ))}
        </div>

        {/* Main Card */}
        <CardSkeleton />

        {/* Another Section */}
        <CardSkeleton />
    </div>
);

// Invitations Page Skeleton
export const InvitationsPageSkeleton = () => (
    <div style={{ padding: '32px', maxWidth: '1400px', margin: '0 auto' }}>
        {/* Stat Cards */}
        <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '20px',
            marginBottom: '32px'
        }}>
            {[1, 2, 3, 4].map((card) => (
                <StatCardSkeleton key={card} />
            ))}
        </div>

        {/* Table Card */}
        <div style={{
            backgroundColor: 'white',
            borderRadius: '12px',
            padding: '24px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            border: '1px solid #E5E7EB'
        }}>
            <TableSkeleton rows={8} />
        </div>
    </div>
);

export default {
    StatCardSkeleton,
    TableRowSkeleton,
    TableSkeleton,
    CardSkeleton,
    DashboardSkeleton,
    InvitationsPageSkeleton
};

import React from 'react';
import AdminLayout from '../../../b2b/web/layouts/AdminLayout';
import { MOCK_INVESTIGATIONS, STATUS_COLORS, PRIORITY_COLORS } from '../mockData';

const InvestigationsPage = () => {
    const investigations = MOCK_INVESTIGATIONS;

    const getStatusBadge = (status) => (
        <span style={{
            padding: '4px 10px',
            borderRadius: '12px',
            fontSize: '12px',
            fontWeight: '500',
            backgroundColor: `${STATUS_COLORS[status]}20`,
            color: STATUS_COLORS[status],
            textTransform: 'capitalize'
        }}>
            {status.replace('_', ' ')}
        </span>
    );

    const getPriorityBadge = (priority) => (
        <span style={{
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: '600',
            backgroundColor: `${PRIORITY_COLORS[priority]}15`,
            color: PRIORITY_COLORS[priority],
            textTransform: 'uppercase'
        }}>
            {priority}
        </span>
    );

    return (
        <AdminLayout>
            <div style={{ padding: '24px' }}>
                <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <h1 style={{ fontSize: '24px', fontWeight: '700', color: '#1F2937', margin: 0 }}>
                            Investigations
                        </h1>
                        <p style={{ color: '#6B7280', marginTop: '4px' }}>
                            Track and manage compliance investigations
                        </p>
                    </div>
                    <button style={{
                        padding: '10px 20px',
                        backgroundColor: '#4F46E5',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        fontWeight: '500',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                    }}>
                        <span>+</span> New Investigation
                    </button>
                </div>

                {/* Investigation Cards */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
                    gap: '16px'
                }}>
                    {investigations.map((inv) => (
                        <div key={inv.id} style={{
                            backgroundColor: 'white',
                            borderRadius: '12px',
                            padding: '20px',
                            boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                            border: '1px solid #E5E7EB',
                            cursor: 'pointer',
                            transition: 'box-shadow 0.2s'
                        }}
                            onMouseEnter={(e) => e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)'}
                            onMouseLeave={(e) => e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)'}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                                <span style={{ fontSize: '12px', color: '#6B7280', fontFamily: 'monospace' }}>{inv.id}</span>
                                {getPriorityBadge(inv.priority)}
                            </div>

                            <h3 style={{ fontSize: '16px', fontWeight: '600', color: '#1F2937', margin: '0 0 12px 0' }}>
                                {inv.title}
                            </h3>

                            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                                {getStatusBadge(inv.status)}
                                <span style={{
                                    padding: '4px 10px',
                                    borderRadius: '12px',
                                    fontSize: '12px',
                                    backgroundColor: '#F3F4F6',
                                    color: '#374151'
                                }}>
                                    🌍 {inv.region}
                                </span>
                            </div>

                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '12px', borderTop: '1px solid #E5E7EB' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <div style={{
                                        width: '28px',
                                        height: '28px',
                                        borderRadius: '50%',
                                        backgroundColor: '#E5E7EB',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        fontSize: '12px'
                                    }}>
                                        👤
                                    </div>
                                    <span style={{ fontSize: '14px', color: '#374151' }}>{inv.assignee}</span>
                                </div>
                                <span style={{ fontSize: '13px', color: '#6B7280' }}>
                                    📧 {inv.communicationsCount} items
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </AdminLayout>
    );
};

export default InvestigationsPage;

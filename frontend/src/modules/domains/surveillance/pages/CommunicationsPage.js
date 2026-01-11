import React, { useState } from 'react';
import AdminLayout from '../../../b2b/web/layouts/AdminLayout';
import { MOCK_COMMUNICATIONS, STATUS_COLORS } from '../mockData';

const CommunicationsPage = () => {
    const [filter, setFilter] = useState('all');

    const communications = filter === 'all'
        ? MOCK_COMMUNICATIONS
        : MOCK_COMMUNICATIONS.filter(c => c.status === filter);

    const getStatusBadge = (status) => (
        <span style={{
            padding: '4px 8px',
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

    const getSensitivityBadge = (sensitivity) => {
        const colors = {
            'INTERNAL': '#6B7280',
            'CONFIDENTIAL': '#F59E0B',
            'RESTRICTED': '#EF4444',
            'TOP_SECRET': '#DC2626'
        };
        return (
            <span style={{
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '10px',
                fontWeight: '600',
                backgroundColor: `${colors[sensitivity] || '#6B7280'}15`,
                color: colors[sensitivity] || '#6B7280'
            }}>
                {sensitivity}
            </span>
        );
    };

    const getTypeIcon = (type) => {
        const icons = { email: '📧', chat: '💬', voice: '📞' };
        return icons[type] || '📄';
    };

    return (
        <AdminLayout>
            <div style={{ padding: '24px' }}>
                <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <h1 style={{ fontSize: '24px', fontWeight: '700', color: '#1F2937', margin: 0 }}>
                            Communications
                        </h1>
                        <p style={{ color: '#6B7280', marginTop: '4px' }}>
                            Review and analyze captured communications
                        </p>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                        {['all', 'flagged', 'pending', 'reviewed', 'cleared'].map(status => (
                            <button
                                key={status}
                                onClick={() => setFilter(status)}
                                style={{
                                    padding: '8px 16px',
                                    borderRadius: '8px',
                                    border: filter === status ? '2px solid #4F46E5' : '1px solid #E5E7EB',
                                    backgroundColor: filter === status ? '#EEF2FF' : 'white',
                                    color: filter === status ? '#4F46E5' : '#6B7280',
                                    cursor: 'pointer',
                                    fontWeight: '500',
                                    fontSize: '14px',
                                    textTransform: 'capitalize'
                                }}
                            >
                                {status}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Communications Table */}
                <div style={{
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                    border: '1px solid #E5E7EB',
                    overflow: 'hidden'
                }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ backgroundColor: '#F9FAFB' }}>
                                <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: '600', color: '#374151', fontSize: '14px' }}>Type</th>
                                <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: '600', color: '#374151', fontSize: '14px' }}>From</th>
                                <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: '600', color: '#374151', fontSize: '14px' }}>Subject</th>
                                <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: '600', color: '#374151', fontSize: '14px' }}>Region</th>
                                <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: '600', color: '#374151', fontSize: '14px' }}>Sensitivity</th>
                                <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: '600', color: '#374151', fontSize: '14px' }}>Status</th>
                                <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: '600', color: '#374151', fontSize: '14px' }}>Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            {communications.map((comm) => (
                                <tr key={comm.id} style={{ borderTop: '1px solid #E5E7EB' }}>
                                    <td style={{ padding: '12px 16px', fontSize: '20px' }}>{getTypeIcon(comm.type)}</td>
                                    <td style={{ padding: '12px 16px', color: '#1F2937', fontSize: '14px' }}>{comm.from}</td>
                                    <td style={{ padding: '12px 16px', color: '#1F2937', fontSize: '14px', maxWidth: '300px' }}>{comm.subject}</td>
                                    <td style={{ padding: '12px 16px', fontWeight: '500', color: '#6B7280', fontSize: '14px' }}>{comm.region}</td>
                                    <td style={{ padding: '12px 16px' }}>{getSensitivityBadge(comm.sensitivity)}</td>
                                    <td style={{ padding: '12px 16px' }}>{getStatusBadge(comm.status)}</td>
                                    <td style={{ padding: '12px 16px', color: '#6B7280', fontSize: '14px' }}>
                                        {new Date(comm.date).toLocaleDateString()}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </AdminLayout>
    );
};

export default CommunicationsPage;

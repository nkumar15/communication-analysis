import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AdminLayout from '../../../b2b/web/layouts/AdminLayout';
import b2bDomainClient from '../../../../core/api/b2bDomainClient';

const STATUS_COLORS = {
    'open': '#4F46E5',
    'in_review': '#F59E0B',
    'escalated': '#EF4444',
    'closed': '#10B981',
};

const PRIORITY_COLORS = {
    'low': '#6B7280',
    'medium': '#3B82F6',
    'high': '#F59E0B',
    'critical': '#EF4444',
};

const CaseListPage = () => {
    const navigate = useNavigate();
    const [cases, setCases] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchCases();
    }, []);

    const fetchCases = async () => {
        try {
            setLoading(true);
            const data = await b2bDomainClient.getCases();
            setCases(data);
            setError(null);
        } catch (err) {
            console.error('Failed to fetch cases:', err);
            setError('Failed to load cases. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const getStatusBadge = (status) => (
        <span style={{
            padding: '4px 10px',
            borderRadius: '12px',
            fontSize: '12px',
            fontWeight: '500',
            backgroundColor: `${STATUS_COLORS[status] || '#9CA3AF'}20`,
            color: STATUS_COLORS[status] || '#9CA3AF',
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
            backgroundColor: `${PRIORITY_COLORS[priority] || '#9CA3AF'}15`,
            color: PRIORITY_COLORS[priority] || '#9CA3AF',
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
                            Case Management
                        </h1>
                        <p style={{ color: '#6B7280', marginTop: '4px' }}>
                            Track and resolve compliance cases with full audit trails
                        </p>
                    </div>
                    <button
                        onClick={() => navigate('/b2b/surveillance/alerts')} // Redirect to alerts as cases usually start there
                        style={{
                            padding: '10px 20px',
                            backgroundColor: '#4F46E5',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontWeight: '500',
                        }}
                    >
                        + New Case (from Alert)
                    </button>
                </div>

                {loading ? (
                    <div style={{ display: 'flex', justifyContent: 'center', padding: '48px' }}>
                        <div className="spinner"></div>
                    </div>
                ) : error ? (
                    <div style={{ padding: '24px', backgroundColor: '#FEF2F2', color: '#B91C1C', borderRadius: '8px' }}>
                        {error}
                    </div>
                ) : cases.length === 0 ? (
                    <div style={{
                        textAlign: 'center',
                        padding: '48px',
                        backgroundColor: 'white',
                        borderRadius: '12px',
                        border: '1px dashed #D1D5DB'
                    }}>
                        <p style={{ color: '#6B7280' }}>No active cases found. High-risk alerts can be escalated into cases.</p>
                    </div>
                ) : (
                    /* Case Cards */
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
                        gap: '16px'
                    }}>
                        {cases.map((caseItem) => (
                            <div
                                key={caseItem.id}
                                onClick={() => navigate(`/b2b/surveillance/cases/${caseItem.id}`)}
                                style={{
                                    backgroundColor: 'white',
                                    borderRadius: '12px',
                                    padding: '20px',
                                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                                    border: '1px solid #E5E7EB',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s'
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
                                    e.currentTarget.style.borderColor = '#4F46E5';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)';
                                    e.currentTarget.style.borderColor = '#E5E7EB';
                                }}
                            >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                                    <span style={{ fontSize: '12px', color: '#6B7280', fontFamily: 'monospace' }}>
                                        #{caseItem.id.substring(0, 8)}
                                    </span>
                                    {getPriorityBadge(caseItem.priority)}
                                </div>

                                <h3 style={{ fontSize: '16px', fontWeight: '600', color: '#1F2937', margin: '0 0 12px 0' }}>
                                    {typeof caseItem.title === 'object' ? JSON.stringify(caseItem.title) : caseItem.title}
                                </h3>

                                <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                                    {getStatusBadge(caseItem.status)}
                                    <span style={{
                                        padding: '4px 10px',
                                        borderRadius: '12px',
                                        fontSize: '12px',
                                        backgroundColor: '#F3F4F6',
                                        color: '#374151'
                                    }}>
                                        🗓️ {new Date(caseItem.created_at).toLocaleDateString()}
                                    </span>
                                </div>

                                <div style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    paddingTop: '12px',
                                    borderTop: '1px solid #E5E7EB'
                                }}>
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
                                        <span style={{ fontSize: '14px', color: '#374151' }}>
                                            {caseItem.assigned_to_user_id ? 'Assigned' : 'Unassigned'}
                                        </span>
                                    </div>
                                    {caseItem.target_closure_date && (
                                        <span style={{ fontSize: '12px', color: '#EF4444' }}>
                                            SLA: {new Date(caseItem.target_closure_date).toLocaleDateString()}
                                        </span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </AdminLayout>
    );
};

export default CaseListPage;

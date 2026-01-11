import React from 'react';
import AdminLayout from '../../../b2b/web/layouts/AdminLayout';
import { MOCK_KPIS } from '../mockData';

const SurveillanceDashboardPage = () => {
    const kpis = MOCK_KPIS;

    const kpiCards = [
        { label: 'Total Communications', value: kpis.totalCommunications.toLocaleString(), icon: '💬', color: '#3B82F6' },
        { label: 'Flagged Items', value: kpis.flaggedItems, icon: '🚩', color: '#EF4444' },
        { label: 'Open Investigations', value: kpis.openInvestigations, icon: '🔍', color: '#F59E0B' },
        { label: 'Compliance Score', value: `${kpis.complianceScore}%`, icon: '✅', color: '#10B981' }
    ];

    return (
        <AdminLayout>
            <div style={{ padding: '24px' }}>
                <div style={{ marginBottom: '24px' }}>
                    <h1 style={{ fontSize: '24px', fontWeight: '700', color: '#1F2937', margin: 0 }}>
                        Surveillance Overview
                    </h1>
                    <p style={{ color: '#6B7280', marginTop: '4px' }}>
                        Monitor communications and investigations across all regions
                    </p>
                </div>

                {/* KPI Cards */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                    gap: '16px',
                    marginBottom: '32px'
                }}>
                    {kpiCards.map((kpi, index) => (
                        <div key={index} style={{
                            backgroundColor: 'white',
                            borderRadius: '12px',
                            padding: '20px',
                            boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                            border: '1px solid #E5E7EB'
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                <div>
                                    <p style={{ color: '#6B7280', fontSize: '14px', marginBottom: '4px' }}>{kpi.label}</p>
                                    <p style={{ fontSize: '28px', fontWeight: '700', color: '#1F2937', margin: 0 }}>
                                        {kpi.value}
                                    </p>
                                </div>
                                <span style={{ fontSize: '32px' }}>{kpi.icon}</span>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Alerts Today */}
                <div style={{
                    backgroundColor: '#FEF3C7',
                    border: '1px solid #F59E0B',
                    borderRadius: '8px',
                    padding: '16px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    marginBottom: '24px'
                }}>
                    <span style={{ fontSize: '24px' }}>⚠️</span>
                    <div>
                        <p style={{ fontWeight: '600', color: '#92400E', margin: 0 }}>
                            {kpis.alertsToday} new alerts today
                        </p>
                        <p style={{ color: '#A16207', fontSize: '14px', margin: 0 }}>
                            Review flagged communications requiring attention
                        </p>
                    </div>
                </div>

                {/* Quick Actions */}
                <div style={{
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    padding: '24px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                    border: '1px solid #E5E7EB'
                }}>
                    <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px' }}>Quick Actions</h2>
                    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                        <button style={{
                            padding: '10px 20px',
                            backgroundColor: '#4F46E5',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontWeight: '500'
                        }}>
                            📧 Review Flagged
                        </button>
                        <button style={{
                            padding: '10px 20px',
                            backgroundColor: '#059669',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontWeight: '500'
                        }}>
                            📋 Generate Report
                        </button>
                        <button style={{
                            padding: '10px 20px',
                            backgroundColor: '#7C3AED',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontWeight: '500'
                        }}>
                            🔍 New Investigation
                        </button>
                    </div>
                </div>
            </div>
        </AdminLayout>
    );
};

export default SurveillanceDashboardPage;

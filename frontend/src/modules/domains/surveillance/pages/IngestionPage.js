import React, { useState, useEffect } from 'react';
import AdminLayout from '../../../b2b/web/layouts/AdminLayout';
import b2bDomainClient from '../../../../core/api/b2bDomainClient';

const IngestionPage = () => {
    const [stats, setStats] = useState(null);
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [triggerModal, setTriggerModal] = useState(false);
    const [triggerDate, setTriggerDate] = useState('');
    const [triggering, setTriggering] = useState(false);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [statsRes, jobsRes] = await Promise.all([
                b2bDomainClient.getIngestionStats(),
                b2bDomainClient.getIngestionJobs()
            ]);
            setStats(statsRes);
            setJobs(jobsRes);
            setError(null);
        } catch (err) {
            console.error('Failed to fetch ingestion data:', err);
            if (err.message && err.message.includes('403')) {
                setError('You do not have permission to view ingestion data. This page is restricted to roles with ingestion access (e.g. Surveillance Chief).');
            } else {
                setError('Failed to load ingestion data. Please try again.');
            }
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        // Auto-refresh every 30 seconds
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, []);

    const handleTrigger = async () => {
        if (!triggerDate) return;

        setTriggering(true);
        try {
            await b2bDomainClient.triggerIngestion({ date: triggerDate });
            setTriggerModal(false);
            setTriggerDate('');
            fetchData();
        } catch (err) {
            alert(err.message || 'Failed to trigger ingestion');
        } finally {
            setTriggering(false);
        }
    };

    const handleRetry = async (jobId) => {
        if (!window.confirm('Are you sure you want to retry this job?')) return;

        try {
            await b2bDomainClient.retryIngestion(jobId);
            fetchData();
        } catch (err) {
            alert(err.message || 'Failed to retry job');
        }
    };

    const getStatusColor = (status) => {
        const colors = {
            completed: '#10B981',
            running: '#3B82F6',
            failed: '#EF4444',
            queued: '#F59E0B'
        };
        return colors[status] || '#6B7280';
    };

    const getStatusIcon = (status) => {
        const icons = {
            completed: '✅',
            running: '⏳',
            failed: '❌',
            queued: '📋'
        };
        return icons[status] || '❓';
    };

    if (loading && !stats) {
        return (
            <AdminLayout>
                <div style={{ padding: '24px', textAlign: 'center' }}>
                    <p>Loading ingestion data...</p>
                </div>
            </AdminLayout>
        );
    }

    return (
        <AdminLayout>
            <div style={{ padding: '24px' }}>
                {/* Header */}
                <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <h1 style={{ fontSize: '24px', fontWeight: '700', color: '#1F2937', margin: 0 }}>
                            Data Ingestion
                        </h1>
                        <p style={{ color: '#6B7280', marginTop: '4px' }}>
                            Monitor and manage daily communication data pipeline
                        </p>
                    </div>
                    <button
                        onClick={() => setTriggerModal(true)}
                        style={{
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
                        }}
                    >
                        <span>📥</span> Trigger Ingestion
                    </button>
                </div>

                {error && (
                    <div style={{
                        padding: '12px 16px',
                        backgroundColor: '#FEE2E2',
                        border: '1px solid #EF4444',
                        borderRadius: '8px',
                        color: '#DC2626',
                        marginBottom: '24px'
                    }}>
                        {error}
                    </div>
                )}

                {/* Stats Cards */}
                {stats && (
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                        gap: '16px',
                        marginBottom: '32px'
                    }}>
                        <StatCard label="Today's Volume" value={stats.today_messages.toLocaleString()} icon="📅" color="#3B82F6" />
                        <StatCard label="Total Messages" value={stats.total_messages.toLocaleString()} icon="📧" color="#10B981" />
                        <StatCard label="Completed Jobs" value={stats.completed_jobs} icon="✅" color="#10B981" />
                        <StatCard label="Failed Jobs" value={stats.failed_jobs} icon="❌" color="#EF4444" />
                        <StatCard label="Running Jobs" value={stats.running_jobs} icon="⏳" color="#F59E0B" />
                    </div>
                )}

                {/* Jobs Table */}
                <div style={{
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                    border: '1px solid #E5E7EB',
                    overflow: 'hidden'
                }}>
                    <div style={{ padding: '16px 20px', borderBottom: '1px solid #E5E7EB' }}>
                        <h2 style={{ fontSize: '18px', fontWeight: '600', margin: 0 }}>Recent Jobs</h2>
                    </div>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ backgroundColor: '#F9FAFB' }}>
                                <th style={thStyle}>Status</th>
                                <th style={thStyle}>Date</th>
                                <th style={thStyle}>File Path</th>
                                <th style={thStyle}>Processed</th>
                                <th style={thStyle}>Errors</th>
                                <th style={thStyle}>Started</th>
                                <th style={thStyle}>Duration</th>
                                <th style={thStyle}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {jobs.length === 0 ? (
                                <tr>
                                    <td colSpan={8} style={{ padding: '24px', textAlign: 'center', color: '#6B7280' }}>
                                        No ingestion jobs found. Trigger one to get started.
                                    </td>
                                </tr>
                            ) : (
                                jobs.map((job) => (
                                    <tr key={job.job_id} style={{ borderTop: '1px solid #E5E7EB' }}>
                                        <td style={tdStyle}>
                                            <span style={{
                                                display: 'inline-flex',
                                                alignItems: 'center',
                                                gap: '6px',
                                                padding: '4px 10px',
                                                borderRadius: '12px',
                                                fontSize: '12px',
                                                fontWeight: '500',
                                                backgroundColor: `${getStatusColor(job.status)}20`,
                                                color: getStatusColor(job.status)
                                            }}>
                                                {getStatusIcon(job.status)} {job.status}
                                            </span>
                                        </td>
                                        <td style={tdStyle}>{job.date}</td>
                                        <td style={{ ...tdStyle, maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                            {job.file_path}
                                        </td>
                                        <td style={tdStyle}>{job.processed_count.toLocaleString()}</td>
                                        <td style={{ ...tdStyle, color: job.error_count > 0 ? '#EF4444' : '#6B7280' }}>
                                            {job.error_count}
                                        </td>
                                        <td style={tdStyle}>
                                            {new Date(job.started_at).toLocaleString()}
                                        </td>
                                        <td style={tdStyle}>
                                            {job.completed_at
                                                ? `${Math.round((new Date(job.completed_at) - new Date(job.started_at)) / 1000)}s`
                                                : '-'}
                                        </td>
                                        <td style={tdStyle}>
                                            {job.status === 'failed' && (
                                                <button
                                                    onClick={() => handleRetry(job.job_id)}
                                                    style={{
                                                        padding: '4px 12px',
                                                        backgroundColor: '#FEF3C7',
                                                        color: '#92400E',
                                                        border: '1px solid #F59E0B',
                                                        borderRadius: '6px',
                                                        cursor: 'pointer',
                                                        fontSize: '12px',
                                                        fontWeight: '500'
                                                    }}
                                                >
                                                    🔄 Retry
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Trigger Modal */}
                {triggerModal && (
                    <div style={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        backgroundColor: 'rgba(0,0,0,0.5)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 1000
                    }}>
                        <div style={{
                            backgroundColor: 'white',
                            borderRadius: '12px',
                            padding: '24px',
                            width: '400px',
                            boxShadow: '0 20px 25px rgba(0,0,0,0.15)'
                        }}>
                            <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px' }}>
                                Trigger Ingestion
                            </h3>
                            <p style={{ color: '#6B7280', marginBottom: '16px' }}>
                                Enter the date (YYYYMMDD) of the dump file to ingest.
                            </p>
                            <input
                                type="text"
                                placeholder="e.g., 20231027"
                                value={triggerDate}
                                onChange={(e) => setTriggerDate(e.target.value)}
                                style={{
                                    width: '100%',
                                    padding: '10px 12px',
                                    border: '1px solid #E5E7EB',
                                    borderRadius: '8px',
                                    fontSize: '14px',
                                    marginBottom: '16px'
                                }}
                            />
                            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                                <button
                                    onClick={() => setTriggerModal(false)}
                                    style={{
                                        padding: '8px 16px',
                                        backgroundColor: 'white',
                                        border: '1px solid #E5E7EB',
                                        borderRadius: '6px',
                                        cursor: 'pointer'
                                    }}
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleTrigger}
                                    disabled={triggering || !triggerDate}
                                    style={{
                                        padding: '8px 16px',
                                        backgroundColor: '#4F46E5',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        cursor: 'pointer',
                                        fontWeight: '500'
                                    }}
                                >
                                    {triggering ? 'Triggering...' : 'Trigger'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </AdminLayout>
    );
};

const StatCard = ({ label, value, icon, color }) => (
    <div style={{
        backgroundColor: 'white',
        borderRadius: '12px',
        padding: '20px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        border: '1px solid #E5E7EB'
    }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
                <p style={{ color: '#6B7280', fontSize: '14px', marginBottom: '4px' }}>{label}</p>
                <p style={{ fontSize: '24px', fontWeight: '700', color: '#1F2937', margin: 0 }}>
                    {value}
                </p>
            </div>
            <span style={{ fontSize: '28px' }}>{icon}</span>
        </div>
    </div>
);

const thStyle = {
    padding: '12px 16px',
    textAlign: 'left',
    fontWeight: '600',
    color: '#374151',
    fontSize: '14px'
};

const tdStyle = {
    padding: '12px 16px',
    fontSize: '14px',
    color: '#1F2937'
};

export default IngestionPage;

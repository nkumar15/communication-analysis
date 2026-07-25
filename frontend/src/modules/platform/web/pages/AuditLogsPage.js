import { useState, useEffect } from 'react';
import platformApiService from '../../../../core/api/platformClient';
import { TableSkeleton } from '../components/LoadingSkeletons';

function AuditLogsPage() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({
        actionType: '',
        startDate: '',
        endDate: '',
        search: ''
    });
    const [pagination, setPagination] = useState({
        limit: 50,
        offset: 0,
        total: 0
    });

    useEffect(() => {
        fetchLogs();
    }, [filters, pagination.offset]);

    const fetchLogs = async () => {
        setLoading(true);
        try {
            // TODO: Replace with real API when available
            // const data = await platformApiService.getAuditLogs({
            //     ...filters,
            //     limit: pagination.limit,
            //     offset: pagination.offset
            // });

            // Mock data for now
            const mockLogs = [
                {
                    id: '1',
                    timestamp: new Date().toISOString(),
                    actor: 'admin@platform.com',
                    action: 'tenant.create',
                    resource: 'Acme Corp',
                    details: 'Created new tenant',
                    ip_address: '192.168.1.1'
                },
                {
                    id: '2',
                    timestamp: new Date(Date.now() - 3600000).toISOString(),
                    actor: 'admin@platform.com',
                    action: 'tenant.impersonate',
                    resource: 'Tech Startup',
                    details: 'Impersonated user admin@techstartup.com',
                    ip_address: '192.168.1.1'
                },
                {
                    id: '3',
                    timestamp: new Date(Date.now() - 7200000).toISOString(),
                    actor: 'system',
                    action: 'tenant.activation_sent',
                    resource: 'Beta Inc',
                    details: 'Activation email sent',
                    ip_address: 'system'
                }
            ];

            setLogs(mockLogs);
            setPagination(prev => ({ ...prev, total: mockLogs.length }));
        } catch (error) {
            console.error('Failed to fetch audit logs:', error);
        } finally {
            setLoading(false);
        }
    };

    const getActionColor = (action) => {
        if (action.includes('create')) return '#10B981';
        if (action.includes('delete')) return '#EF4444';
        if (action.includes('update')) return '#F59E0B';
        if (action.includes('impersonate')) return '#8B5CF6';
        return '#6B7280';
    };

    const formatTimestamp = (timestamp) => {
        return new Date(timestamp).toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const handleExport = () => {
        // TODO: Implement CSV export
        alert('Export functionality coming soon');
    };

    if (loading) {
        return (
            <div>
                <div className="platform-page-header">
                    <h1 className="platform-page-title">📋 Audit Logs</h1>
                </div>
                <TableSkeleton rows={10} />
            </div>
        );
    }

    return (
        <div>
            <div className="platform-page-header">
                <div>
                    <h1 className="platform-page-title">📋 Audit Logs</h1>
                    <p className="platform-page-subtitle">
                        Platform activity and system events
                    </p>
                </div>
                <button
                    onClick={handleExport}
                    className="platform-button"
                    style={{
                        backgroundColor: '#8B5CF6',
                        color: 'white',
                        padding: '10px 20px',
                        borderRadius: '8px',
                        border: 'none',
                        cursor: 'pointer',
                        fontSize: '14px',
                        fontWeight: '500'
                    }}
                >
                    Export CSV
                </button>
            </div>

            {/* Filters */}
            <div className="platform-card" style={{ marginBottom: '20px' }}>
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                    gap: '16px'
                }}>
                    <input
                        type="text"
                        placeholder="Search actor, resource..."
                        value={filters.search}
                        onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                        style={{
                            padding: '10px 12px',
                            border: '1px solid #E5E7EB',
                            borderRadius: '6px',
                            fontSize: '14px'
                        }}
                    />
                    <select
                        value={filters.actionType}
                        onChange={(e) => setFilters({ ...filters, actionType: e.target.value })}
                        style={{
                            padding: '10px 12px',
                            border: '1px solid #E5E7EB',
                            borderRadius: '6px',
                            fontSize: '14px'
                        }}
                    >
                        <option value="">All Actions</option>
                        <option value="create">Create</option>
                        <option value="update">Update</option>
                        <option value="delete">Delete</option>
                        <option value="impersonate">Impersonate</option>
                    </select>
                    <input
                        type="date"
                        value={filters.startDate}
                        onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
                        style={{
                            padding: '10px 12px',
                            border: '1px solid #E5E7EB',
                            borderRadius: '6px',
                            fontSize: '14px'
                        }}
                    />
                    <input
                        type="date"
                        value={filters.endDate}
                        onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
                        style={{
                            padding: '10px 12px',
                            border: '1px solid #E5E7EB',
                            borderRadius: '6px',
                            fontSize: '14px'
                        }}
                    />
                </div>
            </div>

            {/* Logs Table */}
            <div className="platform-card">
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                        <tr style={{ borderBottom: '2px solid #E5E7EB' }}>
                            <th style={styles.th}>Timestamp</th>
                            <th style={styles.th}>Actor</th>
                            <th style={styles.th}>Action</th>
                            <th style={styles.th}>Resource</th>
                            <th style={styles.th}>Details</th>
                            <th style={styles.th}>IP Address</th>
                        </tr>
                    </thead>
                    <tbody>
                        {logs.map((log) => (
                            <tr key={log.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                <td style={styles.td}>
                                    <span style={{ fontSize: '13px', color: '#6B7280' }}>
                                        {formatTimestamp(log.timestamp)}
                                    </span>
                                </td>
                                <td style={styles.td}>
                                    <span style={{ fontWeight: '500' }}>{log.actor}</span>
                                </td>
                                <td style={styles.td}>
                                    <span style={{
                                        padding: '4px 10px',
                                        borderRadius: '9999px',
                                        fontSize: '12px',
                                        fontWeight: '600',
                                        backgroundColor: `${getActionColor(log.action)}20`,
                                        color: getActionColor(log.action)
                                    }}>
                                        {log.action}
                                    </span>
                                </td>
                                <td style={styles.td}>{log.resource}</td>
                                <td style={styles.td}>
                                    <span style={{ fontSize: '13px', color: '#6B7280' }}>
                                        {log.details}
                                    </span>
                                </td>
                                <td style={styles.td}>
                                    <span style={{
                                        fontFamily: 'monospace',
                                        fontSize: '12px',
                                        color: '#6B7280'
                                    }}>
                                        {log.ip_address}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                {logs.length === 0 && (
                    <div style={{
                        textAlign: 'center',
                        padding: '40px',
                        color: '#6B7280'
                    }}>
                        No audit logs found
                    </div>
                )}
            </div>
        </div>
    );
}

const styles = {
    th: {
        textAlign: 'left',
        padding: '12px 16px',
        fontSize: '12px',
        fontWeight: '600',
        color: '#6B7280',
        textTransform: 'uppercase',
        letterSpacing: '0.5px'
    },
    td: {
        padding: '14px 16px',
        fontSize: '14px',
        color: '#374151'
    }
};

export default AuditLogsPage;

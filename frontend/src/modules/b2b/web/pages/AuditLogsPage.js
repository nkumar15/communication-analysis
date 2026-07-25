import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { TENANT_ROLES } from '../../constants/roles';
import AdminLayout from '../layouts/AdminLayout';
import apiService from '../../../../core/api/b2bClient';
import useAuth from '../../../../core/hooks/useAuth';
import { Card } from '../../../../core/components/Card';
import { Button } from '../../../../core/components/Button';
import { TableSkeleton } from '../../../../core/components/LoadingSkeleton';

const AuditLogsPage = () => {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [limit] = useState(20);
    const [filters, setFilters] = useState({
        event_type: '',
        start_date: '',
        end_date: ''
    });
    const [exporting, setExporting] = useState(false);

    const { hasRole, loading: authLoading } = useAuth();
    const navigate = useNavigate();

    useEffect(() => {
        if (!authLoading && !hasRole([TENANT_ROLES.OWNER, TENANT_ROLES.ADMIN])) {
            navigate('/dashboard');
        }
    }, [authLoading, hasRole, navigate]);

    useEffect(() => {
        fetchLogs();
    }, [page, filters]);

    const fetchLogs = async () => {
        setLoading(true);
        try {
            const data = await apiService.getAuditLogs({
                page,
                limit,
                ...filters
            });
            setLogs(data.items);
            setTotal(data.total);
        } catch (error) {
            console.error('Failed to fetch audit logs:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleExport = async () => {
        setExporting(true);
        try {
            const blob = await apiService.exportAuditLogs(filters);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `audit_logs_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Export failed:', error);
            alert('Failed to export logs');
        } finally {
            setExporting(false);
        }
    };

    const handleFilterChange = (e) => {
        const { name, value } = e.target;
        setFilters(prev => ({ ...prev, [name]: value }));
        setPage(1); // Reset to first page on filter change
    };

    if (authLoading) return <div>Loading...</div>;

    return (
        <AdminLayout title="Audit Logs" subtitle="View and export security events">
            <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>

                {/* Filters & Actions */}
                <Card className="mb-6">
                    <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
                        <div style={{ flex: 1, minWidth: '200px' }}>
                            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>
                                Event Type
                            </label>
                            <select
                                name="event_type"
                                value={filters.event_type}
                                onChange={handleFilterChange}
                                style={{
                                    width: '100%',
                                    padding: '8px 12px',
                                    borderRadius: '6px',
                                    border: '1px solid #D1D5DB'
                                }}
                            >
                                <option value="">All Events</option>
                                <option value="auth.login">Login</option>
                                <option value="user.invited">User Invited</option>
                                <option value="user.accepted_invite">Invitation Accepted</option>
                            </select>
                        </div>

                        <div style={{ flex: 1, minWidth: '200px' }}>
                            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>
                                Start Date
                            </label>
                            <input
                                type="date"
                                name="start_date"
                                value={filters.start_date}
                                onChange={handleFilterChange}
                                style={{
                                    width: '100%',
                                    padding: '8px 12px',
                                    borderRadius: '6px',
                                    border: '1px solid #D1D5DB'
                                }}
                            />
                        </div>

                        <div style={{ flex: 1, minWidth: '200px' }}>
                            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>
                                End Date
                            </label>
                            <input
                                type="date"
                                name="end_date"
                                value={filters.end_date}
                                onChange={handleFilterChange}
                                style={{
                                    width: '100%',
                                    padding: '8px 12px',
                                    borderRadius: '6px',
                                    border: '1px solid #D1D5DB'
                                }}
                            />
                        </div>

                        <Button
                            onClick={handleExport}
                            disabled={exporting || loading}
                            variant="secondary"
                        >
                            {exporting ? 'Exporting...' : '📥 Export CSV'}
                        </Button>
                    </div>
                </Card>

                {/* Logs Table */}
                <Card>
                    {loading ? (
                        <TableSkeleton rows={5} />
                    ) : logs.length === 0 ? (
                        <div style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>No audit logs found matching your criteria.</div>
                    ) : (
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid #E5E7EB', backgroundColor: '#F9FAFB' }}>
                                        <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Date</th>
                                        <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Event</th>
                                        <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Actor</th>
                                        <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Resource</th>
                                        <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Details</th>
                                        <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>IP Address</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {logs.map((log) => (
                                        <tr key={log.id} style={{ borderBottom: '1px solid #E5E7EB' }}>
                                            <td style={{ padding: '12px 16px', fontSize: '14px', color: '#111827' }}>
                                                {new Date(log.created_at).toLocaleString()}
                                            </td>
                                            <td style={{ padding: '12px 16px' }}>
                                                <span style={{
                                                    display: 'inline-block',
                                                    padding: '2px 8px',
                                                    borderRadius: '9999px',
                                                    fontSize: '12px',
                                                    fontWeight: '500',
                                                    backgroundColor: '#EEF2FF',
                                                    color: '#4F46E5'
                                                }}>
                                                    {log.event_type}
                                                </span>
                                            </td>
                                            <td style={{ padding: '12px 16px', fontSize: '14px', color: '#374151' }}>
                                                {log.actor_id ? (
                                                    <span title={log.actor_id}>User</span>
                                                ) : 'System'}
                                            </td>
                                            <td style={{ padding: '12px 16px', fontSize: '14px', color: '#374151' }}>
                                                {log.resource_type}
                                            </td>
                                            <td style={{ padding: '12px 16px', fontSize: '14px', color: '#374151', maxWidth: '300px' }}>
                                                <div style={{ whiteSpace: 'pre-wrap', fontSize: '12px', fontFamily: 'monospace' }}>
                                                    {JSON.stringify(log.details || {}, null, 2)}
                                                </div>
                                            </td>
                                            <td style={{ padding: '12px 16px', fontSize: '14px', color: '#6B7280' }}>
                                                {log.ip_address || '-'}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* Pagination */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', borderTop: '1px solid #E5E7EB' }}>
                        <div style={{ fontSize: '14px', color: '#6B7280' }}>
                            Showing {logs.length} of {total} results
                        </div>
                        <div style={{ display: 'flex', gap: '8px' }}>
                            <Button
                                variant="secondary"
                                size="sm"
                                onClick={() => setPage(p => Math.max(1, p - 1))}
                                disabled={page === 1 || loading}
                            >
                                Previous
                            </Button>
                            <Button
                                variant="secondary"
                                size="sm"
                                onClick={() => setPage(p => p + 1)}
                                disabled={logs.length < limit || loading}
                            >
                                Next
                            </Button>
                        </div>
                    </div>
                </Card>
            </div>
        </AdminLayout>
    );
};

export default AuditLogsPage;

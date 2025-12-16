import { useState, useEffect } from 'react';
import platformApiService from '../../../../core/api/platformClient';

function SystemHealthPage() {
    const [health, setHealth] = useState(null);
    const [errors, setErrors] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchHealthStatus();
    }, []);

    const fetchHealthStatus = async () => {
        setLoading(true);
        try {
            // TODO: Replace with real API when available
            // const [healthData, errorsData] = await Promise.all([
            //     platformApiService.getSystemHealth(),
            //     platformApiService.getRecentErrors()
            // ]);

            // Mock data for now
            const mockHealth = {
                services: {
                    b2b_api: { status: 'healthy', response_time: 45 },
                    b2c_api: { status: 'healthy', response_time: 38 },
                    platform_api: { status: 'healthy', response_time: 32 },
                    database: { status: 'healthy', connections: 12 },
                    firebase: { status: 'healthy', uptime: '99.9%' },
                    stripe: { status: 'healthy', last_check: new Date().toISOString() }
                },
                metrics: {
                    tenant_activation_rate: 95.2,
                    failed_logins_24h: 3,
                    subscription_failures_24h: 2,
                    email_delivery_rate: 98.7,
                    api_keys_active: 156
                }
            };

            const mockErrors = [
                {
                    id: '1',
                    timestamp: new Date(Date.now() - 7200000).toISOString(),
                    service: 'B2B',
                    severity: 'error',
                    message: 'Stripe API timeout during subscription creation',
                    trace_id: 'trace_abc123'
                },
                {
                    id: '2',
                    timestamp: new Date(Date.now() - 18000000).toISOString(),
                    service: 'B2C',
                    severity: 'warning',
                    message: 'Email delivery delayed',
                    trace_id: 'trace_def456'
                },
                {
                    id: '3',
                    timestamp: new Date(Date.now() - 32400000).toISOString(),
                    service: 'Platform',
                    severity: 'error',
                    message: 'Firebase authentication timeout',
                    trace_id: 'trace_ghi789'
                }
            ];

            setHealth(mockHealth);
            setErrors(mockErrors);
        } catch (error) {
            console.error('Failed to fetch health status:', error);
        } finally {
            setLoading(false);
        }
    };

    const getStatusColor = (status) => {
        return status === 'healthy' ? '#10B981' : '#EF4444';
    };

    const getStatusIcon = (status) => {
        return status === 'healthy' ? '✅' : '❌';
    };

    const getSeverityColor = (severity) => {
        switch (severity) {
            case 'error': return '#EF4444';
            case 'warning': return '#F59E0B';
            case 'info': return '#3B82F6';
            default: return '#6B7280';
        }
    };

    const formatTimestamp = (timestamp) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

        if (diffHours < 1) {
            const diffMins = Math.floor(diffMs / (1000 * 60));
            return `${diffMins}m ago`;
        } else if (diffHours < 24) {
            return `${diffHours}h ago`;
        } else {
            const diffDays = Math.floor(diffHours / 24);
            return `${diffDays}d ago`;
        }
    };

    if (loading) {
        return (
            <div>
                <div className="platform-page-header">
                    <h1 className="platform-page-title">🏥 System Health</h1>
                </div>
                <div style={{ textAlign: 'center', padding: '40px', color: '#9CA3AF' }}>
                    Loading health status...
                </div>
            </div>
        );
    }

    return (
        <div>
            <div className="platform-page-header">
                <div>
                    <h1 className="platform-page-title">🏥 System Health</h1>
                    <p className="platform-page-subtitle">
                        Platform-wide service status and recent issues
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '12px' }}>
                    <button
                        onClick={() => window.open('http://localhost:3000/grafana', '_blank')}
                        className="platform-button"
                        style={{
                            backgroundColor: '#F59E0B',
                            color: 'white',
                            padding: '10px 20px',
                            borderRadius: '8px',
                            border: 'none',
                            cursor: 'pointer',
                            fontSize: '14px',
                            fontWeight: '500'
                        }}
                    >
                        📊 Open Grafana
                    </button>
                    <button
                        onClick={() => window.open('http://localhost:16686', '_blank')}
                        className="platform-button"
                        style={{
                            backgroundColor: '#3B82F6',
                            color: 'white',
                            padding: '10px 20px',
                            borderRadius: '8px',
                            border: 'none',
                            cursor: 'pointer',
                            fontSize: '14px',
                            fontWeight: '500'
                        }}
                    >
                        🔍 Open Jaeger
                    </button>
                </div>
            </div>

            {/* Service Status */}
            <div className="platform-card" style={{ marginBottom: '24px' }}>
                <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '20px', color: '#E5E7EB' }}>
                    Services Status
                </h2>
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                    gap: '16px'
                }}>
                    {Object.entries(health.services).map(([service, data]) => (
                        <div
                            key={service}
                            style={{
                                padding: '16px',
                                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                                borderRadius: '8px',
                                border: `1px solid ${data.status === 'healthy' ? '#10B98130' : '#EF444430'}`
                            }}
                        >
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                marginBottom: '8px'
                            }}>
                                <span style={{
                                    fontSize: '14px',
                                    fontWeight: '600',
                                    color: '#E5E7EB',
                                    textTransform: 'capitalize'
                                }}>
                                    {service.replace(/_/g, ' ')}
                                </span>
                                <span style={{ fontSize: '20px' }}>
                                    {getStatusIcon(data.status)}
                                </span>
                            </div>
                            <div style={{
                                fontSize: '12px',
                                color: getStatusColor(data.status),
                                fontWeight: '600',
                                textTransform: 'uppercase'
                            }}>
                                {data.status}
                            </div>
                            {data.response_time && (
                                <div style={{ fontSize: '11px', color: '#9CA3AF', marginTop: '4px' }}>
                                    Response: {data.response_time}ms
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {/* Platform Metrics */}
            <div className="platform-card" style={{ marginBottom: '24px' }}>
                <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '20px', color: '#E5E7EB' }}>
                    Platform Metrics (Last 24 Hours)
                </h2>
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                    gap: '20px'
                }}>
                    <div>
                        <div style={{ fontSize: '12px', color: '#9CA3AF', marginBottom: '4px' }}>
                            Tenant Activation Rate
                        </div>
                        <div style={{ fontSize: '24px', fontWeight: '700', color: '#10B981' }}>
                            {health.metrics.tenant_activation_rate}%
                        </div>
                    </div>
                    <div>
                        <div style={{ fontSize: '12px', color: '#9CA3AF', marginBottom: '4px' }}>
                            Failed Login Attempts
                        </div>
                        <div style={{ fontSize: '24px', fontWeight: '700', color: '#F59E0B' }}>
                            {health.metrics.failed_logins_24h}
                        </div>
                    </div>
                    <div>
                        <div style={{ fontSize: '12px', color: '#9CA3AF', marginBottom: '4px' }}>
                            Subscription Failures
                        </div>
                        <div style={{ fontSize: '24px', fontWeight: '700', color: '#EF4444' }}>
                            {health.metrics.subscription_failures_24h}
                        </div>
                    </div>
                    <div>
                        <div style={{ fontSize: '12px', color: '#9CA3AF', marginBottom: '4px' }}>
                            Email Delivery Rate
                        </div>
                        <div style={{ fontSize: '24px', fontWeight: '700', color: '#10B981' }}>
                            {health.metrics.email_delivery_rate}%
                        </div>
                    </div>
                    <div>
                        <div style={{ fontSize: '12px', color: '#9CA3AF', marginBottom: '4px' }}>
                            Active API Keys
                        </div>
                        <div style={{ fontSize: '24px', fontWeight: '700', color: '#6366F1' }}>
                            {health.metrics.api_keys_active}
                        </div>
                    </div>
                </div>
            </div>

            {/* Recent Errors */}
            <div className="platform-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <h2 style={{ fontSize: '18px', fontWeight: '600', color: '#E5E7EB', margin: 0 }}>
                        Recent Application Errors
                    </h2>
                    <button
                        onClick={() => window.location.href = '/audit-logs'}
                        style={{
                            padding: '8px 16px',
                            borderRadius: '6px',
                            border: '1px solid #6366F1',
                            backgroundColor: 'transparent',
                            color: '#A78BFA',
                            fontSize: '13px',
                            fontWeight: '500',
                            cursor: 'pointer'
                        }}
                    >
                        View All Logs →
                    </button>
                </div>

                {errors.length > 0 ? (
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ borderBottom: '2px solid #374151' }}>
                                <th style={styles.th}>Time</th>
                                <th style={styles.th}>Service</th>
                                <th style={styles.th}>Severity</th>
                                <th style={styles.th}>Message</th>
                                <th style={styles.th}>Trace</th>
                            </tr>
                        </thead>
                        <tbody>
                            {errors.map((error) => (
                                <tr key={error.id} style={{ borderBottom: '1px solid #374151' }}>
                                    <td style={styles.td}>
                                        <span style={{ fontSize: '13px', color: '#9CA3AF' }}>
                                            {formatTimestamp(error.timestamp)}
                                        </span>
                                    </td>
                                    <td style={styles.td}>
                                        <span style={{ fontWeight: '500' }}>{error.service}</span>
                                    </td>
                                    <td style={styles.td}>
                                        <span style={{
                                            padding: '4px 10px',
                                            borderRadius: '9999px',
                                            fontSize: '11px',
                                            fontWeight: '600',
                                            backgroundColor: `${getSeverityColor(error.severity)}20`,
                                            color: getSeverityColor(error.severity),
                                            textTransform: 'uppercase'
                                        }}>
                                            {error.severity}
                                        </span>
                                    </td>
                                    <td style={styles.td}>
                                        <span style={{ fontSize: '13px' }}>{error.message}</span>
                                    </td>
                                    <td style={styles.td}>
                                        <button
                                            onClick={() => window.open(`http://localhost:16686/trace/${error.trace_id}`, '_blank')}
                                            style={{
                                                padding: '4px 12px',
                                                borderRadius: '4px',
                                                border: '1px solid #6366F1',
                                                backgroundColor: 'transparent',
                                                color: '#A78BFA',
                                                fontSize: '12px',
                                                cursor: 'pointer'
                                            }}
                                        >
                                            View
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                ) : (
                    <div style={{ textAlign: 'center', padding: '40px', color: '#9CA3AF' }}>
                        No recent errors - all systems running smoothly! 🎉
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
        color: '#9CA3AF',
        textTransform: 'uppercase',
        letterSpacing: '0.5px'
    },
    td: {
        padding: '14px 16px',
        fontSize: '14px',
        color: '#E5E7EB'
    }
};

export default SystemHealthPage;

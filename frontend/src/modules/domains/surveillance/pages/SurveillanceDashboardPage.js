import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, Grid, Chip, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Button, IconButton, Paper, Avatar, Tooltip, CircularProgress } from '@mui/material';
import {
    NotificationsActive,
    Gavel,
    Storage,
    ArrowForward,
    MoreVert,
    TrendingUp,
    Shield
} from '@mui/icons-material';
import AdminLayout from '../../../b2b/web/layouts/AdminLayout';
import b2bDomainClient from '../../../../core/api/b2bDomainClient';

const SurveillanceDashboardPage = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState([]);
    const [regions, setRegions] = useState([]);
    const [priorityAlerts, setPriorityAlerts] = useState([]);
    const [myCases, setMyCases] = useState([]);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [alertStats, caseStats, regStats, alerts, cases, ingestion] = await Promise.all([
                b2bDomainClient.getAlertStats(),
                b2bDomainClient.getCaseStats(),
                b2bDomainClient.getRegionalStats(),
                b2bDomainClient.getAlerts({ status: 'open', limit: 6 }),
                b2bDomainClient.getCases({ status: 'open', limit: 5 }),
                b2bDomainClient.getIngestionStats()
            ]);

            // Map Alert/Case stats to KPI cards
            setStats([
                {
                    title: 'Pending Alerts',
                    subtitle: 'Critical',
                    value: alertStats.high_risk_count || 0,
                    trend: `+${alertStats.open_count} total open`,
                    icon: <NotificationsActive fontSize="small" />,
                    color: 'error.main',
                    bgcolor: 'error.light',
                    path: '/b2b/surveillance/alerts'
                },
                {
                    title: 'Investigations',
                    subtitle: 'Active',
                    value: caseStats.open_count || 0,
                    trend: `${caseStats.in_review_count} in review`,
                    icon: <Gavel fontSize="small" />,
                    color: 'warning.main',
                    bgcolor: 'warning.light',
                    path: '/b2b/surveillance/cases'
                },
                {
                    title: 'Ingestion Lag',
                    subtitle: 'System',
                    value: ingestion.lag_ms ? `${ingestion.lag_ms}ms` : 'Healthy',
                    trend: ingestion.status || 'Stable',
                    icon: <Storage fontSize="small" />,
                    color: 'success.main',
                    bgcolor: 'success.light',
                    path: '/b2b/surveillance/ingestion'
                },
            ]);

            setRegions(regStats.length > 0 ? regStats : [
                { code: 'USA', label: 'Worldwide HQ', risk: 'Stable', color: 'success' }
            ]);

            setPriorityAlerts(alerts || []);
            setMyCases(cases || []);

        } catch (error) {
            console.error("Dashboard fetch failed:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    if (loading) {
        return (
            <AdminLayout title="Command Center">
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
                    <CircularProgress />
                    <Typography sx={{ ml: 2 }}>Loading Command Center...</Typography>
                </Box>
            </AdminLayout>
        );
    }

    return (
        <AdminLayout title="Command Center" subtitle="Strategic Intelligence & Multi-Channel Compliance Monitoring">
            <Box sx={{ p: 2, height: 'calc(100vh - 84px)', display: 'flex', flexDirection: 'column', overflow: 'hidden', bgcolor: '#f3f4f6' }}>

                {/* 1. TOP SUMMARY ROW (Strict 50/50 split, using full 100% width) */}
                <Box sx={{ display: 'flex', gap: 2, mb: 2, flexShrink: 0, width: '100%', minHeight: '120px' }}>

                    {/* Left 50%: Global Risk Monitor */}
                    <Paper sx={{ p: 2, flex: '0 0 calc(50% - 8px)', display: 'flex', flexDirection: 'column', justifyContent: 'center', minWidth: 0 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Shield color="primary" fontSize="small" />
                                <Typography variant="subtitle2" fontWeight="700" color="text.secondary" sx={{ fontSize: '0.75rem' }}>GLOBAL RISK MONITOR</Typography>
                            </Box>
                        </Box>

                        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'nowrap', width: '100%', justifyContent: 'space-between', px: 1 }}>
                            {regions.map((region) => (
                                <Tooltip title={`${region.label}: ${region.risk}`} key={region.code}>
                                    <Box sx={{
                                        flex: 1, // Let them expand to fill space
                                        maxWidth: 100, // But not too much
                                        height: 64, // Fixed height for squareness
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        borderRadius: 2,
                                        border: 1,
                                        borderColor: `${region.color}.main`,
                                        bgcolor: (theme) => `rgba(${region.color === 'success' ? '46, 125, 50' : region.color === 'warning' ? '237, 108, 2' : '2, 136, 209'}, 0.08)`,
                                        textAlign: 'center',
                                        position: 'relative',
                                        overflow: 'hidden',
                                        transition: 'transform 0.2s',
                                        '&:hover': { transform: 'scale(1.05)', boxShadow: 1 }
                                    }}>
                                        <Box sx={{ position: 'absolute', top: 0, left: 0, width: '100%', height: 4, bgcolor: `${region.color}.main` }} />
                                        <Box sx={{ position: 'relative', zIndex: 1 }}>
                                            <Typography variant="caption" fontWeight="700" color="text.secondary" display="block" sx={{ opacity: 0.8, fontSize: '0.7rem', mb: 0.5 }}>{region.code}</Typography>
                                            <Typography variant="body2" fontWeight="800" sx={{ color: `${region.color}.main`, lineHeight: 1, fontSize: '0.8rem' }}>{region.risk}</Typography>
                                        </Box>
                                    </Box>
                                </Tooltip>
                            ))}
                        </Box>
                    </Paper>

                    {/* Right 50%: KPI Cards (Shared split) */}
                    <Box sx={{ flex: '1 1 50%', display: 'flex', gap: 2, minWidth: 0 }}>
                        {stats.map((stat, index) => (
                            <Paper
                                key={index}
                                sx={{
                                    p: 2,
                                    flex: 1,
                                    cursor: 'pointer',
                                    position: 'relative',
                                    transition: 'transform 0.2s',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    justifyContent: 'center',
                                    minWidth: 0,
                                    '&:hover': { transform: 'translateY(-2px)', boxShadow: 2 }
                                }}
                                onClick={() => navigate(stat.path)}
                            >
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 0.5 }}>
                                    <Box sx={{ minWidth: 0 }}>
                                        <Typography variant="caption" color="text.secondary" fontWeight="700" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, fontSize: '0.65rem' }}>
                                            {stat.subtitle}
                                        </Typography>
                                        <Typography variant="body2" fontWeight="700" sx={{ lineHeight: 1.1, fontSize: '0.85rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                            {stat.title}
                                        </Typography>
                                    </Box>
                                    <Avatar sx={{ width: 28, height: 28, bgcolor: stat.bgcolor, color: stat.color }}>
                                        {stat.icon}
                                    </Avatar>
                                </Box>
                                <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
                                    <Typography variant="h5" fontWeight="800" color="text.primary">
                                        {stat.value}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', fontWeight: 'bold', fontSize: '0.65rem' }}>
                                        <TrendingUp sx={{ fontSize: 12, mr: 0.2 }} /> {stat.trend}
                                    </Typography>
                                </Box>
                            </Paper>
                        ))}
                    </Box>
                </Box>

                {/* 2. MAIN CONTENT (Flex Grow) */}
                <Box sx={{ flex: 1, minHeight: 0, width: '100%', display: 'flex', gap: 2 }}>

                    {/* Priority Inbox - 66% width */}
                    <Box sx={{ flex: 2, height: '100%', minWidth: 0 }}>
                        <Paper sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                            <Box sx={{ p: 2, borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Box>
                                    <Typography variant="subtitle1" fontWeight="700">Priority Alert Inbox</Typography>
                                </Box>
                                <Button size="small" sx={{ fontWeight: 600 }} endIcon={<ArrowForward fontSize="small" />} onClick={() => navigate('/b2b/surveillance/alerts')}>
                                    View All
                                </Button>
                            </Box>
                            <TableContainer sx={{ flex: 1 }}>
                                <Table stickyHeader size="small">
                                    <TableHead>
                                        <TableRow>
                                            <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }}>Risk Event</TableCell>
                                            <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }}>Entity</TableCell>
                                            <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }}>Severity</TableCell>
                                            <TableCell align="right" sx={{ fontWeight: 600, color: 'text.secondary' }}>Action</TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {priorityAlerts.map((row) => (
                                            <TableRow key={row.id} hover sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                                                <TableCell>
                                                    <Box>
                                                        <Typography variant="body2" fontWeight="600">{(row.risk_type || 'Unknown').replace('_', ' ').toUpperCase()}</Typography>
                                                        <Typography variant="caption" color="text.secondary">
                                                            {row.region || "Global"} • {new Date(row.communication?.timestamp || row.detected_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                        </Typography>
                                                    </Box>
                                                </TableCell>
                                                <TableCell>
                                                    <Typography variant="body2">{row.communication?.sender || "System"}</Typography>
                                                </TableCell>
                                                <TableCell>
                                                    <Chip
                                                        label={row.severity?.toUpperCase() || "MID"}
                                                        size="small"
                                                        sx={{
                                                            height: 24,
                                                            fontWeight: 800,
                                                            bgcolor: ['high', 'critical'].includes(row.severity) ? '#fee2e2' : '#ffedd5',
                                                            color: ['high', 'critical'].includes(row.severity) ? '#ef4444' : '#f97316'
                                                        }}
                                                    />
                                                </TableCell>
                                                <TableCell align="right">
                                                    <Button
                                                        size="small"
                                                        variant="text"
                                                        sx={{ minWidth: 0, px: 2, fontWeight: 600 }}
                                                        onClick={() => navigate(`/b2b/surveillance/alerts/${row.id}`)}
                                                    >
                                                        View Details
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                        {priorityAlerts.length === 0 && (
                                            <TableRow>
                                                <TableCell colSpan={4} align="center" sx={{ py: 4 }}>
                                                    <Typography color="text.secondary">No active alerts requiring attention.</Typography>
                                                </TableCell>
                                            </TableRow>
                                        )}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                        </Paper>
                    </Box>

                    {/* Active Cases - 33% width */}
                    <Box sx={{ flex: 1, height: '100%', minWidth: 0 }}>
                        <Paper sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                            <Box sx={{ p: 2, borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Typography variant="subtitle1" fontWeight="700">Active Cases</Typography>
                                <IconButton size="small"><MoreVert fontSize="small" /></IconButton>
                            </Box>
                            <Box sx={{ flex: 1, overflowY: 'auto' }}>
                                {myCases.map((item, index) => (
                                    <Box key={index} sx={{
                                        p: 2,
                                        borderBottom: '1px solid #f9fafb',
                                        cursor: 'pointer',
                                        transition: 'bgcolor 0.2s',
                                        '&:hover': { bgcolor: '#f9fafb' }
                                    }} onClick={() => navigate(`/b2b/surveillance/cases/${item.id}`)}>
                                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                            <Chip
                                                label={item.status || "NEW"}
                                                size="small"
                                                sx={{
                                                    height: 20,
                                                    fontSize: '0.65rem',
                                                    fontWeight: 700,
                                                    textTransform: 'uppercase',
                                                    bgcolor: 'rgba(79, 70, 229, 0.1)',
                                                    color: 'primary.main'
                                                }}
                                            />
                                            <Typography variant="caption" color={item.priority === 'high' ? "error.main" : "text.secondary"} fontWeight="700">
                                                {item.priority?.toUpperCase()}
                                            </Typography>
                                        </Box>
                                        <Typography variant="body2" fontWeight="600" sx={{ mb: 0.5 }}>{item.title}</Typography>
                                        <Typography variant="caption" color="text.secondary" fontFamily="monospace">ID: {item.display_id || item.id.substring(0, 8)}</Typography>
                                    </Box>
                                ))}
                                {myCases.length === 0 && (
                                    <Box sx={{ p: 4, textAlign: 'center' }}>
                                        <Typography color="text.secondary">No open cases assigned.</Typography>
                                    </Box>
                                )}
                            </Box>
                            <Box sx={{ p: 2, borderTop: '1px solid #f0f0f0' }}>
                                <Button fullWidth variant="outlined" size="small" onClick={() => navigate('/b2b/surveillance/cases')}>
                                    Go to Case Manager
                                </Button>
                            </Box>
                        </Paper>
                    </Box>
                </Box>
            </Box>
        </AdminLayout>
    );
};

export default SurveillanceDashboardPage;

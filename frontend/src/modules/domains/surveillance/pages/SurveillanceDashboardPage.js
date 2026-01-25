import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, Grid, Chip, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Button, IconButton, Paper, Avatar, Tooltip } from '@mui/material';
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

const SurveillanceDashboardPage = () => {
    const navigate = useNavigate();

    // Mock Data
    const stats = [
        {
            title: 'Pending Alerts',
            subtitle: 'Critical',
            value: 5,
            trend: '+2 today',
            icon: <NotificationsActive fontSize="small" />,
            color: 'error.main',
            bgcolor: 'error.light',
            path: '/b2b/surveillance/alerts'
        },
        {
            title: 'Investigations',
            subtitle: 'Active',
            value: 12,
            trend: '3 closing',
            icon: <Gavel fontSize="small" />,
            color: 'warning.main',
            bgcolor: 'warning.light',
            path: '/b2b/surveillance/cases'
        },
        {
            title: 'Ingestion Lag',
            subtitle: 'System',
            value: '40ms',
            trend: 'Healthy',
            icon: <Storage fontSize="small" />,
            color: 'success.main',
            bgcolor: 'success.light',
            path: '/b2b/surveillance/ingestion'
        },
    ];

    const regions = [
        { code: 'SIN', label: 'Singapore', risk: 'Low', color: 'success' },
        { code: 'EUR', label: 'Europe', risk: 'Mod', color: 'warning' },
        { code: 'USA', label: 'N. America', risk: 'Std', color: 'info' },
    ];

    const priorityAlerts = [
        { id: 1, type: 'Insider Trading', channel: 'Voice', entity: 'Trader A. Smith', score: 98, time: '10m' },
        { id: 2, type: 'Off-Channel Comm', channel: 'WhatsApp', entity: 'Desk: Equities', score: 85, time: '45m' },
        { id: 3, type: 'Collusion', channel: 'Chat', entity: 'T. Stark -> Rogers', score: 72, time: '2h' },
        { id: 4, type: 'Keyword: "Dump it"', channel: 'Email', entity: 'HedgeFund X', score: 65, time: '4h' },
        { id: 5, type: 'Unusual Pattern', channel: 'Market Data', entity: 'Algo Bot 7', score: 60, time: '5h' },
        { id: 6, type: 'Spoofing', channel: 'Order Log', entity: 'Trader B. Wayne', score: 58, time: '6h' },
    ];

    const myCases = [
        { id: 'CASE-89', title: 'Suspicious pre-earnings activity', status: 'Review', due: 'Today' },
        { id: 'CASE-92', title: 'Spoofing pattern Desk B', status: 'Evidence', due: 'Tomorrow' },
        { id: 'CASE-110', title: 'Large volume off-hours', status: 'New', due: '3 Days' },
    ];

    return (
        <AdminLayout title="Command Center" subtitle="Strategic Intelligence & Multi-Channel Compliance Monitoring">
            <Box sx={{ p: 2, height: 'calc(100vh - 84px)', display: 'flex', flexDirection: 'column', overflow: 'hidden', bgcolor: '#f3f4f6' }}>

                {/* 1. TOP SUMMARY ROW (Aligned Baseline) */}
                <Grid container spacing={2} sx={{ mb: 2, flexShrink: 0, width: '100%' }}>

                    {/* Regional Risk Posture */}
                    <Grid item xs={12} md={3} lg={3} xl={3}>
                        <Paper sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <Shield color="primary" fontSize="small" />
                                    <Typography variant="subtitle2" fontWeight="700" color="text.secondary" sx={{ fontSize: '0.75rem' }}>GLOBAL RISK</Typography>
                                </Box>
                                <Chip label="Stable" color="success" size="small" sx={{ height: 20, fontSize: '0.65rem', fontWeight: 700 }} />
                            </Box>

                            <Box sx={{ display: 'flex', gap: 1 }}>
                                {regions.map((region) => (
                                    <Tooltip title={`${region.label}: ${region.risk}`} key={region.code}>
                                        <Box sx={{
                                            flex: 1,
                                            p: 1,
                                            borderRadius: 2,
                                            border: 1,
                                            borderColor: `${region.color}.main`,
                                            bgcolor: (theme) => `rgba(${region.color === 'success' ? '46, 125, 50' : region.color === 'warning' ? '237, 108, 2' : '2, 136, 209'}, 0.08)`,
                                            textAlign: 'center',
                                            position: 'relative',
                                            overflow: 'hidden'
                                        }}>
                                            <Box sx={{ position: 'absolute', top: 0, left: 0, width: 4, height: '100%', bgcolor: `${region.color}.main` }} />
                                            <Box sx={{ position: 'relative', zIndex: 1, pl: 0.5 }}>
                                                <Typography variant="caption" fontWeight="700" color="text.secondary" display="block" sx={{ opacity: 0.8, fontSize: '0.7rem' }}>{region.code}</Typography>
                                                <Typography variant="body2" fontWeight="800" sx={{ color: `${region.color}.main`, lineHeight: 1.2 }}>{region.risk}</Typography>
                                            </Box>
                                        </Box>
                                    </Tooltip>
                                ))}
                            </Box>
                        </Paper>
                    </Grid>

                    {/* KPI Cards */}
                    {stats.map((stat, index) => (
                        <Grid item xs={12} md={3} lg={3} xl={3} key={index} sx={{ flexGrow: 1 }}>
                            <Paper
                                sx={{
                                    p: 2,
                                    height: '100%',
                                    cursor: 'pointer',
                                    position: 'relative',
                                    transition: 'transform 0.2s',
                                    '&:hover': { transform: 'translateY(-2px)', boxShadow: 2 }
                                }}
                                onClick={() => navigate(stat.path)}
                            >
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                                    <Box>
                                        <Typography variant="caption" color="text.secondary" fontWeight="700" sx={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>
                                            {stat.subtitle}
                                        </Typography>
                                        <Typography variant="body2" fontWeight="700" sx={{ lineHeight: 1.2 }}>
                                            {stat.title}
                                        </Typography>
                                    </Box>
                                    <Avatar sx={{ width: 32, height: 32, bgcolor: stat.bgcolor, color: stat.color }}>
                                        {stat.icon}
                                    </Avatar>
                                </Box>
                                <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
                                    <Typography variant="h4" fontWeight="800" color="text.primary">
                                        {stat.value}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', fontWeight: 'bold' }}>
                                        <TrendingUp sx={{ fontSize: 14, mr: 0.5 }} /> {stat.trend}
                                    </Typography>
                                </Box>
                            </Paper>
                        </Grid>
                    ))}
                </Grid>

                {/* 2. MAIN CONTENT (Flex Grow) */}
                {/* 2. MAIN CONTENT (Flex Grow) - Using pure Flexbox for reliability */}
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
                                            <TableCell sx={{ fontWeight: 600, color: 'text.secondary' }}>Score</TableCell>
                                            <TableCell align="right" sx={{ fontWeight: 600, color: 'text.secondary' }}>Action</TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {priorityAlerts.map((row) => (
                                            <TableRow key={row.id} hover sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                                                <TableCell>
                                                    <Box>
                                                        <Typography variant="body2" fontWeight="600">{row.type}</Typography>
                                                        <Typography variant="caption" color="text.secondary">{row.channel} • {row.time} ago</Typography>
                                                    </Box>
                                                </TableCell>
                                                <TableCell>
                                                    <Typography variant="body2">{row.entity}</Typography>
                                                </TableCell>
                                                <TableCell>
                                                    <Chip
                                                        label={row.score}
                                                        size="small"
                                                        sx={{
                                                            height: 24,
                                                            fontWeight: 800,
                                                            bgcolor: row.score > 90 ? '#fee2e2' : '#ffedd5',
                                                            color: row.score > 90 ? '#ef4444' : '#f97316'
                                                        }}
                                                    />
                                                </TableCell>
                                                <TableCell align="right">
                                                    <Button size="small" variant="text" sx={{ minWidth: 0, px: 2, fontWeight: 600 }}>Investigate</Button>
                                                </TableCell>
                                            </TableRow>
                                        ))}
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
                                    }} onClick={() => navigate('/b2b/surveillance/cases')}>
                                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                            <Chip
                                                label={item.status}
                                                size="small"
                                                sx={{
                                                    height: 20,
                                                    fontSize: '0.65rem',
                                                    fontWeight: 700,
                                                    textTransform: 'uppercase',
                                                    bgcolor: 'primary.light',
                                                    color: 'primary.main',
                                                    bgcolor: 'rgba(79, 70, 229, 0.1)'
                                                }}
                                            />
                                            <Typography variant="caption" color="error.main" fontWeight="700">Due: {item.due}</Typography>
                                        </Box>
                                        <Typography variant="body2" fontWeight="600" sx={{ mb: 0.5 }}>{item.title}</Typography>
                                        <Typography variant="caption" color="text.secondary" fontFamily="monospace">ID: {item.id}</Typography>
                                    </Box>
                                ))}
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

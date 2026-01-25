import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AdminLayout from '../../../b2b/web/layouts/AdminLayout';
import b2bDomainClient from '../../../../core/api/b2bDomainClient';
import {
    Box, Typography, Paper, Grid, Card, CardContent,
    Stack, Chip, Button, CircularProgress, Alert,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    IconButton, TextField, MenuItem
} from '@mui/material';
import {
    FolderOpen, RateReview, ReportProblem, Visibility,
    FilterList, Search, Assignment
} from '@mui/icons-material';

const STATUS_COLORS = {
    'open': '#3f51b5',
    'in_review': '#ff9800',
    'escalated': '#f44336',
    'closed': '#4caf50',
};

const PRIORITY_COLORS = {
    'low': '#9e9e9e',
    'medium': '#2196f3',
    'high': '#ff9800',
    'critical': '#f44336',
};

const CaseListPage = () => {
    const navigate = useNavigate();
    const [cases, setCases] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [statusFilter, setStatusFilter] = useState('');

    useEffect(() => {
        fetchData();
    }, [statusFilter]);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [casesData, statsData] = await Promise.all([
                b2bDomainClient.getCases({ status: statusFilter }),
                b2bDomainClient.getCaseStats()
            ]);
            setCases(casesData);
            setStats(statsData);
            setError(null);
        } catch (err) {
            console.error('Failed to fetch cases:', err);
            setError('Failed to load cases. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const getStatusChip = (status) => (
        <Chip
            label={status.replace('_', ' ').toUpperCase()}
            size="small"
            sx={{
                bgcolor: `${STATUS_COLORS[status] || '#9e9e9e'}15`,
                color: STATUS_COLORS[status] || '#9e9e9e',
                fontWeight: 700,
                fontSize: '0.65rem'
            }}
        />
    );

    const getPriorityChip = (priority) => (
        <Chip
            label={priority.toUpperCase()}
            size="small"
            variant="outlined"
            sx={{
                color: PRIORITY_COLORS[priority] || '#9e9e9e',
                borderColor: PRIORITY_COLORS[priority] || '#9e9e9e',
                fontWeight: 700,
                fontSize: '0.6rem',
                height: 20
            }}
        />
    );

    return (
        <AdminLayout>
            <Box sx={{ p: 4, bgcolor: '#f8f9fa', minHeight: '100vh' }}>
                <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                    <Box>
                        <Typography variant="h4" sx={{ fontWeight: 800, color: '#1a1a1a', mb: 1 }}>
                            Case Management
                        </Typography>
                        <Typography variant="body1" color="textSecondary">
                            Manage compliance investigations and lifecycle.
                        </Typography>
                    </Box>
                    <Button
                        variant="contained"
                        startIcon={<Assignment />}
                        onClick={() => navigate('/b2b/surveillance/alerts')}
                        sx={{ px: 3, py: 1, borderRadius: 2, textTransform: 'none', fontWeight: 600 }}
                    >
                        Escalate New Case
                    </Button>
                </Box>

                {/* Stats Cards */}
                {stats && (
                    <Grid container spacing={3} sx={{ mb: 4 }}>
                        {[
                            { label: 'Active Cases', value: stats.open_count, color: '#3f51b5', icon: <FolderOpen /> },
                            { label: 'Pending Review', value: stats.in_review_count, color: '#ff9800', icon: <RateReview /> },
                            { label: 'Escalated', value: stats.escalated_count, color: '#f44336', icon: <ReportProblem /> },
                            { label: 'Total Investigations', value: stats.total_count, color: '#757575', icon: <Search /> }
                        ].map((s, idx) => (
                            <Grid item xs={12} sm={6} md={3} key={idx}>
                                <Paper sx={{ p: 3, borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.04)' }}>
                                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                                        <Box>
                                            <Typography variant="caption" color="textSecondary" sx={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                                                {s.label}
                                            </Typography>
                                            <Typography variant="h4" sx={{ fontWeight: 800, mt: 0.5, color: s.color }}>
                                                {s.value}
                                            </Typography>
                                        </Box>
                                        <Box sx={{ p: 1.5, bgcolor: `${s.color}10`, color: s.color, borderRadius: 2 }}>
                                            {s.icon}
                                        </Box>
                                    </Stack>
                                </Paper>
                            </Grid>
                        ))}
                    </Grid>
                )}

                {/* Filters & Table */}
                <Paper sx={{ borderRadius: 3, overflow: 'hidden', boxShadow: '0 2px 12px rgba(0,0,0,0.04)' }}>
                    <Box sx={{ p: 2.5, borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', gap: 2 }}>
                        <FilterList color="action" />
                        <TextField
                            select
                            size="small"
                            label="Filter by Status"
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            sx={{ width: 200 }}
                        >
                            <MenuItem value="">All Statuses</MenuItem>
                            <MenuItem value="open">Open</MenuItem>
                            <MenuItem value="in_review">In Review</MenuItem>
                            <MenuItem value="escalated">Escalated</MenuItem>
                            <MenuItem value="closed">Closed</MenuItem>
                        </TextField>
                    </Box>

                    {loading ? (
                        <Box sx={{ p: 8, textAlign: 'center' }}><CircularProgress /></Box>
                    ) : error ? (
                        <Alert severity="error" sx={{ m: 2 }}>{error}</Alert>
                    ) : (
                        <TableContainer>
                            <Table sx={{ minWidth: 800 }}>
                                <TableHead sx={{ bgcolor: '#fafafa' }}>
                                    <TableRow>
                                        <TableCell sx={{ fontWeight: 700, color: '#666' }}>Case ID</TableCell>
                                        <TableCell sx={{ fontWeight: 700, color: '#666' }}>Subject</TableCell>
                                        <TableCell sx={{ fontWeight: 700, color: '#666' }}>Status</TableCell>
                                        <TableCell sx={{ fontWeight: 700, color: '#666' }}>Priority</TableCell>
                                        <TableCell sx={{ fontWeight: 700, color: '#666' }}>SLA Target</TableCell>
                                        <TableCell align="right" sx={{ fontWeight: 700, color: '#666' }}>Actions</TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {cases.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={6} align="center" sx={{ py: 8, color: 'text.secondary' }}>
                                                No cases found.
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        cases.map((c) => (
                                            <TableRow key={c.id} hover onClick={() => navigate(`/b2b/surveillance/cases/${c.id}`)} sx={{ cursor: 'pointer' }}>
                                                <TableCell sx={{ fontFamily: 'monospace', color: '#666', fontSize: '0.85rem' }}>
                                                    CASE-{c.id.substring(0, 8).toUpperCase()}
                                                </TableCell>
                                                <TableCell>
                                                    <Typography variant="body2" sx={{ fontWeight: 600, color: '#333' }}>
                                                        {typeof c.title === 'object' ? (c.title.type || JSON.stringify(c.title)) : c.title}
                                                    </Typography>
                                                    <Typography variant="caption" color="textSecondary">
                                                        Opened {new Date(c.created_at).toLocaleDateString()}
                                                    </Typography>
                                                </TableCell>
                                                <TableCell>{getStatusChip(c.status)}</TableCell>
                                                <TableCell>{getPriorityChip(c.priority)}</TableCell>
                                                <TableCell>
                                                    {c.target_closure_date ? (
                                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: new Date(c.target_closure_date) < new Date() ? 'error.main' : 'text.primary' }}>
                                                            <AccessTime sx={{ fontSize: 16 }} />
                                                            <Typography variant="body2">{new Date(c.target_closure_date).toLocaleDateString()}</Typography>
                                                        </Box>
                                                    ) : '-'}
                                                </TableCell>
                                                <TableCell align="right">
                                                    <IconButton color="primary" size="small">
                                                        <Visibility fontSize="small" />
                                                    </IconButton>
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    )}
                                </TableBody>
                            </Table>
                        </TableContainer>
                    )}
                </Paper>
            </Box>
        </AdminLayout>
    );
};

const AccessTime = ({ sx }) => (
    <Box component="span" sx={{ ...sx, display: 'inline-flex' }}>
        <svg fill="currentColor" width="1em" height="1em" viewBox="0 0 24 24"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z" /></svg>
    </Box>
);

export default CaseListPage;

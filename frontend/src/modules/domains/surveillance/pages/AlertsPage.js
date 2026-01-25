import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import AdminLayout from "../../../b2b/web/layouts/AdminLayout";
import b2bDomainClient from "../../../../core/api/b2bDomainClient";
import {
    Box, Typography, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    Chip, Button, IconButton, TextField, MenuItem, Stack, CircularProgress, Tooltip
} from "@mui/material";
import {
    FilterList, Visibility, Warning, CheckCircle, AssignmentInd,
    Close as CloseIcon, Speed, DoneAll, HistoryEdu
} from "@mui/icons-material";
import b2bClient from "../../../../core/api/b2bClient";

const AlertsPage = () => {
    const navigate = useNavigate();
    const [alerts, setAlerts] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [users, setUsers] = useState([]);

    // Filters
    const [statusFilter, setStatusFilter] = useState("");
    const [severityFilter, setSeverityFilter] = useState("");
    const [riskTypeFilter, setRiskTypeFilter] = useState("");
    const [regionFilter, setRegionFilter] = useState("");

    const fetchAlerts = async () => {
        setLoading(true);
        try {
            const filters = {};
            if (statusFilter) filters.status = statusFilter;
            if (severityFilter) filters.severity = severityFilter;
            if (riskTypeFilter) filters.risk_type = riskTypeFilter;
            if (regionFilter) filters.region = regionFilter;

            const [alertsData, statsData, usersData] = await Promise.all([
                b2bDomainClient.getAlerts(filters),
                b2bDomainClient.getAlertStats(),
                b2bClient.listUsers()
            ]);

            setAlerts(alertsData);
            setStats(statsData);
            setUsers(usersData);
        } catch (error) {
            console.error("Failed to fetch alerts:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAlerts();
    }, [statusFilter, severityFilter, riskTypeFilter, regionFilter]);

    const handleStatusUpdate = async (alertId, newStatus, autoNavigate = false) => {
        try {
            if (newStatus === 'escalated') {
                await b2bDomainClient.escalateAlert(alertId);
            } else if (newStatus === 'closed') {
                await b2bDomainClient.closeAlert(alertId);
            } else {
                await b2bDomainClient.updateAlert(alertId, { status: newStatus });
            }
            fetchAlerts(); // Refresh list

            if (autoNavigate) {
                navigate(`/b2b/surveillance/alerts/${alertId}`);
            }
        } catch (error) {
            console.error("Update failed:", error);
        }
    };

    const pickNextAlert = () => {
        const next = alerts.find(a => a.status === 'open' && !a.assigned_to);
        if (next) {
            handleStatusUpdate(next.id, 'investigating', true);
        }
    };

    const handleAssign = async (alertId, userId) => {
        try {
            await b2bDomainClient.updateAlert(alertId, { assigned_to: userId });
            fetchAlerts();
        } catch (error) {
            console.error("Assignment failed:", error);
        }
    };

    const getSeverityColor = (severity) => {
        switch (severity) {
            case "critical": return "error";
            case "high": return "warning";
            case "medium": return "info";
            default: return "default";
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case "open": return "error";
            case "investigating": return "warning";
            case "closed": return "success";
            case "escalated": return "secondary";
            default: return "default";
        }
    };

    const highlightText = (text, keywords) => {
        if (!keywords || keywords.length === 0 || !text) return text;

        // Extract string keywords if they are objects
        const kwStrings = keywords.map(kw =>
            typeof kw === 'object' ? (kw.keyword || kw.text || JSON.stringify(kw)) : kw
        ).filter(kw => typeof kw === 'string' && kw.length > 0);

        if (kwStrings.length === 0) return text;

        const escapedKeywords = kwStrings.map(kw => kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
        const regex = new RegExp(`(${escapedKeywords.join('|')})`, 'gi');
        const parts = text.split(regex);

        return parts.map((part, i) =>
            kwStrings.some(kw => part.toLowerCase() === kw.toLowerCase()) ? (
                <Box
                    key={i}
                    component="span"
                    sx={{
                        bgcolor: '#fff176', // Brighter yellow
                        px: 0.5,
                        mx: 0.1,
                        borderRadius: 0.5,
                        fontWeight: 800,
                        color: '#000',
                        borderBottom: '2px solid #fbc02d'
                    }}
                >
                    {part}
                </Box>
            ) : part
        );
    };

    return (
        <AdminLayout>
            <Box sx={{ p: 4, bgcolor: '#f8f9fa', minHeight: '100vh' }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" mb={4}>
                    <Box>
                        <Typography variant="h4" sx={{ fontWeight: 800, color: '#1a1a1a', mb: 0.5 }}>Surveillance Alerts</Typography>
                        <Typography variant="body2" color="textSecondary">Manage regulatory risk detections and investigations</Typography>
                    </Box>
                    <Stack direction="row" spacing={2}>
                        <Button
                            variant="contained"
                            color="warning"
                            startIcon={<Speed />}
                            onClick={pickNextAlert}
                            disabled={loading || !alerts.some(a => a.status === 'open')}
                            sx={{ fontWeight: 700, px: 3 }}
                        >
                            Pick Next Alert
                        </Button>
                        <Button
                            variant="outlined"
                            startIcon={<HistoryEdu />}
                            onClick={fetchAlerts}
                            disabled={loading}
                        >
                            Refresh Queue
                        </Button>
                    </Stack>
                </Stack>

                {/* Stats Section */}
                {stats && (
                    <Stack direction="row" spacing={3} sx={{ mb: 4 }}>
                        {[
                            { label: "Total Alerts", value: stats.total_alerts, color: '#3f51b5' },
                            { label: "High Risk", value: stats.high_risk_count, color: '#f44336' },
                            { label: "Open", value: stats.open_count, color: '#ff9800' },
                            { label: "Unassigned", value: stats.unassigned_count, color: '#757575' }
                        ].map((card, idx) => (
                            <Paper key={idx} sx={{ p: 3, flex: 1, boxShadow: '0 2px 10px rgba(0,0,0,0.05)', borderRadius: 2 }}>
                                <Typography variant="subtitle2" color="textSecondary" sx={{ mb: 1 }}>{card.label}</Typography>
                                <Typography variant="h3" sx={{ fontWeight: 800, color: card.color }}>{card.value}</Typography>
                            </Paper>
                        ))}
                    </Stack>
                )}

                {/* Filter Bar */}
                <Paper sx={{ p: 2, mb: 3, borderRadius: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
                    <FilterList color="action" />
                    <TextField
                        select
                        label="Risk Type"
                        value={riskTypeFilter}
                        onChange={(e) => setRiskTypeFilter(e.target.value)}
                        size="small"
                        sx={{ width: 180 }}
                    >
                        <MenuItem value="">All Types</MenuItem>
                        <MenuItem value="Financial Fraud">Financial Fraud</MenuItem>
                        <MenuItem value="Market-to-Market Manipulation">Market Manipulation</MenuItem>
                        <MenuItem value="Evasion & Secrecy">Evasion & Secrecy</MenuItem>
                    </TextField>
                    <TextField
                        select
                        label="Region"
                        value={regionFilter}
                        onChange={(e) => setRegionFilter(e.target.value)}
                        size="small"
                        sx={{ width: 150 }}
                    >
                        <MenuItem value="">All Regions</MenuItem>
                        <MenuItem value="USA">USA</MenuItem>
                        <MenuItem value="UK">UK</MenuItem>
                        <MenuItem value="Singapore">Singapore</MenuItem>
                    </TextField>
                    <TextField
                        select
                        label="Status"
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                        size="small"
                        sx={{ width: 150 }}
                    >
                        <MenuItem value="">All Statuses</MenuItem>
                        <MenuItem value="open">Open</MenuItem>
                        <MenuItem value="investigating">Investigating</MenuItem>
                        <MenuItem value="escalated">Escalated</MenuItem>
                        <MenuItem value="closed">Closed</MenuItem>
                    </TextField>
                    <TextField
                        select
                        label="Severity"
                        value={severityFilter}
                        onChange={(e) => setSeverityFilter(e.target.value)}
                        size="small"
                        sx={{ width: 150 }}
                    >
                        <MenuItem value="">All Severities</MenuItem>
                        <MenuItem value="critical">Critical</MenuItem>
                        <MenuItem value="high">High</MenuItem>
                        <MenuItem value="medium">Medium</MenuItem>
                        <MenuItem value="low">Low</MenuItem>
                    </TextField>
                    <Box sx={{ flexGrow: 1 }} />
                    <Button variant="contained" onClick={fetchAlerts} sx={{ px: 4 }}>Refresh Queue</Button>
                </Paper>

                {/* Table */}
                <TableContainer component={Paper}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell sx={{ fontWeight: 700 }}>Alert Id</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Risk</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Type</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Severity</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Sender</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Region</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Detected At</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Description</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Assignee</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 700 }}>Actions</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={10} align="center"><CircularProgress /></TableCell>
                                </TableRow>
                            ) : alerts.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={10} align="center">No alerts found</TableCell>
                                </TableRow>
                            ) : (
                                alerts.map((alert) => (
                                    <TableRow key={alert.id} hover>
                                        <TableCell sx={{ fontWeight: 600, color: '#1a73e8' }}>
                                            {alert.display_id || alert.id.substring(0, 8)}
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                label={alert.metadata?.ai_analysis?.risk_level || "pending"}
                                                size="small"
                                                variant="outlined"
                                                sx={{
                                                    fontWeight: 700,
                                                    fontSize: '0.65rem',
                                                    color: alert.metadata?.ai_analysis?.risk_level === 'high' ? '#d32f2f' : '#757575',
                                                    borderColor: alert.metadata?.ai_analysis?.risk_level === 'high' ? '#ffcdd2' : '#e0e0e0'
                                                }}
                                            />
                                        </TableCell>
                                        <TableCell sx={{ fontWeight: 500, fontSize: '0.85rem' }}>
                                            {(alert.risk_type || 'Unknown').replace('_', ' ').toUpperCase()}
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                label={alert.severity}
                                                size="small"
                                                color={getSeverityColor(alert.severity)}
                                                sx={{ fontSize: '0.7rem' }}
                                            />
                                        </TableCell>
                                        <TableCell sx={{ fontSize: '0.85rem' }}>
                                            {alert.communication?.sender || "System"}
                                        </TableCell>
                                        <TableCell sx={{ fontSize: '0.85rem' }}>{alert.region || "Default"}</TableCell>
                                        <TableCell sx={{ fontSize: '0.85rem', color: 'text.secondary' }}>
                                            {new Date(alert.detected_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                                        </TableCell>
                                        <TableCell sx={{ maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontSize: '0.85rem' }}>
                                            {alert.description}
                                        </TableCell>
                                        <TableCell>
                                            <TextField
                                                select
                                                size="small"
                                                variant="standard"
                                                value={alert.assigned_to || ""}
                                                onChange={(e) => handleAssign(alert.id, e.target.value)}
                                                sx={{ minWidth: 100, fontSize: '0.8rem' }}
                                                InputProps={{ disableUnderline: true }}
                                            >
                                                <MenuItem value=""><em>Unassigned</em></MenuItem>
                                                {users.map(u => (
                                                    <MenuItem key={u.id} value={u.id} sx={{ fontSize: '0.8rem' }}>{u.name || u.email}</MenuItem>
                                                ))}
                                            </TextField>
                                        </TableCell>
                                        <TableCell align="right">
                                            <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                                                <Tooltip title={alert.status === 'open' ? "Review & Verify" : "View Details"}>
                                                    <IconButton
                                                        size="small"
                                                        onClick={() => alert.status === 'open' ? handleStatusUpdate(alert.id, 'investigating', true) : navigate(`/b2b/surveillance/alerts/${alert.id}`)}
                                                        color="primary"
                                                    >
                                                        <Visibility fontSize="small" />
                                                    </IconButton>
                                                </Tooltip>
                                                <Tooltip title="Escalate to Case">
                                                    <span>
                                                        <IconButton
                                                            size="small"
                                                            onClick={() => handleStatusUpdate(alert.id, 'escalated')}
                                                            disabled={!['open', 'investigating'].includes(alert.status)}
                                                        >
                                                            <HistoryEdu fontSize="small" color={['open', 'investigating'].includes(alert.status) ? "secondary" : "disabled"} />
                                                        </IconButton>
                                                    </span>
                                                </Tooltip>
                                                <Tooltip title="Close Alert">
                                                    <span>
                                                        <IconButton
                                                            size="small"
                                                            onClick={() => handleStatusUpdate(alert.id, 'closed')}
                                                            disabled={alert.status === 'closed'}
                                                        >
                                                            <DoneAll fontSize="small" color={alert.status !== 'closed' ? "success" : "disabled"} />
                                                        </IconButton>
                                                    </span>
                                                </Tooltip>
                                            </Stack>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>

                {/* Details Drawer removed as it is now a dedicated page */}
            </Box>
        </AdminLayout>
    );
};

export default AlertsPage;

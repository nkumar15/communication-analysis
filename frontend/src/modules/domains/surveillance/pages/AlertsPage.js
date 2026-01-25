
import React, { useState, useEffect } from "react";
import AdminLayout from "../../../b2b/web/layouts/AdminLayout";
import b2bDomainClient from "../../../../core/api/b2bDomainClient";
import {
    Box, Typography, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    Chip, Button, IconButton, Drawer, TextField, MenuItem, Stack, CircularProgress, Tooltip
} from "@mui/material";
import {
    FilterList, Visibility, Warning, CheckCircle, AssignmentInd,
    Close as CloseIcon, Speed, DoneAll, HistoryEdu
} from "@mui/icons-material";
import b2bClient from "../../../../core/api/b2bClient";

const AlertsPage = () => {
    const [alerts, setAlerts] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [selectedAlert, setSelectedAlert] = useState(null);
    const [drawerOpen, setDrawerOpen] = useState(false);
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

    const handleOpenDrawer = async (alert) => {
        setDrawerOpen(true);
        try {
            // Fetch detailed alert which now includes conversation_thread
            const fullAlert = await b2bDomainClient.getAlert(alert.id);
            setSelectedAlert(fullAlert);
        } catch (err) {
            console.error("Failed to load alert details:", err);
            setSelectedAlert(alert); // Fallback to basic info
        }
    };

    const handleCloseDrawer = () => {
        setDrawerOpen(false);
        setSelectedAlert(null);
    };

    const handleStatusUpdate = async (alertId, newStatus) => {
        try {
            if (newStatus === 'escalated') {
                await b2bDomainClient.escalateAlert(alertId);
            } else if (newStatus === 'closed') {
                await b2bDomainClient.closeAlert(alertId);
            } else {
                await b2bDomainClient.updateAlert(alertId, { status: newStatus });
            }
            fetchAlerts(); // Refresh list
            if (selectedAlert?.id === alertId) handleCloseDrawer();
        } catch (error) {
            console.error("Update failed:", error);
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

        const escapedKeywords = keywords.map(kw => kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
        const regex = new RegExp(`(${escapedKeywords.join('|')})`, 'gi');
        const parts = text.split(regex);

        return parts.map((part, i) =>
            regex.test(part) ? (
                <Box
                    key={i}
                    component="span"
                    sx={{
                        bgcolor: '#ffeb3b',
                        px: 0.5,
                        borderRadius: 0.5,
                        fontWeight: 600,
                        color: '#000'
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
                <Typography variant="h4" sx={{ mb: 4, fontWeight: 700, color: '#1a1a1a' }}>
                    Surveillance Alerts
                </Typography>

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
                                <TableCell sx={{ fontWeight: 700 }}>Risk Type</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Severity</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Region</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Assignee</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Detected At</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Description</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 700 }}>Actions</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={8} align="center"><CircularProgress /></TableCell>
                                </TableRow>
                            ) : alerts.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={8} align="center">No alerts found</TableCell>
                                </TableRow>
                            ) : (
                                alerts.map((alert) => (
                                    <TableRow key={alert.id} hover>
                                        <TableCell sx={{ fontWeight: 500 }}>
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
                                        <TableCell>{alert.region || "Default"}</TableCell>
                                        <TableCell>
                                            <TextField
                                                select
                                                size="small"
                                                variant="standard"
                                                value={alert.assigned_to || ""}
                                                onChange={(e) => handleAssign(alert.id, e.target.value)}
                                                sx={{ minWidth: 120, fontSize: '0.875rem' }}
                                                InputProps={{ disableUnderline: true }}
                                            >
                                                <MenuItem value=""><em>Unassigned</em></MenuItem>
                                                {users.map(u => (
                                                    <MenuItem key={u.id} value={u.id}>{u.name || u.email}</MenuItem>
                                                ))}
                                            </TextField>
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                label={alert.status}
                                                size="small"
                                                variant="outlined"
                                                color={getStatusColor(alert.status)}
                                                sx={{ fontSize: '0.7rem' }}
                                            />
                                        </TableCell>
                                        <TableCell sx={{ fontSize: '0.85rem', color: 'text.secondary' }}>
                                            {new Date(alert.detected_at).toLocaleString()}
                                        </TableCell>
                                        <TableCell sx={{ maxWidth: 300, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                            {alert.description}
                                        </TableCell>
                                        <TableCell align="right">
                                            <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                                                {alert.status === 'open' && (
                                                    <Tooltip title="Start Investigation">
                                                        <IconButton size="small" onClick={() => handleStatusUpdate(alert.id, 'investigating')}>
                                                            <Speed fontSize="small" color="warning" />
                                                        </IconButton>
                                                    </Tooltip>
                                                )}
                                                {alert.status !== 'closed' && (
                                                    <Tooltip title="Close Alert">
                                                        <IconButton size="small" onClick={() => handleStatusUpdate(alert.id, 'closed')}>
                                                            <DoneAll fontSize="small" color="success" />
                                                        </IconButton>
                                                    </Tooltip>
                                                )}
                                                {['open', 'investigating'].includes(alert.status) && (
                                                    <Tooltip title="Escalate to Case">
                                                        <IconButton size="small" onClick={() => handleStatusUpdate(alert.id, 'escalated')}>
                                                            <HistoryEdu fontSize="small" color="secondary" />
                                                        </IconButton>
                                                    </Tooltip>
                                                )}
                                                <Tooltip title="View Details">
                                                    <IconButton size="small" onClick={() => handleOpenDrawer(alert)}>
                                                        <Visibility fontSize="small" color="primary" />
                                                    </IconButton>
                                                </Tooltip>
                                            </Stack>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>

                {/* Details Drawer */}
                <Drawer
                    anchor="right"
                    open={drawerOpen}
                    onClose={handleCloseDrawer}
                    PaperProps={{ sx: { width: 600, bgcolor: '#fdfdfd' } }}
                >
                    <Box sx={{ p: 4 }}>
                        {selectedAlert && (
                            <>
                                <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                    <Box>
                                        <Typography variant="overline" color="textSecondary" sx={{ letterSpacing: 1.2 }}>
                                            {(selectedAlert.risk_type || 'Unknown').replace('_', ' ')}
                                        </Typography>
                                        <Typography variant="h5" sx={{ fontWeight: 800 }}>
                                            {selectedAlert.subject || "Flagged Communication"}
                                        </Typography>
                                    </Box>
                                    <Chip
                                        label={selectedAlert.severity}
                                        color={getSeverityColor(selectedAlert.severity)}
                                        sx={{ fontWeight: 'bold' }}
                                    />
                                </Box>

                                {/* Action Bar */}
                                <Paper variant="outlined" sx={{ p: 2, mb: 4, bgcolor: '#f0f4f8', border: '1px solid #d1d9e6' }}>
                                    <Stack direction="row" spacing={2} alignItems="center">
                                        <TextField
                                            select
                                            size="small"
                                            label="Assign To"
                                            value={selectedAlert.assigned_to || ""}
                                            onChange={(e) => handleAssign(selectedAlert.id, e.target.value)}
                                            sx={{ minWidth: 200, bgcolor: 'white' }}
                                        >
                                            <MenuItem value=""><em>Unassigned</em></MenuItem>
                                            {users.map(u => (
                                                <MenuItem key={u.id} value={u.id}>{u.name || u.email}</MenuItem>
                                            ))}
                                        </TextField>

                                        <Box sx={{ flexGrow: 1 }} />

                                        <Button
                                            variant="contained"
                                            color="error"
                                            startIcon={<Warning />}
                                            onClick={() => handleStatusUpdate(selectedAlert.id, 'escalated')}
                                            disabled={selectedAlert.status === 'escalated' || selectedAlert.status === 'closed'}
                                        >
                                            Escalate
                                        </Button>
                                        <Button
                                            variant="contained"
                                            color="success"
                                            onClick={() => handleStatusUpdate(selectedAlert.id, 'closed')}
                                            disabled={selectedAlert.status === 'closed'}
                                        >
                                            Close
                                        </Button>
                                        <Button
                                            variant="outlined"
                                            onClick={() => handleStatusUpdate(selectedAlert.id, 'investigating')}
                                            disabled={selectedAlert.status === 'investigating' || selectedAlert.status === 'closed'}
                                        >
                                            Investigate
                                        </Button>
                                    </Stack>
                                </Paper>

                                <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                                    Conversation Thread
                                    <Typography variant="caption" sx={{ bgcolor: '#eee', px: 1, borderRadius: 1 }}>
                                        {selectedAlert.conversation_thread?.length || 0} messages
                                    </Typography>
                                </Typography>

                                <Box sx={{ borderLeft: '2px solid #e0e0e0', ml: 1, pl: 3 }}>
                                    {(selectedAlert.conversation_thread || []).map((msg, idx) => (
                                        <Box key={idx} sx={{ mb: 4, position: 'relative' }}>
                                            {/* Thread Dot */}
                                            <Box sx={{
                                                position: 'absolute',
                                                left: -33,
                                                top: 10,
                                                width: 14,
                                                height: 14,
                                                borderRadius: '50%',
                                                bgcolor: msg.is_trigger ? '#f44336' : '#bdbdbd',
                                                border: '3px solid white',
                                                zIndex: 1
                                            }} />

                                            {/* Risk Indicator Header */}
                                            {msg.is_trigger && (
                                                <Box sx={{
                                                    mb: 1,
                                                    p: 1,
                                                    bgcolor: '#fff5f5',
                                                    border: '1px solid #ffcdd2',
                                                    borderRadius: 1,
                                                    display: 'flex',
                                                    gap: 1,
                                                    alignItems: 'center'
                                                }}>
                                                    <Warning sx={{ fontSize: 16, color: '#f44336' }} />
                                                    <Typography variant="caption" sx={{ fontWeight: 800, color: '#c62828', textTransform: 'uppercase' }}>
                                                        Risk Indicator: {msg.risk_indicators.join(", ")}
                                                    </Typography>
                                                    {msg.matched_keywords?.length > 0 && (
                                                        <Box sx={{ ml: 'auto', display: 'flex', gap: 0.5 }}>
                                                            {msg.matched_keywords.map((kw, kidx) => (
                                                                <Chip
                                                                    key={kidx}
                                                                    label={typeof kw === 'object' ? (kw.type || JSON.stringify(kw)) : kw}
                                                                    size="small"
                                                                    sx={{
                                                                        height: 18,
                                                                        fontSize: '0.65rem',
                                                                        bgcolor: '#ffebee',
                                                                        color: '#d32f2f',
                                                                        border: '1px solid #ffcdd2'
                                                                    }}
                                                                />
                                                            ))}
                                                        </Box>
                                                    )}
                                                </Box>
                                            )}

                                            <Paper
                                                elevation={0}
                                                sx={{
                                                    p: 2,
                                                    bgcolor: msg.is_trigger ? '#fff' : '#fcfcfc',
                                                    border: msg.is_trigger ? '2px solid #ffcdd2' : '1px solid #eee',
                                                    borderRadius: 2
                                                }}
                                            >
                                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                                    <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{msg.sender}</Typography>
                                                    <Typography variant="caption" color="textSecondary">
                                                        {new Date(msg.timestamp).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                                                    </Typography>
                                                </Box>
                                                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', color: '#444' }}>
                                                    {highlightText(msg.content, msg.matched_keywords)}
                                                </Typography>
                                            </Paper>
                                        </Box>
                                    ))}
                                </Box>

                                {/* AI Reasoning HIDDEN per user request */}
                                {false && (
                                    <Box sx={{ mt: 6, opacity: 0.5 }}>
                                        <Typography variant="overline">AI Trust & Reasoning</Typography>
                                        <Paper sx={{ p: 2, bgcolor: '#f5f5f5', border: '1px dashed #ccc' }}>
                                            <Typography variant="body2" color="textSecondary">
                                                AI Chain-of-Thought reasoning will appear here in the next phase.
                                            </Typography>
                                        </Paper>
                                    </Box>
                                )}
                            </>
                        )}
                    </Box>
                </Drawer>
            </Box>
        </AdminLayout>
    );
};

export default AlertsPage;

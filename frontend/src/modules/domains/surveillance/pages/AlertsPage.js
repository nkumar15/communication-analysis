
import React, { useState, useEffect } from "react";
import AdminLayout from "../../../b2b/web/layouts/AdminLayout";
import b2bDomainClient from "../../../../core/api/b2bDomainClient";
import {
    Box, Typography, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    Chip, Button, IconButton, Drawer, TextField, MenuItem, Stack, CircularProgress
} from "@mui/material";
import { FilterList, Visibility, Warning, CheckCircle } from "@mui/icons-material";

const AlertsPage = () => {
    const [alerts, setAlerts] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [selectedAlert, setSelectedAlert] = useState(null);
    const [drawerOpen, setDrawerOpen] = useState(false);

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

            const [alertsData, statsData] = await Promise.all([
                b2bDomainClient.getAlerts(filters),
                b2bDomainClient.getAlertStats()
            ]);

            setAlerts(alertsData);
            setStats(statsData);
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

    const handleStatusUpdate = async (newStatus) => {
        if (!selectedAlert) return;
        try {
            if (newStatus === 'escalated') {
                await b2bDomainClient.escalateAlert(selectedAlert.id);
            } else if (newStatus === 'closed') {
                await b2bDomainClient.closeAlert(selectedAlert.id);
            } else {
                await b2bDomainClient.updateAlert(selectedAlert.id, { status: newStatus });
            }
            fetchAlerts(); // Refresh list
            handleCloseDrawer();
        } catch (error) {
            console.error("Update failed:", error);
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
                                <TableCell>Risk Type</TableCell>
                                <TableCell>Severity</TableCell>
                                <TableCell>Region</TableCell>
                                <TableCell>Status</TableCell>
                                <TableCell>Detected At</TableCell>
                                <TableCell>Description</TableCell>
                                <TableCell align="right">Actions</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={6} align="center"><CircularProgress /></TableCell>
                                </TableRow>
                            ) : alerts.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} align="center">No alerts found</TableCell>
                                </TableRow>
                            ) : (
                                alerts.map((alert) => (
                                    <TableRow key={alert.id} hover>
                                        <TableCell>
                                            <Typography variant="subtitle2" sx={{ textTransform: 'capitalize' }}>
                                                {(alert.risk_type || 'Unknown').replace('_', ' ')}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Chip label={alert.severity} color={getSeverityColor(alert.severity)} size="small" />
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="body2">{alert.region || 'Default'}</Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Chip label={alert.status} color={getStatusColor(alert.status)} variant="outlined" size="small" />
                                        </TableCell>
                                        <TableCell>{new Date(alert.detected_at).toLocaleString()}</TableCell>
                                        <TableCell>{alert.description}</TableCell>
                                        <TableCell align="right">
                                            <IconButton onClick={() => handleOpenDrawer(alert)} color="primary">
                                                <Visibility />
                                            </IconButton>
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
                                    <Stack direction="row" spacing={2}>
                                        <Button
                                            variant="contained"
                                            color="error"
                                            startIcon={<Warning />}
                                            onClick={() => handleStatusUpdate('escalated')}
                                            disabled={selectedAlert.status === 'escalated' || selectedAlert.status === 'closed'}
                                            fullWidth
                                        >
                                            Escalate
                                        </Button>
                                        <Button
                                            variant="contained"
                                            color="success"
                                            onClick={() => handleStatusUpdate('closed')}
                                            disabled={selectedAlert.status === 'closed'}
                                            fullWidth
                                        >
                                            Close Alert
                                        </Button>
                                        <Button
                                            variant="outlined"
                                            onClick={() => handleStatusUpdate('investigating')}
                                            disabled={selectedAlert.status === 'investigating' || selectedAlert.status === 'closed'}
                                            fullWidth
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
                                                                    label={kw}
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

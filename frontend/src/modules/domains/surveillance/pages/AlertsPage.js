
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
    const [loading, setLoading] = useState(true);
    const [selectedAlert, setSelectedAlert] = useState(null);
    const [drawerOpen, setDrawerOpen] = useState(false);

    // Filters
    const [statusFilter, setStatusFilter] = useState("");
    const [severityFilter, setSeverityFilter] = useState("");

    const fetchAlerts = async () => {
        setLoading(true);
        try {
            const filters = {};
            if (statusFilter) filters.status = statusFilter;
            if (severityFilter) filters.severity = severityFilter;

            const data = await b2bDomainClient.getAlerts(filters);
            setAlerts(data);
        } catch (error) {
            console.error("Failed to fetch alerts:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAlerts();
    }, [statusFilter, severityFilter]);

    const [communication, setCommunication] = useState(null);

    const handleOpenDrawer = async (alert) => {
        setSelectedAlert(alert);
        setCommunication(null); // Reset prev state
        setDrawerOpen(true);

        if (alert.communication_id) {
            try {
                const comm = await b2bDomainClient.getMessage(alert.communication_id);
                setCommunication(comm);
            } catch (err) {
                console.error("Failed to load communication context:", err);
            }
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

    return (
        <AdminLayout>
            <Box sx={{ p: 3 }}>
                <Typography variant="h4" sx={{ mb: 3, fontWeight: 'bold' }}>
                    Risk Alerts
                </Typography>

                {/* Filters */}
                <Paper sx={{ p: 2, mb: 3 }}>
                    <Stack direction="row" spacing={2} alignItems="center">
                        <FilterList color="action" />
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
                        <Button variant="outlined" onClick={fetchAlerts}>Refresh</Button>
                    </Stack>
                </Paper>

                {/* Table */}
                <TableContainer component={Paper}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Risk Type</TableCell>
                                <TableCell>Severity</TableCell>
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
                <Drawer anchor="right" open={drawerOpen} onClose={handleCloseDrawer}>
                    <Box sx={{ width: 400, p: 3 }}>
                        {selectedAlert && (
                            <>
                                <Typography variant="h5" sx={{ mb: 2 }}>Alert Details</Typography>

                                <Stack spacing={2}>
                                    <Paper variant="outlined" sx={{ p: 2 }}>
                                        <Typography variant="subtitle2" color="textSecondary">ID</Typography>
                                        <Typography variant="body2">{selectedAlert.id}</Typography>
                                    </Paper>

                                    <Box>
                                        <Typography variant="subtitle2">Status</Typography>
                                        <Chip label={selectedAlert.status} color={getStatusColor(selectedAlert.status)} sx={{ mt: 0.5 }} />
                                    </Box>

                                    <Box>
                                        <Typography variant="subtitle2">Severity</Typography>
                                        <Chip label={selectedAlert.severity} color={getSeverityColor(selectedAlert.severity)} sx={{ mt: 0.5 }} />
                                    </Box>

                                    <Box>
                                        <Typography variant="subtitle2">Description</Typography>
                                        <Typography variant="body1">{selectedAlert.description}</Typography>
                                    </Box>

                                    <Box>
                                        <Typography variant="subtitle2">AI Metadata</Typography>
                                        <pre style={{ background: '#f5f5f5', padding: '10px', borderRadius: '4px', overflow: 'auto' }}>
                                            {JSON.stringify(selectedAlert.metadata, null, 2)}
                                        </pre>
                                    </Box>

                                    {communication && (
                                        <Box>
                                            <Typography variant="subtitle2">Communication Context</Typography>
                                            <Paper variant="outlined" sx={{ p: 1.5, mt: 0.5, bgcolor: '#FAFAFA' }}>
                                                <Typography variant="caption" display="block">
                                                    From: {communication.sender}
                                                </Typography>
                                                <Typography variant="caption" display="block" sx={{ mb: 1 }}>
                                                    Date: {new Date(communication.timestamp).toLocaleString()}
                                                </Typography>
                                                <Box sx={{ maxHeight: 300, overflowY: 'auto', borderLeft: '3px solid #ccc', pl: 1 }}>
                                                    <Typography variant="body2" sx={{ fontStyle: 'italic', whiteSpace: 'pre-wrap' }}>
                                                        {communication.content}
                                                    </Typography>
                                                </Box>
                                            </Paper>
                                        </Box>
                                    )}

                                    <Typography variant="h6" sx={{ mt: 2 }}>Actions</Typography>
                                    <Stack direction="row" spacing={1}>
                                        <Button
                                            variant="contained"
                                            color="secondary"
                                            startIcon={<Warning />}
                                            onClick={() => handleStatusUpdate('escalated')}
                                            disabled={selectedAlert.status === 'escalated' || selectedAlert.status === 'closed'}
                                        >
                                            Escalate
                                        </Button>
                                        <Button
                                            variant="contained"
                                            color="success"
                                            startIcon={<CheckCircle />}
                                            onClick={() => handleStatusUpdate('closed')}
                                            disabled={selectedAlert.status === 'closed'}
                                        >
                                            Close
                                        </Button>
                                    </Stack>
                                    <Button
                                        variant="outlined"
                                        onClick={() => handleStatusUpdate('investigating')}
                                        disabled={selectedAlert.status === 'investigating' || selectedAlert.status === 'closed'}
                                    >
                                        Mark Investigating
                                    </Button>
                                </Stack>
                            </>
                        )}
                    </Box>
                </Drawer>
            </Box>
        </AdminLayout>
    );
};

export default AlertsPage;

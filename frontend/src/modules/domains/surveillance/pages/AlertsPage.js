import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import AdminLayout from "../../../b2b/web/layouts/AdminLayout";
import b2bDomainClient from "../../../../core/api/b2bDomainClient";
import {
    Box, Typography, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    Chip, Button, IconButton, TextField, MenuItem, Stack, CircularProgress, Tooltip, TablePagination
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

    // Pagination & Sorting
    const [page, setPage] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(20);
    const [totalcount, setTotalCount] = useState(0);
    const [sortBy, setSortBy] = useState("detected_at");
    const [sortDesc, setSortDesc] = useState(true);

    const fetchAlerts = async () => {
        setLoading(true);
        try {
            const filters = {};
            if (statusFilter) filters.status = statusFilter;
            if (severityFilter) filters.severity = severityFilter;
            if (riskTypeFilter) filters.risk_type = riskTypeFilter;
            if (regionFilter) filters.region = regionFilter;

            // Pagination params
            filters.limit = rowsPerPage;
            filters.offset = page * rowsPerPage;
            filters.sort_by = sortBy;
            filters.sort_desc = sortDesc;

            const [alertsData, statsData, usersData] = await Promise.all([
                b2bDomainClient.getAlerts(filters),
                b2bDomainClient.getAlertStats(),
                b2bClient.listUsers()
            ]);

            // Handle response which might be [data, total] or just data depending on previous client implementation
            // Assuming client update or standard response. For now assuming updated API sends x-total-count or similar, 
            // BUT backend service returns (list, count). Router returns `list`. 
            // WAIT - Router returns list only! `return alerts`. 
            // I need to update router to return boxed response or handle headers.
            // For now, let's assume strict array until router is updated to return {items, total}

            // Correction: Router returns List[AlertResponse]. To get total, I need to update router too or rely on stats?
            // Stats has total_alerts!

            setAlerts(alertsData || []);
            setStats(statsData);
            setTotalCount(statsData?.total_alerts || 0); // Approximate total from stats
            setUsers(usersData);
        } catch (error) {
            console.error("Failed to fetch alerts:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAlerts();
    }, [statusFilter, severityFilter, riskTypeFilter, regionFilter, page, rowsPerPage, sortBy, sortDesc]);

    const handleSort = (property) => {
        const isDesc = sortBy === property && sortDesc === true;
        setSortBy(property);
        setSortDesc(!isDesc); // Toggle
    };

    const handleStatusUpdate = async (alertId, newStatus, autoNavigate = false) => {
        try {
            if (newStatus === 'escalated') {
                await b2bDomainClient.escalateAlert(alertId);
            } else if (newStatus === 'closed') {
                await b2bDomainClient.closeAlert(alertId);
            } else {
                await b2bDomainClient.updateAlert(alertId, { status: newStatus });
            }
            fetchAlerts();

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
                <Paper sx={{ p: 2, mb: 3, borderRadius: 2, display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
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
                        <MenuItem value="Market Manipulation">Market Manipulation</MenuItem>
                        <MenuItem value="Evasion & Secrecy">Evasion & Secrecy</MenuItem>
                        <MenuItem value="Insider Trading">Insider Trading</MenuItem>
                        <MenuItem value="Bribery & Corruption">Bribery & Corruption</MenuItem>
                        <MenuItem value="Fraud & Deception">Fraud & Deception</MenuItem>
                        <MenuItem value="Conduct & Communications">Conduct & Communications</MenuItem>
                        <MenuItem value="Obstruction of Justice">Obstruction of Justice</MenuItem>
                        <MenuItem value="Conflict of Interest">Conflict of Interest</MenuItem>
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
                        <MenuItem value="United States (Global HQ)">United States (Global HQ)</MenuItem>
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

                    <Box sx={{ flexGrow: 1 }} />
                </Paper>

                {/* Table */}
                <TableContainer component={Paper}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell sx={{ fontWeight: 700 }} onClick={() => handleSort('display_id')} style={{ cursor: 'pointer' }}>
                                    Alert Id {sortBy === 'display_id' && (sortDesc ? '▼' : '▲')}
                                </TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Type</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>
                                    Status
                                </TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Sender</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Region</TableCell>
                                <TableCell sx={{ fontWeight: 700 }} onClick={() => handleSort('detected_at')} style={{ cursor: 'pointer' }}>
                                    Date {sortBy === 'detected_at' && (sortDesc ? '▼' : '▲')}
                                </TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Description</TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>Assignee</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 700 }}>Actions</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={9} align="center"><CircularProgress /></TableCell>
                                </TableRow>
                            ) : alerts.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={9} align="center">No alerts found</TableCell>
                                </TableRow>
                            ) : (
                                alerts.map((alert) => (
                                    <TableRow key={alert.id} hover>
                                        <TableCell sx={{ fontWeight: 600, color: '#1a73e8', fontFamily: 'monospace' }}>
                                            {alert.display_id || alert.id.substring(0, 8)}
                                        </TableCell>
                                        <TableCell sx={{ fontWeight: 500, fontSize: '0.85rem' }}>
                                            {(alert.risk_type || 'Unknown').replace('_', ' ').toUpperCase()}
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                label={alert.status.toUpperCase()}
                                                size="small"
                                                color={alert.status === 'open' ? 'warning' : alert.status === 'closed' ? 'success' : 'default'}
                                                variant="outlined"
                                                sx={{ fontSize: '0.7rem' }}
                                            />
                                        </TableCell>
                                        <TableCell sx={{ fontSize: '0.85rem' }}>
                                            {alert.communication?.sender || "System"}
                                        </TableCell>
                                        <TableCell sx={{ fontSize: '0.85rem' }}>{alert.region || "Default"}</TableCell>
                                        <TableCell sx={{ fontSize: '0.85rem', color: 'text.secondary' }}>
                                            {/* Prefer Communication Date, fallback to Detected At */}
                                            {new Date(alert.communication?.timestamp || alert.detected_at).toLocaleString('en-GB', {
                                                day: '2-digit', month: '2-digit', year: 'numeric',
                                                hour: '2-digit', minute: '2-digit', hour12: true
                                            }).replace(',', '').toUpperCase()}
                                        </TableCell>
                                        <TableCell sx={{ maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontSize: '0.85rem' }}>
                                            <Tooltip
                                                title={
                                                    <Box>
                                                        <Typography variant="body2">{alert.description}</Typography>
                                                        {alert.metadata?.matched_keywords && (
                                                            <Typography variant="caption" sx={{ display: 'block', mt: 1, color: '#ffb74d' }}>
                                                                Keywords: {Array.isArray(alert.metadata.matched_keywords) ? alert.metadata.matched_keywords.join(", ") : alert.metadata.matched_keywords}
                                                            </Typography>
                                                        )}
                                                    </Box>
                                                }
                                                arrow
                                                placement="top"
                                            >
                                                <span>{alert.description}</span>
                                            </Tooltip>
                                        </TableCell>
                                        <TableCell>
                                            <TextField
                                                select
                                                size="small"
                                                variant="standard"
                                                value={alert.assigned_to || ""}
                                                onChange={(e) => handleAssign(alert.id, e.target.value)}
                                                sx={{ minWidth: 100, fontSize: '0.8rem' }}
                                                SelectProps={{ displayEmpty: true }}
                                                InputProps={{ disableUnderline: true }}
                                            >
                                                <MenuItem value="">Unassigned</MenuItem>
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

                {/* Pagination */}
                <TablePagination
                    rowsPerPageOptions={[20, 50, 100]}
                    component="div"
                    count={totalcount}
                    rowsPerPage={rowsPerPage}
                    page={page}
                    onPageChange={(e, newPage) => setPage(newPage)}
                    onRowsPerPageChange={(e) => {
                        setRowsPerPage(parseInt(e.target.value, 10));
                        setPage(0);
                    }}
                />
            </Box>
        </AdminLayout>
    );
};

export default AlertsPage;

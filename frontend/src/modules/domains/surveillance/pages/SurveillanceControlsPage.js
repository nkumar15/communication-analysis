import React, { useState, useEffect } from "react";
import AdminLayout from "../../../b2b/web/layouts/AdminLayout";
import b2bDomainClient from "../../../../core/api/b2bDomainClient";
import {
    Box, Typography, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    Chip, Button, IconButton, Stack, CircularProgress, Alert, Tooltip
} from "@mui/material";
import { Gavel, Refresh, InfoOutlined } from "@mui/icons-material";

const SurveillanceControlsPage = () => {
    const [controls, setControls] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchControls = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await b2bDomainClient.getSurveillanceControls();
            setControls(data);
        } catch (err) {
            console.error("Failed to fetch controls:", err);
            setError("Could not load surveillance controls.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchControls();
    }, []);

    const getStatusColor = (status) => {
        switch (status?.toLowerCase()) {
            case 'active': return 'success';
            case 'inactive': return 'error';
            case 'testing': return 'warning';
            default: return 'default';
        }
    };

    return (
        <AdminLayout title="Surveillance Controls" subtitle="Manage risk detection logic and regulatory mapping">
            <Box sx={{ p: 4 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3}>
                    <Typography variant="h5" sx={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Gavel color="primary" /> Detection Rules (Controls)
                    </Typography>
                    <Button
                        startIcon={<Refresh />}
                        variant="outlined"
                        onClick={fetchControls}
                        disabled={loading}
                    >
                        Refresh
                    </Button>
                </Stack>

                {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

                <TableContainer component={Paper} elevation={2} sx={{ borderRadius: 2 }}>
                    <Table>
                        <TableHead sx={{ bgcolor: 'grey.100' }}>
                            <TableRow>
                                <TableCell sx={{ fontWeight: 'bold' }}>Risk Indicator</TableCell>
                                <TableCell sx={{ fontWeight: 'bold' }}>Typology</TableCell>
                                <TableCell sx={{ fontWeight: 'bold' }}>Regulatory Reference</TableCell>
                                <TableCell sx={{ fontWeight: 'bold' }}>Methods</TableCell>
                                <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
                                <TableCell sx={{ fontWeight: 'bold' }}>Mapping</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                                        <CircularProgress size={30} />
                                    </TableCell>
                                </TableRow>
                            ) : controls.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                                        No surveillance controls found.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                controls.map((ctrl) => (
                                    <TableRow key={ctrl.id} hover>
                                        <TableCell sx={{ fontWeight: 500 }}>{ctrl.risk_indicator}</TableCell>
                                        <TableCell>
                                            <Typography variant="body2">{ctrl.risk_typology}</Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="body2" sx={{ maxWidth: 200, noWrap: true, textOverflow: 'ellipsis', overflow: 'hidden' }}>
                                                {ctrl.regulatory_reference_text || (ctrl.regulatory_document?.title) || 'N/A'}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Stack direction="row" spacing={0.5}>
                                                {ctrl.detection_methods?.map(m => (
                                                    <Chip key={m} label={m} size="small" sx={{ fontSize: '0.7rem' }} />
                                                ))}
                                            </Stack>
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                label={ctrl.status}
                                                size="small"
                                                color={getStatusColor(ctrl.status)}
                                                variant="outlined"
                                            />
                                        </TableCell>
                                        <TableCell>
                                            {ctrl.regulatory_id ? (
                                                <Tooltip title={`Linked to: ${ctrl.regulatory_document?.title || ctrl.regulatory_id}`}>
                                                    <Chip label="Linked" size="small" variant="contained" color="info" />
                                                </Tooltip>
                                            ) : (
                                                <Chip label="Manual" size="small" variant="outlined" />
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>

                <Box mt={4} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <InfoOutlined fontSize="small" color="action" />
                    <Typography variant="body2" color="text.secondary">
                        Controls are executed as part of the dynamic risk assessment engine.
                    </Typography>
                </Box>
            </Box>
        </AdminLayout>
    );
};

export default SurveillanceControlsPage;

import React, { useState, useEffect } from "react";
import AdminLayout from "../../../b2b/web/layouts/AdminLayout";
import b2bDomainClient from "../../../../core/api/b2bDomainClient";
import {
    Box, Typography, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    Chip, Button, IconButton, Stack, CircularProgress, Alert
} from "@mui/material";
import { Description, Refresh } from "@mui/icons-material";

const RegulatoryLibraryPage = () => {
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchDocuments = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await b2bDomainClient.getRegulatoryDocuments();
            setDocuments(data);
        } catch (err) {
            console.error("Failed to fetch documents:", err);
            setError("Could not load regulatory documents.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDocuments();
    }, []);

    return (
        <AdminLayout title="Regulatory Library" subtitle="Central repository for regulatory frameworks and guidelines">
            <Box sx={{ p: 4 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3}>
                    <Typography variant="h5" sx={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Description color="primary" /> Document Repository
                    </Typography>
                    <Button
                        startIcon={<Refresh />}
                        variant="outlined"
                        onClick={fetchDocuments}
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
                                <TableCell sx={{ fontWeight: 'bold' }}>Title</TableCell>
                                <TableCell sx={{ fontWeight: 'bold' }}>Framework</TableCell>
                                <TableCell sx={{ fontWeight: 'bold' }}>Year</TableCell>
                                <TableCell sx={{ fontWeight: 'bold' }}>Version</TableCell>
                                <TableCell sx={{ fontWeight: 'bold' }}>Storage Path</TableCell>
                                <TableCell sx={{ fontWeight: 'bold' }}>Created</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                                        <CircularProgress size={30} />
                                    </TableCell>
                                </TableRow>
                            ) : documents.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                                        No regulatory documents found. Use the seed script or API to add some.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                documents.map((doc) => (
                                    <TableRow key={doc.id} hover>
                                        <TableCell sx={{ fontWeight: 500 }}>{doc.title}</TableCell>
                                        <TableCell>
                                            <Chip label={doc.framework} size="small" variant="outlined" color="primary" />
                                        </TableCell>
                                        <TableCell>{doc.year || 'N/A'}</TableCell>
                                        <TableCell>{doc.version || 'N/A'}</TableCell>
                                        <TableCell sx={{ color: 'text.secondary', fontSize: '0.8rem' }}>
                                            {doc.storage_path}
                                        </TableCell>
                                        <TableCell sx={{ color: 'text.secondary' }}>
                                            {new Date(doc.created_at).toLocaleDateString()}
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>

                <Box mt={4}>
                    <Typography variant="body2" color="text.secondary">
                        ℹ️ Note: Document ingestion (PDF upload) is currently managed via API or bulk ingestion service.
                    </Typography>
                </Box>
            </Box>
        </AdminLayout>
    );
};

export default RegulatoryLibraryPage;

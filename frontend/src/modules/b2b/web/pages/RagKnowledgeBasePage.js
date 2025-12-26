import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, TextField, Paper, Card, CardContent, Chip, CircularProgress, Alert, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, IconButton, Tooltip } from '@mui/material';
import { ContentCopy, Refresh } from '@mui/icons-material';
import b2bClient from '../../../../core/api/b2bClient';
import AdminLayout from '../layouts/AdminLayout';
import useAuth from '../../../../core/hooks/useAuth';

const RagKnowledgeBasePage = () => {
    const { user } = useAuth();
    const [tab, setTab] = useState('search'); // 'search' or 'upload'

    // Search State
    const [query, setQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [searching, setSearching] = useState(false);
    const [searchError, setSearchError] = useState('');

    // Upload State
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [uploadStatus, setUploadStatus] = useState('');
    const [jobId, setJobId] = useState(null);
    const [pollingJobId, setPollingJobId] = useState(null); // For auto-refresh

    // Fetch documents on mount or tab change
    const [documents, setDocuments] = useState([]);
    const [loadingDocs, setLoadingDocs] = useState(false);

    useEffect(() => {
        if (tab === 'upload') {
            loadDocuments();
        }
    }, [tab]);

    // Auto-refresh polling for upload status
    useEffect(() => {
        if (!pollingJobId) return;

        const interval = setInterval(async () => {
            try {
                const tenantId = user?.tenant_id || localStorage.getItem('tenant_id');
                const status = await b2bClient.checkRagStatus(pollingJobId, tenantId);

                if (status.status === 'completed' || status.status === 'failed') {
                    clearInterval(interval);
                    setPollingJobId(null);
                    setUploadStatus(status.status === 'completed'
                        ? `✅ Completed! ${status.chunk_count || 0} chunks indexed.`
                        : `❌ Failed: ${status.error_message || 'Unknown error'}`
                    );
                    loadDocuments(); // Refresh document list
                } else {
                    setUploadStatus(`⏳ ${status.status}... (${status.chunk_count || 0} chunks)`);
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        }, 2000); // Poll every 2 seconds

        return () => clearInterval(interval);
    }, [pollingJobId, user]);

    const loadDocuments = async () => {
        try {
            setLoadingDocs(true);
            const tenantId = user?.tenant_id || localStorage.getItem('tenant_id');
            const docs = await b2bClient.getDocuments(tenantId);
            setDocuments(docs);
        } catch (err) {
            console.error("Failed to load documents", err);
        } finally {
            setLoadingDocs(false);
        }
    };

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setSearching(true);
        setSearchError('');
        setSearchResults([]); // Clear previous results
        try {
            const tenantId = user?.tenant_id || localStorage.getItem('tenant_id');
            const res = await b2bClient.searchRag(query, tenantId);
            setSearchResults(res.results || []);
        } catch (err) {
            console.error(err);
            setSearchError(err.message);
        } finally {
            setSearching(false);
        }
    };

    const handleUpload = async (e) => {
        e.preventDefault();
        if (!file) return;

        setUploading(true);
        setUploadStatus('Uploading...');
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('tenant_id', user?.tenant_id || localStorage.getItem('tenant_id'));
            formData.append('company_name', user?.company_name || 'MyCompany');

            const res = await b2bClient.uploadRagDocument(formData);
            setJobId(res.job_id);
            setPollingJobId(res.job_id); // Start polling
            setUploadStatus(`⏳ Upload successful! Processing...`);
            setFile(null); // Clear input
        } catch (err) {
            setUploadStatus(`❌ Error: ${err.message}`);
        } finally {
            setUploading(false);
        }
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
    };

    // Helper to detect if text is a table
    const isTableContent = (text) => {
        const lines = text.split('\n');
        return lines.length > 3 && lines.some(line =>
            (line.match(/\d+/g) || []).length > 3 // Has multiple numbers
        );
    };

    // Helper to parse simple table (very basic)
    const parseTable = (text) => {
        const lines = text.split('\n').filter(l => l.trim());
        if (lines.length < 2) return null;

        // Try to split by spaces or tabs
        const rows = lines.map(line => line.split(/\s{2,}|\t/).filter(cell => cell.trim()));

        // Check if it looks like a table
        if (rows.some(row => row.length < 2)) return null;

        return {
            headers: rows[0],
            rows: rows.slice(1)
        };
    };

    // Format relevance score (convert negative distance to percentage)
    const formatRelevance = (score) => {
        // Assuming score is negative distance, convert to percentage
        // Lower (more negative) = better
        if (score > 0) return `${Math.round(score * 100)}%`;

        // For negative scores (distance metrics), show as-is or convert
        const relevance = Math.max(0, Math.min(100, Math.round((1 + score / 10) * 100)));
        return `${relevance}%`;
    };

    return (
        <AdminLayout title="Knowledge Base" subtitle="RAG Powered Document Search">
            <Box sx={{ padding: '32px', maxWidth: '1200px', margin: '0 auto' }}>

                {/* Tabs */}
                <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
                    <Button
                        onClick={() => setTab('search')}
                        sx={{ mr: 2, borderBottom: tab === 'search' ? '2px solid #4F46E5' : 'none', borderRadius: 0 }}
                    >
                        Search
                    </Button>
                    <Button
                        onClick={() => setTab('upload')}
                        sx={{ borderBottom: tab === 'upload' ? '2px solid #4F46E5' : 'none', borderRadius: 0 }}
                    >
                        Upload & Manage
                    </Button>
                </Box>

                {/* SEARCH TAB */}
                {tab === 'search' && (
                    <Box>
                        <Paper component="form" onSubmit={handleSearch} sx={{ p: '2px 4px', display: 'flex', alignItems: 'center', mb: 4 }}>
                            <TextField
                                sx={{ ml: 1, flex: 1 }}
                                placeholder="Search earnings transcripts, reports..."
                                variant="standard"
                                InputProps={{ disableUnderline: true }}
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                            />
                            <Button type="submit" variant="contained" disabled={searching} sx={{ m: 1, minWidth: 100 }}>
                                {searching ? <CircularProgress size={24} color="inherit" /> : 'Search'}
                            </Button>
                        </Paper>

                        {searchError && <Alert severity="error" sx={{ mb: 2 }}>{searchError}</Alert>}

                        {/* Loading State for Results */}
                        {searching && !searchResults.length && (
                            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                                <CircularProgress />
                            </Box>
                        )}

                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                            {searchResults.map((result, idx) => {
                                const isTable = isTableContent(result.text);
                                const tableData = isTable ? parseTable(result.text) : null;

                                return (
                                    <Card key={idx} variant="outlined">
                                        <CardContent>
                                            <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                                                <Box flex={1}>
                                                    <Typography variant="h6" component="div" gutterBottom>
                                                        📄 {result.metadata?.filename || result.metadata?.source || 'Document'}
                                                        {result.metadata?.page && ` • Page ${result.metadata.page}`}
                                                    </Typography>
                                                    <Box display="flex" gap={1} mb={1}>
                                                        <Chip
                                                            label={`${formatRelevance(result.score)} match`}
                                                            color="success"
                                                            size="small"
                                                        />
                                                        {result.metadata?.section && (
                                                            <Chip label={result.metadata.section} size="small" variant="outlined" />
                                                        )}
                                                    </Box>
                                                </Box>
                                                <Tooltip title="Copy to clipboard">
                                                    <IconButton size="small" onClick={() => copyToClipboard(result.text)}>
                                                        <ContentCopy fontSize="small" />
                                                    </IconButton>
                                                </Tooltip>
                                            </Box>

                                            {/* Render table if detected */}
                                            {tableData ? (
                                                <TableContainer component={Paper} variant="outlined" sx={{ mt: 2, maxHeight: 400 }}>
                                                    <Table size="small">
                                                        <TableHead>
                                                            <TableRow>
                                                                {tableData.headers.map((header, i) => (
                                                                    <TableCell key={i} sx={{ fontWeight: 'bold' }}>{header}</TableCell>
                                                                ))}
                                                            </TableRow>
                                                        </TableHead>
                                                        <TableBody>
                                                            {tableData.rows.map((row, i) => (
                                                                <TableRow key={i}>
                                                                    {row.map((cell, j) => (
                                                                        <TableCell key={j}>{cell}</TableCell>
                                                                    ))}
                                                                </TableRow>
                                                            ))}
                                                        </TableBody>
                                                    </Table>
                                                </TableContainer>
                                            ) : (
                                                <Typography
                                                    variant="body2"
                                                    sx={{
                                                        mt: 2,
                                                        whiteSpace: 'pre-wrap',
                                                        fontFamily: 'monospace',
                                                        backgroundColor: '#f5f5f5',
                                                        padding: 2,
                                                        borderRadius: 1,
                                                        maxHeight: 300,
                                                        overflow: 'auto'
                                                    }}
                                                >
                                                    {result.text}
                                                </Typography>
                                            )}
                                        </CardContent>
                                    </Card>
                                );
                            })}
                            {!searching && searchResults.length === 0 && query && !searchError && (
                                <Typography color="text.secondary" align="center">No results found.</Typography>
                            )}
                        </Box>
                    </Box>
                )}

                {/* UPLOAD TAB */}
                {tab === 'upload' && (
                    <Box>
                        <Box component={Paper} sx={{ p: 4, maxWidth: 600, mx: 'auto', mb: 4 }}>
                            <Typography variant="h6" gutterBottom>Upload New Document</Typography>
                            <Alert severity="info" sx={{ mb: 3 }}>
                                Supported formats: PDF, TXT. Documents will be processed for hybrid search.
                            </Alert>

                            <form onSubmit={handleUpload}>
                                <input
                                    type="file"
                                    accept=".pdf,.txt"
                                    onChange={(e) => setFile(e.target.files[0])}
                                    style={{ display: 'block', marginBottom: '20px', width: '100%' }}
                                />
                                <Button
                                    type="submit"
                                    variant="contained"
                                    color="primary"
                                    fullWidth
                                    disabled={!file || uploading || pollingJobId}
                                >
                                    {uploading || pollingJobId ? <CircularProgress size={24} /> : 'Start Ingestion'}
                                </Button>
                            </form>

                            {uploadStatus && (
                                <Box sx={{ mt: 2, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
                                    <Typography variant="body2">{uploadStatus}</Typography>
                                </Box>
                            )}
                        </Box>

                        {/* Document List */}
                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                            <Typography variant="h6">Uploaded Documents ({documents.length})</Typography>
                            <IconButton onClick={loadDocuments} disabled={loadingDocs}>
                                <Refresh />
                            </IconButton>
                        </Box>

                        {loadingDocs ? (
                            <Box display="flex" justifyContent="center" p={4}>
                                <CircularProgress />
                            </Box>
                        ) : (
                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                {documents.length === 0 ? (
                                    <Typography color="text.secondary">No documents uploaded yet.</Typography>
                                ) : (
                                    documents.map((doc) => (
                                        <Card key={doc.id} variant="outlined">
                                            <CardContent sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                <Box>
                                                    <Typography variant="subtitle1">{doc.filename}</Typography>
                                                    <Typography variant="body2" color="text.secondary">
                                                        Uploaded: {new Date(doc.created_at).toLocaleDateString()}
                                                        {doc.chunk_count > 0 && ` • ${doc.chunk_count} chunks`}
                                                    </Typography>
                                                    {doc.error_message && (
                                                        <Typography variant="caption" color="error">
                                                            {doc.error_message}
                                                        </Typography>
                                                    )}
                                                </Box>
                                                <Chip
                                                    label={doc.status}
                                                    color={doc.status === 'completed' ? 'success' : doc.status === 'processing' ? 'warning' : doc.status === 'failed' ? 'error' : 'default'}
                                                    size="small"
                                                    icon={doc.status === 'processing' ? <CircularProgress size={16} color="inherit" /> : null}
                                                />
                                            </CardContent>
                                        </Card>
                                    ))
                                )}
                            </Box>
                        )}
                    </Box>
                )}
            </Box>
        </AdminLayout>
    );
};

export default RagKnowledgeBasePage;

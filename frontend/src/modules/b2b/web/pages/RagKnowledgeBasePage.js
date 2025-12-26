import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, TextField, Paper, Card, CardContent, Chip, CircularProgress, Alert, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, IconButton, Tooltip, Drawer, Divider, Collapse } from '@mui/material';
import { ContentCopy, Refresh, Add, Close, ChevronLeft, ChevronRight } from '@mui/icons-material';
import b2bClient from '../../../../core/api/b2bClient';
import AdminLayout from '../layouts/AdminLayout';
import useAuth from '../../../../core/hooks/useAuth';

const RagKnowledgeBasePage = () => {
    const { user, loading: authLoading } = useAuth();

    // Search State
    const [query, setQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [searching, setSearching] = useState(false);
    const [searchError, setSearchError] = useState('');

    // Upload State
    const [uploadDrawerOpen, setUploadDrawerOpen] = useState(false);
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [uploadStatus, setUploadStatus] = useState('');
    const [jobId, setJobId] = useState(null);
    const [pollingJobId, setPollingJobId] = useState(null);

    // Documents State
    const [documents, setDocuments] = useState([]);
    const [loadingDocs, setLoadingDocs] = useState(false);
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

    // Load documents when auth completes
    useEffect(() => {
        if (!authLoading && user) {
            loadDocuments();
        }
    }, [authLoading, user]);

    // Auto-refresh polling for upload status
    useEffect(() => {
        if (!pollingJobId) return;

        const interval = setInterval(async () => {
            try {
                const tenantId = user?.tenant_id || user?.tenantId || localStorage.getItem('tenant_id');
                const status = await b2bClient.checkRagStatus(pollingJobId, tenantId);

                if (status.status === 'completed' || status.status === 'failed') {
                    clearInterval(interval);
                    setPollingJobId(null);
                    setUploadStatus(status.status === 'completed'
                        ? `✅ Completed! ${status.chunk_count || 0} chunks indexed.`
                        : `❌ Failed: ${status.error_message || 'Unknown error'}`
                    );
                    loadDocuments();

                    if (status.status === 'completed') {
                        setTimeout(() => {
                            setUploadDrawerOpen(false);
                            setUploadStatus('');
                        }, 3000);
                    }
                } else {
                    setUploadStatus(`⏳ ${status.status}... (${status.chunk_count || 0} chunks)`);
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        }, 2000);

        return () => clearInterval(interval);
    }, [pollingJobId, user]);

    const loadDocuments = async () => {
        try {
            setLoadingDocs(true);
            let tenantId = user?.tenant_id || user?.tenantId || localStorage.getItem('tenant_id');

            if (!tenantId || tenantId === 'null') {
                console.error('No valid tenant_id found. User:', user);
                setDocuments([]);
                return;
            }

            const docs = await b2bClient.getDocuments(tenantId);
            setDocuments(docs);
        } catch (err) {
            console.error("Failed to load documents", err);
            setDocuments([]);
        } finally {
            setLoadingDocs(false);
        }
    };

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setSearching(true);
        setSearchError('');
        setSearchResults([]);
        try {
            const tenantId = user?.tenant_id || user?.tenantId || localStorage.getItem('tenant_id');
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
            formData.append('tenant_id', user?.tenant_id || user?.tenantId || localStorage.getItem('tenant_id'));
            formData.append('company_name', user?.company_name || 'MyCompany');

            const res = await b2bClient.uploadRagDocument(formData);
            setJobId(res.job_id);
            setPollingJobId(res.job_id);
            setUploadStatus(`⏳ Upload successful! Processing...`);
            setFile(null);
        } catch (err) {
            setUploadStatus(`❌ Error: ${err.message}`);
        } finally {
            setUploading(false);
        }
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
    };

    const isTableContent = (text) => {
        const lines = text.split('\n');

        // Check for markdown table (has pipe separators)
        if (lines.some(line => line.includes('|') && line.split('|').length > 2)) {
            return true;
        }

        // Check for numeric table (multiple lines with 2+ numbers)
        const linesWithNumbers = lines.filter(line => {
            const numbers = line.match(/\d+(\.\d+)?/g);
            return numbers && numbers.length >= 2;
        });

        return linesWithNumbers.length >= 3;
    };

    const parseTable = (text) => {
        const lines = text.split('\n').filter(l => l.trim());
        if (lines.length < 2) return null;

        // Try markdown table first
        if (lines.some(line => line.includes('|'))) {
            const tableLines = lines.filter(line => line.includes('|'));
            const rows = tableLines.map(line =>
                line.split('|')
                    .map(cell => cell.trim())
                    .filter(cell => cell && cell !== '---' && !cell.match(/^-+$/))
            ).filter(row => row.length > 0);

            if (rows.length >= 2) {
                return {
                    headers: rows[0],
                    rows: rows.slice(1)
                };
            }
        }

        // Not a markdown table - return null to display as formatted text
        return null;
    };

    const sanitizeText = (text) => {
        if (!text) return '';
        const lines = text.split('\n');
        let result = [];
        let buffer = '';

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            // Heuristic: If line is single char (alphanumeric/symbol), treat as vertical text part
            // We interpret consecutive 1-char lines as a single word split vertically
            if (line.length === 1 && line.match(/^[a-zA-Z0-9.%]$/)) {
                buffer += line;
            } else {
                if (buffer) {
                    result.push(buffer);
                    buffer = '';
                }
                result.push(lines[i]); // Keep original line
            }
        }
        if (buffer) result.push(buffer); // Flush remaining buffer

        // Secondary pass: Join lines that look like split sentences? 
        // For now, just fixing the vertical text (1-char lines) is the biggest win.
        return result.join('\n');
    };

    const formatRelevance = (score) => {
        // Cross-encoder scores can be any value (negative for bad, positive for good)
        // Convert to percentage-like display, capped at 100%
        let relevance;

        if (score > 1) {
            // Already a percentage-like score from reranker (cap at 100)
            relevance = Math.min(100, Math.round(score * 100));
        } else if (score > 0) {
            // Score between 0-1, treat as probability
            relevance = Math.round(score * 100);
        } else {
            // Negative score (distance metric), map to 0-100
            // Closer to 0 = better match
            relevance = Math.max(0, Math.min(100, Math.round((1 + score / 10) * 100)));
        }

        return `${relevance}%`;
    };

    const sidebarWidth = sidebarCollapsed ? 0 : 350;

    return (
        <AdminLayout title="Knowledge Base" subtitle="RAG Powered Document Search">
            <Box sx={{ display: 'flex', height: 'calc(100vh - 64px)', overflow: 'hidden' }}>

                {/* Main Content Area */}
                <Box sx={{
                    flex: 1,
                    padding: '32px',
                    overflowY: 'auto',
                    transition: 'margin-right 0.3s ease',
                    marginRight: sidebarCollapsed ? '48px' : `${sidebarWidth}px`
                }}>
                    {/* Search Section */}
                    <Box sx={{ display: 'flex', justifyContent: 'center', mb: 4 }}>
                        <Paper
                            component="form"
                            onSubmit={handleSearch}
                            elevation={2}
                            sx={{
                                p: '8px 12px',
                                display: 'flex',
                                alignItems: 'center',
                                width: '100%',
                                maxWidth: '900px',
                                borderRadius: 2
                            }}
                        >
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
                    </Box>

                    {searchError && (
                        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                            <Alert severity="error" sx={{ maxWidth: '900px', width: '100%' }}>{searchError}</Alert>
                        </Box>
                    )}

                    {/* Search Results */}
                    {query && (
                        <Box sx={{ mb: 4, maxWidth: '900px', width: '100%', mx: 'auto' }}>
                            <Typography variant="h6" gutterBottom>Search Results</Typography>

                            {searching && !searchResults.length && (
                                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                                    <CircularProgress />
                                </Box>
                            )}

                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                {searchResults.map((result, idx) => {
                                    const cleanedText = sanitizeText(result.text);
                                    const isTable = isTableContent(cleanedText);
                                    const tableData = isTable ? parseTable(cleanedText) : null;

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
                                                        <IconButton size="small" onClick={() => copyToClipboard(cleanedText)}>
                                                            <ContentCopy fontSize="small" />
                                                        </IconButton>
                                                    </Tooltip>
                                                </Box>

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
                                                            fontFamily: 'Consolas, Monaco, "Andale Mono", "Ubuntu Mono", monospace',
                                                            backgroundColor: '#f8f9fa',
                                                            padding: 2,
                                                            borderRadius: 1,
                                                            maxHeight: 400,
                                                            overflow: 'auto',
                                                            lineHeight: 1.6,
                                                            fontSize: '0.85rem',
                                                            border: '1px solid #eee'
                                                        }}
                                                    >
                                                        {cleanedText}
                                                    </Typography>
                                                )}
                                            </CardContent>
                                        </Card>
                                    );
                                })}
                            </Box>
                        </Box>
                    )}

                    {!searching && searchResults.length === 0 && !searchError && query && (
                        <Typography color="text.secondary" align="center" sx={{ mt: 4 }}>No results found.</Typography>
                    )}

                    {/* Empty state when no search and no documents */}
                    {!query && documents.length === 0 && !loadingDocs && (
                        <Box sx={{ maxWidth: '900px', textAlign: 'center', p: 4, mx: 'auto' }}>
                            <Typography variant="h5" color="text.secondary" gutterBottom>
                                Welcome to your Knowledge Base
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Upload documents using the sidebar to get started
                            </Typography>
                        </Box>
                    )}
                </Box>

                {/* Sidebar - Documents List */}
                <Box sx={{
                    position: 'fixed',
                    right: 0,
                    top: '64px',
                    height: 'calc(100vh - 64px)',
                    width: sidebarCollapsed ? '48px' : `${sidebarWidth}px`,
                    backgroundColor: '#f8f9fa',
                    borderLeft: '1px solid #e0e0e0',
                    transition: 'width 0.3s ease',
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden',
                    zIndex: 10
                }}>
                    {/* Sidebar Header */}
                    <Box sx={{
                        p: 2,
                        borderBottom: '1px solid #e0e0e0',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        minHeight: '64px'
                    }}>
                        {!sidebarCollapsed && (
                            <>
                                <Typography variant="h6" sx={{ fontSize: '16px' }}>
                                    Documents ({documents.length})
                                </Typography>
                                <Box display="flex" gap={0.5}>
                                    <IconButton onClick={loadDocuments} disabled={loadingDocs} size="small">
                                        <Refresh fontSize="small" />
                                    </IconButton>
                                    <IconButton onClick={() => setSidebarCollapsed(true)} size="small">
                                        <ChevronRight fontSize="small" />
                                    </IconButton>
                                </Box>
                            </>
                        )}
                        {sidebarCollapsed && (
                            <IconButton onClick={() => setSidebarCollapsed(false)} size="small">
                                <ChevronLeft fontSize="small" />
                            </IconButton>
                        )}
                    </Box>

                    {/* Sidebar Content */}
                    {!sidebarCollapsed && (
                        <Box sx={{ flex: 1, overflowY: 'auto', p: 2 }}>
                            <Button
                                variant="contained"
                                startIcon={<Add />}
                                onClick={() => setUploadDrawerOpen(true)}
                                fullWidth
                                sx={{ mb: 2 }}
                            >
                                Upload
                            </Button>

                            {loadingDocs ? (
                                <Box display="flex" justifyContent="center" p={4}>
                                    <CircularProgress size={30} />
                                </Box>
                            ) : documents.length === 0 ? (
                                <Box sx={{ textAlign: 'center', p: 2 }}>
                                    <Typography variant="body2" color="text.secondary" gutterBottom>
                                        No documents yet
                                    </Typography>
                                </Box>
                            ) : (
                                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                                    {documents.map((doc) => (
                                        <Card key={doc.id} variant="outlined" sx={{ p: 1 }}>
                                            <Box>
                                                <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '13px' }}>
                                                    {doc.filename}
                                                </Typography>
                                                <Typography variant="caption" color="text.secondary" display="block">
                                                    {new Date(doc.created_at).toLocaleDateString()}
                                                    {doc.chunk_count > 0 && ` • ${doc.chunk_count} chunks`}
                                                </Typography>
                                                {doc.error_message && (
                                                    <Typography variant="caption" color="error" display="block">
                                                        {doc.error_message}
                                                    </Typography>
                                                )}
                                                <Chip
                                                    label={doc.status}
                                                    color={doc.status === 'completed' ? 'success' : doc.status === 'processing' ? 'warning' : doc.status === 'failed' ? 'error' : 'default'}
                                                    size="small"
                                                    sx={{ mt: 0.5, fontSize: '11px', height: '20px' }}
                                                    icon={doc.status === 'processing' ? <CircularProgress size={12} color="inherit" /> : null}
                                                />
                                            </Box>
                                        </Card>
                                    ))}
                                </Box>
                            )}
                        </Box>
                    )}
                </Box>

                {/* Upload Drawer */}
                <Drawer
                    anchor="right"
                    open={uploadDrawerOpen}
                    onClose={() => !pollingJobId && setUploadDrawerOpen(false)}
                >
                    <Box sx={{ width: 400, p: 3 }}>
                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                            <Typography variant="h6">Upload Document</Typography>
                            <IconButton
                                onClick={() => setUploadDrawerOpen(false)}
                                disabled={pollingJobId}
                                size="small"
                            >
                                <Close />
                            </IconButton>
                        </Box>

                        <Divider sx={{ mb: 3 }} />

                        <Alert severity="info" sx={{ mb: 3 }}>
                            Supported formats: PDF, TXT. Documents will be processed for hybrid search.
                        </Alert>

                        <form onSubmit={handleUpload}>
                            <Box sx={{ mb: 3 }}>
                                <input
                                    type="file"
                                    accept=".pdf,.txt"
                                    onChange={(e) => setFile(e.target.files[0])}
                                    style={{ display: 'block', width: '100%' }}
                                    disabled={uploading || pollingJobId}
                                />
                            </Box>

                            <Button
                                type="submit"
                                variant="contained"
                                color="primary"
                                fullWidth
                                disabled={!file || uploading || pollingJobId}
                                sx={{ mb: 2 }}
                            >
                                {uploading || pollingJobId ? <CircularProgress size={24} /> : 'Start Ingestion'}
                            </Button>
                        </form>

                        {uploadStatus && (
                            <Alert
                                severity={uploadStatus.includes('✅') ? 'success' : uploadStatus.includes('❌') ? 'error' : 'info'}
                                sx={{ mt: 2 }}
                            >
                                {uploadStatus}
                            </Alert>
                        )}

                        {pollingJobId && (
                            <Box sx={{ mt: 3, textAlign: 'center' }}>
                                <CircularProgress size={40} />
                                <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                                    Processing document...
                                </Typography>
                            </Box>
                        )}
                    </Box>
                </Drawer>
            </Box>
        </AdminLayout >
    );
};

export default RagKnowledgeBasePage;

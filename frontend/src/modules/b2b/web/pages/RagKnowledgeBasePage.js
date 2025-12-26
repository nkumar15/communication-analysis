import React, { useState, useEffect } from 'react';
import {
    Box,
    Container,
    Typography,
    Paper,
    TextField,
    InputAdornment,
    IconButton,
    Button,
    Card,
    CardContent,
    CircularProgress,
    Chip,
    Alert,
    Tooltip,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Drawer,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    Divider,
    Collapse,
    LinearProgress
} from '@mui/material';
import {
    Search as SearchIcon,
    CloudUpload as CloudUploadIcon,
    Description as DescriptionIcon,
    CheckCircle as CheckCircleIcon,
    Error as ErrorIcon,
    ContentCopy,
    Menu as MenuIcon,
    ChevronLeft as ChevronLeftIcon,
    Close as CloseIcon,
    Refresh as RefreshIcon
} from '@mui/icons-material';
import b2bClient from '../../../../core/api/b2bClient';
import useAuth from '../../../../core/hooks/useAuth';

const RagKnowledgeBasePage = ({ domain = 'nse' }) => {
    const { user, loading: authLoading } = useAuth();

    // Search State
    const [query, setQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [searching, setSearching] = useState(false);
    const [searchError, setSearchError] = useState(null);

    // Documents/Upload State
    const [documents, setDocuments] = useState([]);
    const [loadingDocs, setLoadingDocs] = useState(false);

    // Upload Drawer
    const [uploadDrawerOpen, setUploadDrawerOpen] = useState(false);
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [uploadStatus, setUploadStatus] = useState('');
    const [pollingJobId, setPollingJobId] = useState(null);

    // Sidebar State
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

    const isTableContent = (text) => {
        if (!text) return false;
        // Check for Markdown table structure (pipes and dashes)
        const hasPipes = text.includes('|');
        const hasDashes = text.includes('---');
        // Check for numeric table-like structure (lines with multiple numbers)
        const lines = text.split('\n');
        const numericLines = lines.filter(line => (line.match(/\d/g) || []).length > 2);

        return (hasPipes && hasDashes) || (numericLines.length > 2 && hasPipes);
    };

    const parseTable = (text) => {
        try {
            const lines = text.split('\n').filter(l => l.trim());
            // Naive markdown parser
            if (lines.length < 2) return null;

            // Check if it's a markdown table
            if (lines[1].includes('---')) {
                const headers = lines[0].split('|').map(h => h.trim()).filter(h => h);
                const rows = lines.slice(2).map(line =>
                    line.split('|').map(cell => cell.trim()).filter(cell => cell !== '')
                );
                return { headers, rows };
            }
            return null;
        } catch (e) {
            return null;
        }
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
        return result.join('\n');
    };

    const formatRelevance = (score) => {
        // Cross-encoder scores can be any value (negative for bad, positive for good)
        // Convert to percentage-like display, capped at 100%
        if (score > 1) return '100.0%';
        const percentage = Math.max(0, score) * 100;
        return `${percentage.toFixed(1)}%`;
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
    };

    const fetchDocuments = async () => {
        try {
            setLoadingDocs(true);
            const docs = await b2bClient.listRagDocuments(domain);
            setDocuments(docs || []);
        } catch (error) {
            console.error("Failed to load documents", error);
            setDocuments([]);
        } finally {
            setLoadingDocs(false);
        }
    };

    // Initial Load & Auth Wait
    useEffect(() => {
        if (user && !authLoading) {
            fetchDocuments();
        }
    }, [user, authLoading, domain]);

    // Polling for documents update (e.g. status changes)
    useEffect(() => {
        if (!user) return;
        const interval = setInterval(fetchDocuments, 10000); // Poll every 10s for general list updates
        return () => clearInterval(interval);
    }, [user, domain]);

    // Polling for specific upload job
    useEffect(() => {
        if (!pollingJobId) return;

        const interval = setInterval(async () => {
            try {
                const statusData = await b2bClient.getRagStatus(domain, pollingJobId);

                if (statusData.status === 'completed' || statusData.status === 'failed') {
                    clearInterval(interval);
                    setPollingJobId(null);
                    setUploadStatus(statusData.status === 'completed'
                        ? `✅ Completed! ${statusData.chunks || 0} chunks.`
                        : `❌ Failed: ${statusData.error || 'Unknown error'}`
                    );
                    fetchDocuments();

                    if (statusData.status === 'completed') {
                        setTimeout(() => {
                            setUploadDrawerOpen(false);
                            setUploadStatus('');
                            setFile(null);
                        }, 2000);
                    }
                } else {
                    setUploadStatus(`⏳ Processing... (${statusData.status})`);
                }
            } catch (err) {
                console.error("Polling error", err);
            }
        }, 2000);

        return () => clearInterval(interval);
    }, [pollingJobId, domain]);


    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setSearching(true);
        setSearchError(null);
        setSearchResults([]);

        try {
            const results = await b2bClient.searchRag(domain, query);
            setSearchResults(results.results || []); // Assuming API returns { results: [...] }
        } catch (error) {
            console.error("Search failed", error);
            setSearchError(error.message);
        } finally {
            setSearching(false);
        }
    };

    const handleUpload = async (e) => {
        e.preventDefault();
        if (!file) return;

        setUploading(true);
        setUploadStatus('Uploading...');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await b2bClient.uploadRagDocument(domain, formData);
            setUploadStatus('Processing...');
            setPollingJobId(res.job_id); // Start polling
        } catch (error) {
            console.error("Upload failed", error);
            setUploadStatus(`❌ Error: ${error.message}`);
        } finally {
            setUploading(false);
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'completed': return 'success';
            case 'processing': return 'warning';
            case 'failed': return 'error';
            default: return 'default';
        }
    };

    return (
        <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden', bgcolor: '#f4f6f8' }}>
            {/* Main Content Area */}
            <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

                {/* Header */}
                <Paper elevation={0} sx={{ p: 3, borderBottom: '1px solid #e0e0e0', bgcolor: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box>
                        <Typography variant="h5" fontWeight="600" color="#1a2027">
                            {domain === 'nse' ? 'NSE Knowledge Base' : 'Enron Knowledge Base'}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            Semantic Search & RAG Intelligence
                        </Typography>
                    </Box>
                    <Box>
                        <Button
                            variant="outlined"
                            startIcon={sidebarCollapsed ? <ChevronLeftIcon /> : <ChevronRightIcon />}
                            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                            sx={{ mr: 2 }}
                        >
                            {sidebarCollapsed ? 'Show Sidebar' : 'Hide Sidebar'}
                        </Button>
                        <Button
                            variant="contained"
                            startIcon={<CloudUploadIcon />}
                            onClick={() => setUploadDrawerOpen(true)}
                            sx={{ bgcolor: '#4F46E5', '&:hover': { bgcolor: '#4338CA' } }}
                        >
                            Upload Document
                        </Button>
                    </Box>
                </Paper>

                <Box sx={{ display: 'flex', flexGrow: 1, overflow: 'hidden' }}>
                    {/* Search Area */}
                    <Container maxWidth="xl" sx={{ flexGrow: 1, overflowY: 'auto', p: 4, pb: 10 }}>
                        {/* Search Bar */}
                        <Paper
                            elevation={3}
                            component="form"
                            onSubmit={handleSearch}
                            sx={{
                                p: '2px 4px',
                                display: 'flex',
                                alignItems: 'center',
                                maxWidth: '900px',
                                mx: 'auto',
                                mb: 4,
                                borderRadius: '12px',
                                border: '1px solid #e0e0e0'
                            }}
                        >
                            <InputAdornment position="start" sx={{ pl: 2 }}>
                                <SearchIcon color="action" />
                            </InputAdornment>
                            <TextField
                                sx={{ ml: 1, flex: 1 }}
                                placeholder={`Ask a question about ${domain.toUpperCase()} data...`}
                                variant="standard"
                                InputProps={{ disableUnderline: true }}
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                            />
                            <Button
                                type="submit"
                                variant="contained"
                                sx={{ m: 1, borderRadius: '8px', bgcolor: '#4F46E5', textTransform: 'none' }}
                                disabled={searching}
                            >
                                {searching ? 'Searching...' : 'Search'}
                            </Button>
                        </Paper>

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
                                        const tableData = isTable ? parseTable(result.text) : null; // Use raw text for table parse if sanitize breaks structure

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
                                <Typography color="text.secondary" paragraph>
                                    Upload PDF documents to get started. You can query financial reports, transcripts, and more.
                                </Typography>
                                <Button
                                    variant="outlined"
                                    startIcon={<CloudUploadIcon />}
                                    onClick={() => setUploadDrawerOpen(true)}
                                >
                                    Upload your first document
                                </Button>
                            </Box>
                        )}
                    </Container>

                    {/* Sidebar for Documents */}
                    <Collapse orientation="horizontal" in={!sidebarCollapsed} collapsedSize={0}>
                        <Paper
                            elevation={4}
                            sx={{
                                width: '320px',
                                borderLeft: '1px solid #e0e0e0',
                                display: 'flex',
                                flexDirection: 'column',
                                height: '100%',
                                bgcolor: 'white'
                            }}
                        >
                            <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0', bgcolor: '#f9fafb' }}>
                                <Box display="flex" justifyContent="space-between" alignItems="center">
                                    <Typography variant="subtitle1" fontWeight="600">
                                        Documents ({documents.length})
                                    </Typography>
                                    <Tooltip title="Refresh List">
                                        <IconButton size="small" onClick={fetchDocuments}>
                                            <RefreshIcon fontSize="small" />
                                        </IconButton>
                                    </Tooltip>
                                </Box>
                            </Box>

                            <List sx={{ flexGrow: 1, overflowY: 'auto' }}>
                                {loadingDocs ? (
                                    <Box display="flex" justifyContent="center" p={4}>
                                        <CircularProgress size={24} />
                                    </Box>
                                ) : (
                                    documents.map((doc, index) => (
                                        <React.Fragment key={index}>
                                            <ListItem alignItems="flex-start">
                                                <ListItemIcon sx={{ minWidth: 36, mt: 0.5 }}>
                                                    <DescriptionIcon color={doc.status === 'completed' ? 'primary' : 'disabled'} fontSize="small" />
                                                </ListItemIcon>
                                                <ListItemText
                                                    primary={
                                                        <Typography variant="body2" fontWeight="500" noWrap title={doc.filename}>
                                                            {doc.filename}
                                                        </Typography>
                                                    }
                                                    secondary={
                                                        <Box display="flex" flexDirection="column" gap={0.5} mt={0.5}>
                                                            <Box display="flex" alignItems="center" gap={1}>
                                                                <Chip
                                                                    label={doc.status}
                                                                    size="small"
                                                                    color={getStatusColor(doc.status)}
                                                                    variant="outlined"
                                                                    sx={{ height: 20, fontSize: '0.7rem' }}
                                                                />
                                                                <Typography variant="caption" color="text.secondary">
                                                                    {new Date(doc.created_at).toLocaleDateString()}
                                                                </Typography>
                                                            </Box>
                                                            {doc.error_message && (
                                                                <Typography variant="caption" color="error" sx={{ lineHeight: 1.2 }}>
                                                                    {doc.error_message}
                                                                </Typography>
                                                            )}
                                                        </Box>
                                                    }
                                                />
                                            </ListItem>
                                            <Divider component="li" />
                                        </React.Fragment>
                                    ))
                                )}
                                {!loadingDocs && documents.length === 0 && (
                                    <Box p={3} textAlign="center">
                                        <Typography variant="body2" color="text.secondary">
                                            No documents yet.
                                        </Typography>
                                    </Box>
                                )}
                            </List>
                        </Paper>
                    </Collapse>
                </Box>
            </Box>

            {/* Upload Drawer */}
            <Drawer
                anchor="right"
                open={uploadDrawerOpen}
                onClose={() => !uploading && setUploadDrawerOpen(false)}
            >
                <Box sx={{ width: 400, p: 3 }}>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                        <Typography variant="h6">Upload Document</Typography>
                        <IconButton onClick={() => setUploadDrawerOpen(false)} disabled={uploading}>
                            <CloseIcon />
                        </IconButton>
                    </Box>

                    <Box
                        sx={{
                            border: '2px dashed #e0e0e0',
                            borderRadius: 2,
                            p: 4,
                            textAlign: 'center',
                            bgcolor: '#fafafa',
                            mb: 3,
                            cursor: uploading ? 'default' : 'pointer',
                            '&:hover': { bgcolor: uploading ? '#fafafa' : '#f0f0f0' }
                        }}
                        component="label"
                    >
                        <input
                            type="file"
                            hidden
                            accept=".pdf,.txt,.md"
                            onChange={handleUpload}
                            disabled={uploading}
                        />
                        <CloudUploadIcon sx={{ fontSize: 48, color: '#bdbdbd', mb: 2 }} />
                        <Typography color="text.secondary">
                            Click to upload PDF, TXT, or MD
                            <br />
                            <Typography variant="caption" display="block" mt={1}>
                                Max size: 20MB
                            </Typography>
                        </Typography>
                    </Box>

                    {uploading && (
                        <Box mb={3}>
                            <LinearProgress sx={{ mb: 1 }} />
                            <Typography variant="caption" color="text.secondary">
                                {uploadStatus}
                            </Typography>
                        </Box>
                    )}

                    {!uploading && uploadStatus && (
                        <Alert severity={uploadStatus.includes('Error') || uploadStatus.includes('Failed') ? 'error' : 'success'} sx={{ mb: 3 }}>
                            {uploadStatus}
                        </Alert>
                    )}

                    <Box mt={4}>
                        <Alert severity="info" icon={<ScheduleIcon fontSize="inherit" />}>
                            <strong>Processing takes time.</strong>
                            <br />
                            Uploaded documents are queued for background processing (embedding & indexing). This usually takes 10-20 seconds per page.
                        </Alert>
                    </Box>
                </Box>
            </Drawer>
        </Box>
    );
};

export default RagKnowledgeBasePage;

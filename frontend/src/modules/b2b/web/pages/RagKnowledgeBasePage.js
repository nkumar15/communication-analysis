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
    ChevronRight as ChevronRightIcon,
    Close as CloseIcon,
    Refresh as RefreshIcon,
    Schedule as ScheduleIcon
} from '@mui/icons-material';
import b2bClient from '../../../../core/api/b2bClient';
import useAuth from '../../../../core/hooks/useAuth';
import AdminLayout from '../layouts/AdminLayout';

const RagKnowledgeBasePage = ({ domain = 'nse' }) => {
    const pageTitles = {
        nse: { title: 'NSE Earnings Analysis', subtitle: 'Search and analyze earnings call transcripts' },
        enron: { title: 'Enron Email Corpus', subtitle: 'Search and analyze email communications' }
    };
    const { title, subtitle } = pageTitles[domain] || { title: 'Knowledge Base', subtitle: 'Domain Knowledge Base' };

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

    const fetchDocuments = async (showLoading = true) => {
        try {
            if (showLoading) setLoadingDocs(true);
            const docs = await b2bClient.listRagDocuments(domain);
            setDocuments(docs || []);
        } catch (error) {
            console.error("Failed to load documents", error);
            setDocuments([]);
        } finally {
            if (showLoading) setLoadingDocs(false);
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
        const interval = setInterval(() => fetchDocuments(false), 10000); // Poll every 10s for general list updates (silent)
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
                    fetchDocuments(false); // Update list silently

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

    const handleFileSelect = (e) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setUploadStatus(''); // Reset status
        }
    };

    const handleUpload = async () => {
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
            setUploading(false); // Only stop uploading state on error, otherwise polling takes over
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
        <AdminLayout title={title} subtitle={subtitle}>
            {domain === 'enron' ? (
                <Box
                    display="flex"
                    flexDirection="column"
                    alignItems="center"
                    justifyContent="center"
                    height="calc(100vh - 100px)"
                    p={3}
                    textAlign="center"
                >
                    <Box sx={{ bgcolor: 'action.hover', borderRadius: '50%', p: 4, mb: 3 }}>
                        <ScheduleIcon sx={{ fontSize: 64, color: 'text.secondary', opacity: 0.5 }} />
                    </Box>
                    <Typography variant="h4" color="text.primary" gutterBottom fontWeight="600">
                        Coming Soon
                    </Typography>
                    <Typography variant="body1" color="text.secondary" maxWidth={500}>
                        The Enron Email Corpus knowledge base is currently under construction.
                        We are processing the dataset and preparing the indexes.
                    </Typography>
                </Box>
            ) : (
                <Box display="flex" height="calc(100vh - 80px)">
                    {/* Search Pane */}
                    <Box flex={1} display="flex" flexDirection="column" sx={{ borderRight: '1px solid #e0e0e0' }}>

                        {/* Search Bar */}
                        <Paper
                            elevation={0}
                            sx={{
                                p: 3,
                                borderBottom: '1px solid #e0e0e0',
                                bgcolor: 'white',
                                zIndex: 1
                            }}
                        >
                            <form onSubmit={handleSearch}>
                                <TextField
                                    fullWidth
                                    placeholder={`Search ${domain === 'nse' ? 'earnings calls' : 'emails'}... (e.g., "${domain === 'nse' ? 'revenue growth guidance' : 'risk management issues'}")`}
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    InputProps={{
                                        startAdornment: (
                                            <InputAdornment position="start">
                                                <SearchIcon sx={{ color: 'text.secondary' }} />
                                            </InputAdornment>
                                        ),
                                        endAdornment: searching && <CircularProgress size={20} />,
                                        sx: { borderRadius: 2, bgcolor: '#f8fafc' }
                                    }}
                                    sx={{
                                        '& .MuiOutlinedInput-root': {
                                            '& fieldset': { borderColor: '#e2e8f0' },
                                            '&:hover fieldset': { borderColor: '#cbd5e1' },
                                            '&.Mui-focused fieldset': { borderColor: '#6366f1' }
                                        }
                                    }}
                                />
                            </form>
                            {searchError && (
                                <Alert severity="error" sx={{ mt: 2 }}>
                                    {searchError}
                                </Alert>
                            )}
                        </Paper>

                        {/* Search Results Area */}
                        <Box
                            sx={{
                                flex: 1,
                                overflowY: 'auto',
                                bgcolor: '#f8fafc',
                                p: 3
                            }}
                        >
                            {!searching && searchResults.length === 0 && !query && (
                                <Box
                                    display="flex"
                                    flexDirection="column"
                                    alignItems="center"
                                    justifyContent="center"
                                    height="100%"
                                    color="text.secondary"
                                >
                                    <SearchIcon sx={{ fontSize: 64, opacity: 0.2, mb: 2 }} />
                                    <Typography variant="h6" color="text.secondary">
                                        Ready to search
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        Enter a query above to search through indexed documents.
                                    </Typography>
                                </Box>
                            )}

                            {searching && (
                                <Box sx={{ p: 4, textAlign: 'center' }}>
                                    <CircularProgress />
                                    <Typography sx={{ mt: 2, color: 'text.secondary' }}>
                                        Searching context...
                                    </Typography>
                                </Box>
                            )}

                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                {searchResults.map((result, index) => {
                                    // Normalize score using sigmoid for display
                                    const sigmoid = (x) => 1 / (1 + Math.exp(-x));
                                    const normalizedScore = sigmoid(result.score);

                                    return (
                                        <Card key={index} elevation={0} sx={{ border: '1px solid #e2e8f0' }}>
                                            <CardContent>
                                                <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
                                                    <Box>
                                                        <Typography variant="subtitle2" color="primary" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                            <DescriptionIcon fontSize="small" />
                                                            {result.metadata?.filename || result.metadata?.file_name || result.metadata?.source || 'Unknown Document'}
                                                        </Typography>
                                                        {result.metadata?.page_label && (
                                                            <Typography variant="caption" color="text.secondary" sx={{ ml: 3.5 }}>
                                                                Page: {result.metadata.page_label}
                                                            </Typography>
                                                        )}
                                                    </Box>
                                                    <Box display="flex" alignItems="center" gap={1}>
                                                        <Chip
                                                            label={`Score: ${(normalizedScore * 100).toFixed(1)}%`}
                                                            size="small"
                                                            color={normalizedScore > 0.7 ? 'success' : normalizedScore > 0.5 ? 'warning' : 'default'}
                                                            variant="outlined"
                                                        />
                                                        <Tooltip title="Copy Context">
                                                            <IconButton
                                                                size="small"
                                                                onClick={() => navigator.clipboard.writeText(result.text)}
                                                                sx={{ color: 'text.secondary' }}
                                                            >
                                                                <ContentCopy fontSize="small" />
                                                            </IconButton>
                                                        </Tooltip>
                                                    </Box>
                                                </Box>
                                                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', color: '#334155' }}>
                                                    {result.text}
                                                </Typography>
                                            </CardContent>
                                        </Card>
                                    );
                                })}
                            </Box>
                        </Box>
                    </Box>

                    {/* Right Panel: Documents & Upload */}
                    <Paper
                        elevation={0}
                        sx={{
                            width: sidebarCollapsed ? 60 : 380,
                            borderLeft: '1px solid #e0e0e0',
                            display: 'flex',
                            flexDirection: 'column',
                            bgcolor: 'white',
                            transition: 'width 0.3s ease',
                            overflow: 'hidden'
                        }}
                    >
                        <Box p={sidebarCollapsed ? 1 : 2} borderBottom="1px solid #e0e0e0" display="flex" justifyContent="space-between" alignItems="center" flexDirection={sidebarCollapsed ? 'column' : 'row'}>
                            {!sidebarCollapsed && (
                                <>
                                    <Typography variant="h6" sx={{ fontSize: '1rem', fontWeight: 600 }}>
                                        Knowledge Base
                                    </Typography>
                                    <Box>
                                        <Tooltip title="Refresh List">
                                            <IconButton size="small" onClick={() => fetchDocuments(true)}>
                                                <RefreshIcon fontSize="small" />
                                            </IconButton>
                                        </Tooltip>
                                        <Tooltip title="Collapse Sidebar">
                                            <IconButton size="small" onClick={() => setSidebarCollapsed(true)}>
                                                <ChevronRightIcon fontSize="small" />
                                            </IconButton>
                                        </Tooltip>
                                    </Box>
                                </>
                            )}

                            {sidebarCollapsed && (
                                <Tooltip title="Expand Sidebar">
                                    <IconButton size="small" onClick={() => setSidebarCollapsed(false)}>
                                        <ChevronLeftIcon fontSize="small" />
                                    </IconButton>
                                </Tooltip>
                            )}
                        </Box>

                        {!sidebarCollapsed && (
                            <>
                                {/* Document List */}
                                <Box flex={1} overflow="auto">
                                    {loadingDocs ? (
                                        <Box p={3} textAlign="center">
                                            <CircularProgress size={24} />
                                        </Box>
                                    ) : documents.length === 0 ? (
                                        <Box p={4} textAlign="center" color="text.secondary">
                                            <Typography variant="body2">No documents yet.</Typography>
                                        </Box>
                                    ) : (
                                        <List disablePadding>
                                            {documents.map((doc) => (
                                                <React.Fragment key={doc.id}>
                                                    <ListItem
                                                        alignItems="flex-start"
                                                        secondaryAction={
                                                            <Tooltip title={doc.status}>
                                                                {doc.status === 'completed' ? (
                                                                    <CheckCircleIcon color="success" fontSize="small" />
                                                                ) : doc.status === 'failed' ? (
                                                                    <ErrorIcon color="error" fontSize="small" />
                                                                ) : (
                                                                    <CircularProgress size={16} />
                                                                )}
                                                            </Tooltip>
                                                        }
                                                    >
                                                        <ListItemIcon sx={{ minWidth: 36, mt: 0.5 }}>
                                                            <DescriptionIcon fontSize="small" />
                                                        </ListItemIcon>
                                                        <ListItemText
                                                            primary={
                                                                <Typography variant="body2" noWrap title={doc.filename}>
                                                                    {doc.filename}
                                                                </Typography>
                                                            }
                                                            secondary={
                                                                <Typography variant="caption" color="text.secondary">
                                                                    {new Date(doc.created_at).toLocaleDateString()} • {doc.chunks_count || 0} chunks
                                                                </Typography>
                                                            }
                                                        />
                                                    </ListItem>
                                                    <Divider component="li" />
                                                </React.Fragment>
                                            ))}
                                        </List>
                                    )}
                                </Box>

                                {/* Upload Section (Collapsible) */}
                                <Box borderTop="1px solid #e0e0e0" bgcolor="#f8fafc">
                                    <Collapse in={uploadDrawerOpen}>
                                        <Box p={3}>
                                            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                                                <Typography variant="subtitle1" fontWeight="600">Upload Document</Typography>
                                                <IconButton size="small" onClick={() => setUploadDrawerOpen(false)}>
                                                    <CloseIcon fontSize="small" />
                                                </IconButton>
                                            </Box>

                                            <Typography variant="caption" color="text.secondary" paragraph display="block">
                                                Upload PDFs or text files to index them for the {domain} knowledge base.
                                            </Typography>

                                            <Box
                                                border={1}
                                                borderColor={uploading ? 'grey.300' : 'primary.main'}
                                                borderStyle="dashed"
                                                borderRadius={2}
                                                p={2}
                                                sx={{
                                                    display: 'flex',
                                                    flexDirection: 'column',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    cursor: uploading ? 'default' : 'pointer',
                                                    bgcolor: uploading ? 'action.hover' : 'background.paper',
                                                    '&:hover': { bgcolor: uploading ? 'action.hover' : 'action.hover' },
                                                    transition: 'background-color 0.2s',
                                                    minHeight: '120px'
                                                }}
                                                component="label"
                                            >
                                                <input
                                                    type="file"
                                                    style={{ display: 'none' }}
                                                    accept=".pdf,.txt,.md"
                                                    onChange={handleFileSelect}
                                                    disabled={uploading}
                                                />
                                                {file ? (
                                                    <>
                                                        <DescriptionIcon color="primary" sx={{ fontSize: 32, mb: 1 }} />
                                                        <Typography variant="body2" color="text.primary" fontWeight="500" noWrap sx={{ maxWidth: '100%' }}>
                                                            {file.name}
                                                        </Typography>
                                                        <Typography variant="caption" color="text.secondary">
                                                            {(file.size / 1024).toFixed(1)} KB
                                                        </Typography>
                                                        <Typography variant="caption" color="primary" sx={{ mt: 1 }}>
                                                            Click to change
                                                        </Typography>
                                                    </>
                                                ) : (
                                                    <>
                                                        <CloudUploadIcon color={uploading ? 'disabled' : 'primary'} sx={{ fontSize: 32, mb: 1 }} />
                                                        <Typography variant="caption" color={uploading ? 'text.secondary' : 'primary'} align="center">
                                                            {uploading ? 'Uploading...' : 'Click to select file'}
                                                        </Typography>
                                                    </>
                                                )}
                                            </Box>

                                            <Box mt={2} mb={1}>
                                                <Button
                                                    variant="contained"
                                                    fullWidth
                                                    size="small"
                                                    onClick={handleUpload}
                                                    disabled={!file || uploading}
                                                    startIcon={uploading ? <CircularProgress size={16} color="inherit" /> : <CloudUploadIcon />}
                                                >
                                                    {uploading ? 'Ingesting...' : 'Start Ingestion'}
                                                </Button>
                                            </Box>

                                            {uploadStatus && (
                                                <Box mt={2}>
                                                    <Alert
                                                        severity={getStatusColor(uploadStatus.includes('Error') || uploadStatus.includes('Failed') ? 'failed' : uploadStatus.includes('Processing') ? 'processing' : 'success')}
                                                        icon={uploadStatus.includes('Processing') ? <CircularProgress size={16} /> : undefined}
                                                        sx={{ '& .MuiAlert-message': { fontSize: '0.75rem' } }}
                                                    >
                                                        {uploadStatus}
                                                    </Alert>
                                                </Box>
                                            )}
                                        </Box>
                                    </Collapse>

                                    {!uploadDrawerOpen && (
                                        <Box p={2}>
                                            <Button
                                                variant="outlined"
                                                fullWidth
                                                startIcon={<CloudUploadIcon />}
                                                onClick={() => setUploadDrawerOpen(true)}
                                            >
                                                Upload Document
                                            </Button>
                                        </Box>
                                    )}
                                </Box>
                            </>
                        )}
                    </Paper>
                </Box>
            )}
        </AdminLayout>
    );
};

export default RagKnowledgeBasePage;

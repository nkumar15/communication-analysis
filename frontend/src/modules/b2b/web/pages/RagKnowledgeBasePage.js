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
    Schedule as ScheduleIcon,
    OpenInNew as OpenInNewIcon
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
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
    const [searchAnswer, setSearchAnswer] = useState(null); // New state for AI answer
    const [searchMetric, setSearchMetric] = useState(null); // New state for time
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

    // Upload Metadata State
    const [reportType, setReportType] = useState('earnings');
    const [financialPeriod, setFinancialPeriod] = useState('');

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


    // Polling for documents update (only if active processing exists)
    useEffect(() => {
        if (!user) return;

        // Check if any document is in a pending/processing state
        const hasPendingDocs = documents.some(doc =>
            doc.status === 'pending' || doc.status === 'processing'
        );

        if (!hasPendingDocs) return;

        // Poll every 5s if there are active documents, otherwise stop
        const interval = setInterval(() => fetchDocuments(false), 5000);
        return () => clearInterval(interval);
    }, [user, domain, documents]);

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
                            // Reset metadata
                            setReportType('earnings');
                            setFinancialPeriod('');
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
        setSearchAnswer(null); // Reset answer

        try {
            const startTime = performance.now();
            const response = await b2bClient.searchRag(domain, query);
            const endTime = performance.now();
            const durationSeconds = (endTime - startTime) / 1000;

            // Handle both old format (array) and new format ({ answer, results })
            if (response.results) {
                setSearchResults(response.results || []);
                setSearchAnswer(response.answer || null);
                setSearchMetric(durationSeconds);
            } else if (Array.isArray(response)) {
                setSearchResults(response);
                setSearchMetric(durationSeconds);
            } else {
                setSearchResults([]);
                setSearchMetric(durationSeconds);
            }
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
        if (reportType) formData.append('report_type', reportType);
        if (financialPeriod) formData.append('financial_period', financialPeriod);

        try {
            const res = await b2bClient.uploadRagDocument(domain, formData);
            setUploadStatus('Processing...');
            setPollingJobId(res.job_id); // Start polling
            setUploading(false); // Upload (request) is finished
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



    // Markdown Configuration for Material UI integration
    const MarkdownComponents = {
        // Text Typography
        p: ({ node, ...props }) => <Typography variant="body2" sx={{ color: '#334155', mb: 1, lineHeight: 1.6 }} {...props} />,
        h1: ({ node, ...props }) => <Typography variant="h6" sx={{ color: '#1e293b', mt: 2, mb: 1, fontWeight: 600 }} {...props} />,
        h2: ({ node, ...props }) => <Typography variant="subtitle1" sx={{ color: '#1e293b', mt: 2, mb: 1, fontWeight: 600 }} {...props} />,
        h3: ({ node, ...props }) => <Typography variant="subtitle2" sx={{ color: '#1e293b', mt: 1, mb: 1, fontWeight: 600 }} {...props} />,

        // Lists
        ul: ({ node, ...props }) => <Box component="ul" sx={{ pl: 2, mb: 1, color: '#334155' }} {...props} />,
        ol: ({ node, ...props }) => <Box component="ol" sx={{ pl: 2, mb: 1, color: '#334155' }} {...props} />,
        li: ({ node, ...props }) => <Typography component="li" variant="body2" sx={{ mb: 0.5 }} {...props} />,

        // Tables (The Star of the Show)
        table: ({ node, ...props }) => (
            <TableContainer component={Paper} variant="outlined" sx={{ my: 2, boxShadow: 'none', border: '1px solid #e2e8f0' }}>
                <Table size="small" aria-label="markdown table" {...props} />
            </TableContainer>
        ),
        thead: ({ node, ...props }) => <TableHead sx={{ bgcolor: '#f8fafc' }} {...props} />,
        tbody: ({ node, ...props }) => <TableBody {...props} />,
        tr: ({ node, ...props }) => <TableRow sx={{ '&:nth-of-type(even)': { bgcolor: '#fbfcfd' } }} {...props} />,
        th: ({ node, ...props }) => (
            <TableCell sx={{ fontWeight: 600, fontSize: '0.75rem', color: '#475569', borderBottom: '1px solid #e2e8f0' }} {...props} />
        ),
        td: ({ node, ...props }) => (
            <TableCell sx={{ fontSize: '0.75rem', color: '#334155', borderBottom: '1px solid #f1f5f9' }} {...props} />
        ),

        // Links
        a: ({ node, ...props }) => (
            <a {...props} style={{ color: '#6366f1', textDecoration: 'none' }} target="_blank" rel="noopener noreferrer" />
        ),

        // Code
        code: ({ node, inline, ...props }) => (
            inline
                ? <Typography component="span" sx={{ fontFamily: 'monospace', bgcolor: '#f1f5f9', p: 0.5, borderRadius: 1, fontSize: '0.75rem' }} {...props} />
                : <Box component="pre" sx={{ bgcolor: '#1e293b', color: '#f8fafc', p: 2, borderRadius: 2, overflowX: 'auto', fontSize: '0.75rem' }} {...props} />
        )
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

                            {/* AI Answer Section */}
                            {!searching && searchAnswer && (
                                <Paper
                                    elevation={0}
                                    sx={{
                                        p: 3,
                                        mb: 3,
                                        bgcolor: 'white',
                                        border: '1px solid #e2e8f0',
                                        borderRadius: 2
                                    }}
                                >
                                    <Box display="flex" alignItems="center" gap={1} mb={2}>
                                        <Typography variant="subtitle1" fontWeight="600" color="primary">
                                            AI Analysis
                                        </Typography>
                                        <Chip label="Generated by GPT-4o-mini" size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                                        {searchMetric && (
                                            <Chip
                                                label={`⏱️ ${searchMetric.toFixed(2)}s`}
                                                size="small"
                                                variant="outlined"
                                                color="info"
                                                sx={{
                                                    fontSize: '0.7rem',
                                                    borderColor: '#e0f2fe',
                                                    color: '#0284c7',
                                                    bgcolor: '#f0f9ff'
                                                }}
                                            />
                                        )}
                                    </Box>
                                    <Box sx={{ color: '#1e293b' }}>
                                        <ReactMarkdown
                                            remarkPlugins={[remarkGfm]}
                                            components={{
                                                ...MarkdownComponents,
                                                p: ({ node, ...props }) => <Typography variant="body1" sx={{ mb: 1, lineHeight: 1.6 }} {...props} />
                                            }}
                                        >
                                            {searchAnswer}
                                        </ReactMarkdown>
                                    </Box>
                                    <Divider sx={{ my: 2 }} />
                                    <Typography variant="caption" color="text.secondary">
                                        Based on {searchResults.length} relevant sources found below.
                                    </Typography>
                                </Paper>
                            )}

                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                {searchResults.length > 0 && (
                                    <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1, textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '0.5px' }}>
                                        Supporting Citations
                                    </Typography>
                                )}
                                {searchResults.map((result, index) => {
                                    // Normalize score using sigmoid for display
                                    const sigmoid = (x) => 1 / (1 + Math.exp(-x));
                                    const normalizedScore = sigmoid(result.score);
                                    const filename = result.metadata?.original_filename || result.metadata?.filename || result.metadata?.file_name || result.metadata?.source || 'Unknown Document';

                                    return (
                                        <Card key={index} elevation={0} sx={{ border: '1px solid #e2e8f0' }}>
                                            <CardContent>
                                                <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
                                                    <Box>
                                                        <Typography variant="subtitle2" color="primary" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                            <DescriptionIcon fontSize="small" />
                                                            {filename}
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
                                                                onClick={() => copyToClipboard(result.text)}
                                                                sx={{ color: 'text.secondary' }}
                                                            >
                                                                <ContentCopy fontSize="small" />
                                                            </IconButton>
                                                        </Tooltip>
                                                    </Box>
                                                </Box>

                                                {/* Render Table if Table JSON exists, else Render Text */}
                                                {result.metadata?.table_json ? (
                                                    <Box sx={{ overflowX: 'auto', mt: 1 }}>
                                                        <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid #e2e8f0', minWidth: 650 }}>
                                                            <Table size="small">
                                                                <TableHead sx={{ bgcolor: '#f8fafc' }}>
                                                                    <TableRow>
                                                                        {result.metadata.table_json.headers.map((header, i) => (
                                                                            <TableCell key={i} sx={{ fontWeight: 600, fontSize: '0.75rem', color: '#475569' }}>
                                                                                {typeof header === 'string' ? header : JSON.stringify(header)}
                                                                            </TableCell>
                                                                        ))}
                                                                    </TableRow>
                                                                </TableHead>
                                                                <TableBody>
                                                                    {result.metadata.table_json.rows.map((row, i) => (
                                                                        <TableRow key={i} sx={{ '&:nth-of-type(odd)': { bgcolor: '#fbfcfd' } }}>
                                                                            {row.map((cell, j) => (
                                                                                <TableCell key={j} sx={{ fontSize: '0.75rem', color: '#334155' }}>
                                                                                    {typeof cell === 'string' ? cell : JSON.stringify(cell)}
                                                                                </TableCell>
                                                                            ))}
                                                                        </TableRow>
                                                                    ))}
                                                                </TableBody>
                                                            </Table>
                                                        </TableContainer>
                                                        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                                                            ⚠️ Table extraction is experimental. Check original PDF if formatting looks incorrect.
                                                        </Typography>
                                                    </Box>
                                                ) : (
                                                    <Box sx={{ mt: 1 }}>
                                                        <ReactMarkdown
                                                            remarkPlugins={[remarkGfm]}
                                                            components={MarkdownComponents}
                                                        >
                                                            {result.text}
                                                        </ReactMarkdown>
                                                    </Box>
                                                )}
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

                                            {/* Metadata Controls */}
                                            <Box mb={2}>
                                                <Typography variant="caption" fontWeight="600" display="block" mb={1}>
                                                    Document Type
                                                </Typography>
                                                <Box display="flex" gap={1} mb={2}>
                                                    {['earnings', 'concall'].map((type) => (
                                                        <Chip
                                                            key={type}
                                                            label={type === 'earnings' ? 'Earnings Report' : 'Concall Transcript'}
                                                            onClick={() => setReportType(type)}
                                                            color={reportType === type ? 'primary' : 'default'}
                                                            variant={reportType === type ? 'filled' : 'outlined'}
                                                            size="small"
                                                            sx={{ textTransform: 'capitalize' }}
                                                        />
                                                    ))}
                                                </Box>

                                                <Typography variant="caption" fontWeight="600" display="block" mb={1}>
                                                    Financial Period (Optional)
                                                </Typography>
                                                <TextField
                                                    size="small"
                                                    fullWidth
                                                    placeholder="e.g. Q2 FY26"
                                                    value={financialPeriod}
                                                    onChange={(e) => setFinancialPeriod(e.target.value)}
                                                    sx={{ bgcolor: 'white', mb: 2 }}
                                                />
                                            </Box>

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

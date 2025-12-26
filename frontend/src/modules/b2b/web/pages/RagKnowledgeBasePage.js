import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, TextField, Paper, Card, CardContent, Chip, CircularProgress, Alert } from '@mui/material';
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

    // Fetch documents on mount or tab change
    const [documents, setDocuments] = useState([]);

    useEffect(() => {
        if (tab === 'upload') {
            loadDocuments();
        }
    }, [tab]);

    const loadDocuments = async () => {
        try {
            const tenantId = user?.tenant_id || localStorage.getItem('tenant_id');
            const docs = await b2bClient.getDocuments(tenantId);
            setDocuments(docs);
        } catch (err) {
            console.error("Failed to load documents", err);
        }
    };

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setSearching(true);
        setSearchError('');
        setSearchResults([]); // Clear previous results
        try {
            // Need tenantId from user context or localStorage
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
            // Optional: generic company name if not in user
            formData.append('company_name', user?.company_name || 'MyCompany');

            const res = await b2bClient.uploadRagDocument(formData);
            setJobId(res.job_id);
            setUploadStatus(`Upload successful! Job ID: ${res.job_id}. Processing in background.`);
            loadDocuments(); // Refresh list
            setFile(null); // Clear input
        } catch (err) {
            setUploadStatus(`Error: ${err.message}`);
        } finally {
            setUploading(false);
        }
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
                            {searchResults.map((result, idx) => (
                                <Card key={idx} variant="outlined">
                                    <CardContent>
                                        <Typography variant="h6" component="div" gutterBottom>
                                            {result.metadata?.company_name} - {result.metadata?.source || 'Document'}
                                        </Typography>
                                        <Typography color="text.secondary" gutterBottom sx={{ fontSize: 14 }}>
                                            Score: {result.score?.toFixed(4)} | Role: {result.metadata?.speaker_role || 'N/A'}
                                        </Typography>
                                        <Typography variant="body2" sx={{ mt: 1, whiteSpace: 'pre-wrap' }}>
                                            {result.text}
                                        </Typography>
                                    </CardContent>
                                </Card>
                            ))}
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
                                    disabled={!file || uploading}
                                >
                                    {uploading ? <CircularProgress size={24} /> : 'Start Ingestion'}
                                </Button>
                            </form>

                            {uploadStatus && (
                                <Box sx={{ mt: 2, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
                                    <Typography variant="body2">{uploadStatus}</Typography>
                                </Box>
                            )}
                        </Box>

                        {/* Document List */}
                        <Typography variant="h6" gutterBottom>Uploaded Documents</Typography>
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
                                                </Typography>
                                            </Box>
                                            <Chip
                                                label={doc.status}
                                                color={doc.status === 'completed' || doc.status === 'success' ? 'success' : doc.status === 'pending' ? 'warning' : 'default'}
                                                size="small"
                                            />
                                        </CardContent>
                                    </Card>
                                ))
                            )}
                        </Box>
                    </Box>
                )}
            </Box>
        </AdminLayout>
    );
};

export default RagKnowledgeBasePage;

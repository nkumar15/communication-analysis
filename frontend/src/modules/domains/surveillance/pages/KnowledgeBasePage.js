import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, TextField, Button, Paper, Card, CardContent, Chip, CircularProgress, Divider, Alert } from '@mui/material';
import { Search, Description, Email, DateRange, ArrowBack } from '@mui/icons-material';
import AdminLayout from '../../../b2b/web/layouts/AdminLayout';
import b2bDomainClient from '../../../../core/api/b2bDomainClient';

const KnowledgeBasePage = () => {
    const navigate = useNavigate();
    const [query, setQuery] = useState('');
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState(null);
    const [error, setError] = useState(null);

    const handleSearch = async () => {
        if (!query.trim()) return;

        setLoading(true);
        setError(null);
        setResults(null);

        try {
            const response = await b2bDomainClient.searchCommunications({
                q: query,
                limit: 10
            });
            setResults(response);
        } catch (err) {
            console.error('Search failed:', err);
            setError(err.message || 'Search failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    };

    return (
        <AdminLayout title="Institutional Knowledge Base" subtitle="RAG-powered semantic search over corporate communication archives">
            <Box sx={{ p: 4, maxWidth: 1000, margin: '0 auto' }}>
                <Button
                    startIcon={<ArrowBack />}
                    onClick={() => navigate(-1)}
                    sx={{ mb: 2 }}
                >
                    Back to Dashboard
                </Button>

                <Box textAlign="center" mb={4}>
                    <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2, fontWeight: 700 }}>
                        <Description fontSize="large" color="primary" /> Knowledge Base (RAG)
                    </Typography>
                    <Typography variant="body1" color="text.secondary">
                        Search through thousands of archived communications using semantic understanding.
                        Ask questions about past events, policy interpretations, or specific person-to-person interactions.
                    </Typography>
                </Box>

                <Paper elevation={2} sx={{ p: 2, display: 'flex', gap: 2, alignItems: 'center', borderRadius: 2 }}>
                    <Search color="action" />
                    <TextField
                        fullWidth
                        placeholder="e.g. 'Who discussed the partnership terms in October?'"
                        variant="standard"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyPress={handleKeyPress}
                        InputProps={{ disableUnderline: true, style: { fontSize: '1.1rem' } }}
                    />
                    <Button
                        variant="contained"
                        size="large"
                        onClick={handleSearch}
                        disabled={loading || !query.trim()}
                        sx={{ minWidth: 100, borderRadius: '8px' }}
                    >
                        {loading ? <CircularProgress size={24} color="inherit" /> : 'Search'}
                    </Button>
                </Paper>

                {error && (
                    <Alert severity="error" sx={{ mt: 3, borderRadius: 2 }}>{error}</Alert>
                )}

                {results && (
                    <Box sx={{ mt: 4 }}>
                        <Typography variant="h6" gutterBottom color="text.primary" fontWeight="600">
                            Found {results.count || (results.results ? results.results.length : 0)} relevant result(s)
                        </Typography>

                        {results.results && results.results.length === 0 && (
                            <Typography variant="body1" color="text.secondary" sx={{ mt: 2, fontStyle: 'italic' }}>
                                No documents matched your query in the current search scope.
                            </Typography>
                        )}

                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                            {results.results && results.results.map((item, index) => {
                                const meta = item.metadata || {};
                                return (
                                    <Card key={index} variant="outlined" sx={{ borderRadius: 2, '&:hover': { bgcolor: '#fbfbfb', borderColor: 'primary.light' } }}>
                                        <CardContent>
                                            <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
                                                <Typography variant="subtitle1" fontWeight="bold" color="primary">
                                                    {meta.subject || '(No Subject)'}
                                                </Typography>
                                                <Chip
                                                    label={`Relevance: ${item.score?.toFixed(2)}`}
                                                    size="small"
                                                    variant="outlined"
                                                    color="default"
                                                    sx={{ opacity: 0.7 }}
                                                />
                                            </Box>

                                            <Box display="flex" gap={2} mb={1.5} flexWrap="wrap">
                                                <Box display="flex" alignItems="center" gap={0.5}>
                                                    <Email fontSize="small" color="action" />
                                                    <Typography variant="caption" color="text.secondary">
                                                        From: <b>{meta.sender || 'Unknown'}</b> to <b>{meta.recipients || 'Unknown'}</b>
                                                    </Typography>
                                                </Box>
                                                {meta.date && (
                                                    <Box display="flex" alignItems="center" gap={0.5}>
                                                        <DateRange fontSize="small" color="action" />
                                                        <Typography variant="caption" color="text.secondary">
                                                            {new Date(meta.date).toLocaleDateString()}
                                                        </Typography>
                                                    </Box>
                                                )}
                                            </Box>

                                            <Divider sx={{ my: 1 }} />

                                            <Typography variant="body2" color="text.primary" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.9rem', bgcolor: '#f5f5f5', p: 1.5, borderRadius: 1 }}>
                                                {item.text}
                                            </Typography>
                                        </CardContent>
                                    </Card>
                                );
                            })}
                        </Box>
                    </Box>
                )}
            </Box>
        </AdminLayout>
    );
};

export default KnowledgeBasePage;

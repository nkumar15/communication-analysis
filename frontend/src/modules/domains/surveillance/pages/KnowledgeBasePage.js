import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, TextField, Button, Paper, Card, CardContent, Chip, CircularProgress, Divider, Alert } from '@mui/material';
import { Search, Description, Email, DateRange, ArrowBack } from '@mui/icons-material';
import AdminLayout from '../../../b2b/web/layouts/AdminLayout';
import b2bDomainClient from '../../../../core/api/b2bDomainClient';

const SearchResultCard = ({ item }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const meta = item.metadata || {};
    const highlights = item.highlights || {};
    const subjectHighlight = highlights['metadata.subject']?.[0];
    const contentHighlights = highlights['content'] || [];

    return (
        <Card variant="outlined" sx={{ borderRadius: 2, '&:hover': { bgcolor: '#fbfbfb', borderColor: 'primary.light' } }}>
            <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
                    <Typography
                        variant="subtitle1"
                        fontWeight="bold"
                        color="primary"
                        dangerouslySetInnerHTML={subjectHighlight ? { __html: subjectHighlight } : null}
                    >
                        {!subjectHighlight && (meta.subject || '(No Subject)')}
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

                {contentHighlights.length > 0 && !isExpanded ? (
                    <Box sx={{ mt: 1, bgcolor: '#f8f9fa', p: 1.5, borderRadius: 1, borderLeft: '3px solid #1976d2' }}>
                        <Typography variant="caption" color="primary" sx={{ fontWeight: 700, mb: 0.5, display: 'block' }}>
                            MATCH HIGHLIGHTS
                        </Typography>
                        {contentHighlights.map((snippet, i) => (
                            <Typography
                                key={i}
                                variant="body2"
                                color="text.primary"
                                sx={{
                                    mb: 1,
                                    fontStyle: 'italic',
                                    '& mark': { bgcolor: 'yellow', p: '2px', fontWeight: 600 }
                                }}
                                dangerouslySetInnerHTML={{ __html: `... ${snippet} ...` }}
                            />
                        ))}
                        <Button
                            size="small"
                            onClick={() => setIsExpanded(true)}
                            sx={{ mt: 1, textTransform: 'none', fontWeight: 600 }}
                        >
                            View Full Message
                        </Button>
                    </Box>
                ) : (
                    <Box>
                        <Typography variant="body2" color="text.primary" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.9rem', bgcolor: '#f5f5f5', p: 1.5, borderRadius: 1 }}>
                            {item.text}
                        </Typography>
                        {contentHighlights.length > 0 && (
                            <Button
                                size="small"
                                onClick={() => setIsExpanded(false)}
                                sx={{ mt: 1, textTransform: 'none', fontWeight: 600 }}
                            >
                                Show Highlights Only
                            </Button>
                        )}
                    </Box>
                )}
            </CardContent>
        </Card>
    );
};

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
        <AdminLayout title="Intelligence Archive" subtitle="Semantic exploration across historical communication logs and policy directives">
            <Box sx={{ p: 4, maxWidth: 1000, margin: '0 auto' }}>
                <Box textAlign="center" mb={4}>
                    <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2, fontWeight: 700 }}>
                        <Description fontSize="large" color="primary" /> Intelligence Archive
                    </Typography>
                    <Typography variant="body1" color="text.secondary">
                        Gain deep insights by querying corporate archives using advanced semantic intelligence.
                        Analyze past interactions, verify policy adherence, and trace decision-making threads across the organization.
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

                <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap', justifyContent: 'center' }}>
                    <Typography variant="caption" sx={{ alignSelf: 'center', mr: 1, color: 'text.secondary', fontWeight: 600 }}>
                        TRENDING ANALYTICS:
                    </Typography>
                    {[
                        'Raptor partnership',
                        'Andrew Fastow',
                        'California energy',
                        'LJM transaction'
                    ].map((term) => (
                        <Chip
                            key={term}
                            label={term}
                            onClick={() => {
                                setQuery(term);
                                // Trigger search in next tick after state update
                                setTimeout(handleSearch, 0);
                            }}
                            size="small"
                            variant="outlined"
                            clickable
                            sx={{
                                borderRadius: '4px',
                                '&:hover': { bgcolor: 'primary.light', color: 'white' },
                                borderStyle: 'dashed'
                            }}
                        />
                    ))}
                </Box>

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
                            {results.results && results.results.map((item, index) => (
                                <SearchResultCard key={index} item={item} />
                            ))}
                        </Box>
                    </Box>
                )}
            </Box>
        </AdminLayout>
    );
};

export default KnowledgeBasePage;

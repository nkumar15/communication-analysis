import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, TextField, Button, Paper, Card, CardContent, Alert, Chip, CircularProgress, IconButton } from '@mui/material';
import { Assessment, Security, Warning, CheckCircle, ArrowBack } from '@mui/icons-material';
import AdminLayout from './web/layouts/AdminLayout';
import b2bClient from '../../core/api/b2bClient';

import EnronGraphView from './components/EnronGraphView';

const getRiskColor = (riskLevel) => {
    switch (riskLevel?.toLowerCase()) {
        case 'high': return 'error';
        case 'medium': return 'warning';
        case 'low': return 'success';
        default: return 'default';
    }
};

const getRiskIcon = (riskLevel) => {
    switch (riskLevel?.toLowerCase()) {
        case 'high': return <Warning />;
        case 'medium': return <Security />;
        case 'low': return <CheckCircle />;
        default: return <Assessment />;
    }
};

const EnronInvestigationPage = () => {
    const navigate = useNavigate();
    const [emailText, setEmailText] = useState('');
    const [sender, setSender] = useState('');
    const [loading, setLoading] = useState(false);
    const [report, setReport] = useState(null);
    const [error, setError] = useState(null);

    const handleInvestigate = async () => {
        if (!emailText.trim()) return;

        setLoading(true);
        setError(null);
        setReport(null);

        try {
            const response = await b2bClient.post('/api/domain/enron/investigate', {
                email_text: emailText,
                email_metadata: {
                    sender: sender.trim() || undefined
                }
            });
            setReport(response);
        } catch (err) {
            console.error('Investigation failed:', err);
            setError(err.message || 'Investigation failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <AdminLayout title="Email Investigation" subtitle="Multi-Agent AI surveillance and compliance analysis">
            <Box sx={{ p: 4, maxWidth: 1200, margin: '0 auto' }}>
                <Button
                    startIcon={<ArrowBack />}
                    onClick={() => navigate(-1)}
                    sx={{ mb: 2 }}
                >
                    Back
                </Button>
                <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Assessment /> Enron Email Investigation
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                    Multi-Agent AI system for detecting fraud, policy violations, and evasion attempts
                </Typography>

                {/* Input Form */}
                <Paper sx={{ p: 3, mt: 3 }}>
                    <Typography variant="h6" gutterBottom>
                        Investigation Input
                    </Typography>

                    <TextField
                        fullWidth
                        label="Sender Email (Optional for Graph Context)"
                        placeholder="e.g. kenneth.lay@enron.com"
                        value={sender}
                        onChange={(e) => setSender(e.target.value)}
                        variant="outlined"
                        helperText="Provide a sender email to visualize their Ego Network graph."
                        sx={{ mb: 3 }}
                    />

                    <Typography variant="subtitle1" gutterBottom>
                        Email Content
                    </Typography>
                    <TextField
                        fullWidth
                        multiline
                        rows={10}
                        placeholder="Paste email content here..."
                        value={emailText}
                        onChange={(e) => setEmailText(e.target.value)}
                        variant="outlined"
                        sx={{ mb: 2 }}
                    />
                    <Button
                        variant="contained"
                        color="primary"
                        onClick={handleInvestigate}
                        disabled={!emailText.trim() || loading}
                        startIcon={loading ? <CircularProgress size={20} /> : <Assessment />}
                    >
                        {loading ? 'Investigating...' : 'Investigate Email'}
                    </Button>
                </Paper>

                {/* Error Display */}
                {error && (
                    <Alert severity="error" sx={{ mt: 3 }}>
                        {error}
                    </Alert>
                )}

                {/* Investigation Report */}
                {report && (
                    <Box sx={{ mt: 4 }}>
                        <Typography variant="h5" gutterBottom>
                            Investigation Report
                        </Typography>

                        {/* Summary Card */}
                        <Card sx={{ mb: 3, borderLeft: `5px solid`, borderLeftColor: (theme) => theme.palette[getRiskColor(report.risk_level)].main }}>
                            <CardContent>
                                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        {getRiskIcon(report.risk_level)}
                                        <Typography variant="h6">
                                            Risk Level:
                                        </Typography>
                                        <Chip
                                            label={report.risk_level.toUpperCase()}
                                            color={getRiskColor(report.risk_level)}
                                            icon={getRiskIcon(report.risk_level)}
                                        />
                                    </Box>
                                    <Chip
                                        label={report.requires_action ? 'ACTION REQUIRED' : 'No Action Needed'}
                                        color={report.requires_action ? 'error' : 'success'}
                                        variant={report.requires_action ? 'filled' : 'outlined'}
                                    />
                                </Box>
                                <Typography variant="body1" color="text.primary">
                                    <strong>Summary:</strong> {report.summary}
                                </Typography>
                                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                                    Analyzed: {new Date(report.timestamp).toLocaleString()}
                                </Typography>
                            </CardContent>
                        </Card>

                        {/* Agent Verdicts */}
                        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 2 }}>
                            {/* Intent Classification */}
                            {report.intent_verdict && (
                                <Card>
                                    <CardContent>
                                        <Typography variant="h6" gutterBottom color="primary">
                                            Intent Classification
                                        </Typography>
                                        <Typography variant="body2" gutterBottom>
                                            <strong>Classification:</strong> {report.intent_verdict.classification}
                                        </Typography>
                                        <Typography variant="body2" gutterBottom>
                                            <strong>Confidence:</strong> {report.intent_verdict.confidence ? (report.intent_verdict.confidence * 100).toFixed(0) : 'N/A'}%
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                            {report.intent_verdict.reasoning}
                                        </Typography>
                                    </CardContent>
                                </Card>
                            )}

                            {/* Policy Check */}
                            {report.policy_verdict && (
                                <Card>
                                    <CardContent>
                                        <Typography variant="h6" gutterBottom color="secondary">
                                            Policy Compliance
                                        </Typography>
                                        <Typography variant="body2" gutterBottom>
                                            <strong>Compliant:</strong> {report.policy_verdict.is_compliant ? 'Yes' : 'No'}
                                        </Typography>
                                        {!report.policy_verdict.is_compliant && (
                                            <Typography variant="body2" gutterBottom color="error">
                                                <strong>Violation:</strong> {report.policy_verdict.violation_citation}
                                            </Typography>
                                        )}
                                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                            {report.policy_verdict.reasoning}
                                        </Typography>
                                    </CardContent>
                                </Card>
                            )}

                            {/* Evasion Detection */}
                            {report.evasion_verdict && (
                                <Card>
                                    <CardContent>
                                        <Typography variant="h6" gutterBottom color="error">
                                            Evasion Detection
                                        </Typography>
                                        <Typography variant="body2" gutterBottom>
                                            <strong>Evasion Detected:</strong> {report.evasion_verdict.is_evasion ? 'Yes' : 'No'}
                                        </Typography>
                                        {report.evasion_verdict.is_evasion && (
                                            <>
                                                <Typography variant="body2" gutterBottom color="error">
                                                    <strong>Type:</strong> {report.evasion_verdict.evasion_type}
                                                </Typography>
                                                <Typography variant="body2" gutterBottom>
                                                    <strong>Evidence:</strong> {report.evasion_verdict.evidence}
                                                </Typography>
                                                <Typography variant="body2" gutterBottom>
                                                    <strong>Confidence:</strong> {report.evasion_verdict.confidence ? (report.evasion_verdict.confidence * 100).toFixed(0) : 'N/A'}%
                                                </Typography>
                                            </>
                                        )}
                                    </CardContent>
                                </Card>
                            )}
                        </Box>

                        {/* Graph Visualization */}
                        {report.graph_context && (
                            <Box sx={{ mt: 4 }}>
                                <EnronGraphView data={report.graph_context} width={1100} height={600} />
                            </Box>
                        )}
                    </Box>
                )}
            </Box>
        </AdminLayout>
    );
};

export default EnronInvestigationPage;

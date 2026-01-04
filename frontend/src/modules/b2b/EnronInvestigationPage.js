import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, TextField, Button, Paper, Card, CardContent, Alert, Chip, CircularProgress, IconButton } from '@mui/material';
import { Assessment, Security, Warning, CheckCircle, ArrowBack, History, Email, Download } from '@mui/icons-material';
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
    const [date, setDate] = useState('2001-10-22'); // Default to peak Enron crisis
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
                    sender: sender.trim() || undefined,
                    date: date || undefined
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

    const handleExportPDF = async () => {
        if (!report) return;

        try {
            // Dynamically import jsPDF
            const { default: jsPDF } = await import('jspdf');
            const doc = new jsPDF();

            let yPos = 20;
            const lineHeight = 7;
            const pageWidth = doc.internal.pageSize.getWidth();
            const margin = 20;
            const maxWidth = pageWidth - (margin * 2);

            // Helper function to add text with word wrap
            const addText = (text, fontSize = 10, isBold = false, color = [0, 0, 0]) => {
                doc.setFontSize(fontSize);
                doc.setFont(undefined, isBold ? 'bold' : 'normal');
                doc.setTextColor(...color);
                const lines = doc.splitTextToSize(text, maxWidth);
                lines.forEach(line => {
                    if (yPos > 270) {
                        doc.addPage();
                        yPos = 20;
                    }
                    doc.text(line, margin, yPos);
                    yPos += lineHeight;
                });
            };

            // Title
            addText('ENRON EMAIL INVESTIGATION REPORT', 18, true, [0, 51, 102]);
            yPos += 5;
            addText(`Generated: ${new Date(report.timestamp).toLocaleString()}`, 9, false, [100, 100, 100]);
            yPos += 5;

            // Risk Level
            const riskColor = report.risk_level.toLowerCase() === 'high' ? [211, 47, 47] :
                report.risk_level.toLowerCase() === 'medium' ? [237, 108, 2] : [46, 125, 50];
            addText(`RISK LEVEL: ${report.risk_level.toUpperCase()}`, 14, true, riskColor);
            addText(`ACTION REQUIRED: ${report.requires_action ? 'YES' : 'NO'}`, 12, true);
            yPos += 3;

            // Summary
            addText('SUMMARY:', 12, true);
            addText(report.summary, 10);
            yPos += 3;

            // Intent Classification
            if (report.intent_verdict) {
                addText('INTENT CLASSIFICATION:', 12, true, [0, 51, 102]);
                addText(`Classification: ${report.intent_verdict.classification}`, 10);
                addText(`Confidence: ${(report.intent_verdict.confidence * 100).toFixed(0)}%`, 10);
                addText(`Reasoning: ${report.intent_verdict.reasoning}`, 10);
                yPos += 3;
            }

            // Policy Compliance
            if (report.policy_verdict) {
                addText('POLICY COMPLIANCE:', 12, true, [0, 51, 102]);
                addText(`Compliant: ${report.policy_verdict.is_compliant ? 'Yes' : 'No'}`, 10);
                if (!report.policy_verdict.is_compliant) {
                    addText(`Violation: ${report.policy_verdict.violation_citation}`, 10, false, [211, 47, 47]);
                }
                addText(`Reasoning: ${report.policy_verdict.reasoning}`, 10);
                yPos += 3;
            }

            // Evasion Detection
            if (report.evasion_verdict) {
                addText('EVASION DETECTION:', 12, true, [0, 51, 102]);
                addText(`Evasion Detected: ${report.evasion_verdict.is_evasion ? 'Yes' : 'No'}`, 10);
                if (report.evasion_verdict.is_evasion) {
                    addText(`Type: ${report.evasion_verdict.evasion_type}`, 10, false, [211, 47, 47]);
                    addText(`Evidence: ${report.evasion_verdict.evidence}`, 10);
                    addText(`Confidence: ${(report.evasion_verdict.confidence * 100).toFixed(0)}%`, 10);
                }
                yPos += 3;
            }

            // Case Timeline
            if (report.timeline && report.timeline.length > 0) {
                addText(`CASE TIMELINE (${report.timeline.length} emails):`, 12, true, [0, 51, 102]);
                report.timeline.forEach((event, i) => {
                    addText(`${i + 1}. ${new Date(event.date).toLocaleString()}`, 10, true);
                    addText(`   Subject: ${event.subject || '(No Subject)'}`, 9);
                    addText(`   From: ${event.sender}`, 9);
                    addText(`   Snippet: ${event.snippet}`, 9, false, [80, 80, 80]);
                    yPos += 2;
                });
                yPos += 3;
            }

            // Evidence Pack
            if (report.evidence_pack && report.evidence_pack.length > 0) {
                addText('EVIDENCE PACK:', 12, true, [0, 51, 102]);
                addText(`Total emails: ${report.evidence_pack.length}`, 10);
                addText(`IDs: ${report.evidence_pack.join(', ')}`, 9, false, [80, 80, 80]);
            }

            // Save PDF
            doc.save(`enron-investigation-${Date.now()}.pdf`);
        } catch (error) {
            console.error('PDF generation failed:', error);
            alert('Failed to generate PDF. Please try again.');
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

                    <TextField
                        fullWidth
                        type="date"
                        label="Reference Date"
                        InputLabelProps={{ shrink: true }}
                        value={date}
                        onChange={(e) => setDate(e.target.value)}
                        variant="outlined"
                        helperText="Required for Case Timeline (e.g., approximate date of the email). Try: 2001-10-22"
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


                        {/* Case Timeline (Investigation Assembly) */}
                        {report.timeline && report.timeline.length > 0 && (
                            <Box sx={{ mt: 4 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                    <Typography variant="h5" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        <History /> Case Timeline
                                    </Typography>
                                    <Button
                                        variant="outlined"
                                        size="small"
                                        startIcon={<Download />}
                                        onClick={handleExportPDF}
                                    >
                                        Export Report
                                    </Button>
                                </Box>
                                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#fafafa' }}>
                                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                        {report.timeline.map((event, index) => (
                                            <Box key={index} sx={{ display: 'flex', gap: 2 }}>
                                                {/* Date Column */}
                                                <Box sx={{ minWidth: 150, textAlign: 'right' }}>
                                                    <Typography variant="body2" fontWeight="bold" color="text.secondary">
                                                        {new Date(event.date).toLocaleDateString()}
                                                    </Typography>
                                                    <Typography variant="caption" color="text.secondary">
                                                        {new Date(event.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                    </Typography>
                                                </Box>

                                                {/* Line */}
                                                <Box sx={{ width: 2, bgcolor: 'divider', position: 'relative' }}>
                                                    <Box sx={{
                                                        width: 10, height: 10, borderRadius: '50%', bgcolor: 'primary.main',
                                                        position: 'absolute', left: -4, top: 4
                                                    }} />
                                                </Box>

                                                {/* Content */}
                                                <Box sx={{ flex: 1, pb: 2 }}>
                                                    <Card variant="outlined" sx={{ '&:hover': { borderColor: 'primary.main' } }}>
                                                        <CardContent sx={{ py: 1, px: 2, '&:last-child': { pb: 1 } }}>
                                                            <Typography variant="subtitle2" color="primary" fontWeight="bold">
                                                                {event.subject || '(No Subject)'}
                                                            </Typography>
                                                            <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                                                                <Email fontSize="inherit" color="action" />
                                                                <Typography variant="caption" color="text.secondary">
                                                                    From: {event.sender || 'Unknown'}
                                                                </Typography>
                                                            </Box>
                                                            <Typography variant="body2" sx={{
                                                                fontFamily: 'monospace', fontSize: '0.85rem',
                                                                display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden'
                                                            }}>
                                                                {event.snippet}
                                                            </Typography>
                                                        </CardContent>
                                                    </Card>
                                                </Box>
                                            </Box>
                                        ))}
                                    </Box>
                                </Paper>
                            </Box>
                        )}

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

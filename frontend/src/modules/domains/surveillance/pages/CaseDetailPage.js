import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Box, Typography, Paper, Grid, Chip, Divider,
    TextField, Button, List, ListItem, ListItemText,
    CircularProgress, Alert, Card, CardContent, Dialog, DialogTitle,
    DialogContent, DialogActions, IconButton, Tooltip
} from '@mui/material';
import {
    History, Assignment, Gavel, AccessTime,
    Send, CheckCircle, Warning, ArrowBack,
    Description, AttachFile, Person
} from '@mui/icons-material';
import AdminLayout from '../../../b2b/web/layouts/AdminLayout';
import b2bDomainClient from '../../../../core/api/b2bDomainClient';

const STATUS_COLORS = {
    'open': 'primary',
    'in_review': 'warning',
    'escalated': 'error',
    'closed': 'success',
};

const CaseDetailPage = () => {
    const { caseId } = useParams();
    const navigate = useNavigate();
    const [caseData, setCaseData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [note, setNote] = useState('');
    const [rationale, setRationale] = useState('');
    const [isClosing, setIsClosing] = useState(false);
    const [closeDialogOpen, setCloseDialogOpen] = useState(false);

    useEffect(() => {
        fetchCase();
    }, [caseId]);

    const fetchCase = async () => {
        try {
            setLoading(true);
            const data = await b2bDomainClient.getCase(caseId);
            setCaseData(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleAddNote = async () => {
        if (!note.trim()) return;
        try {
            await b2bDomainClient.addCaseNote(caseId, { content: note });
            setNote('');
            fetchCase();
        } catch (err) {
            alert('Failed to add note');
        }
    };

    const handleCloseCase = async () => {
        if (!rationale.trim()) return;
        setIsClosing(true);
        try {
            await b2bDomainClient.updateCase(caseId, {
                status: 'closed',
                decision_rationale: rationale
            });
            setCloseDialogOpen(false);
            fetchCase();
        } catch (err) {
            alert(err.message);
        } finally {
            setIsClosing(false);
        }
    };

    const handleEscalate = async () => {
        try {
            await b2bDomainClient.updateCase(caseId, { status: 'escalated' });
            fetchCase();
        } catch (err) {
            alert('Escalation failed');
        }
    };

    if (loading) return <AdminLayout><Box sx={{ display: 'flex', justifyContent: 'center', p: 8 }}><CircularProgress /></Box></AdminLayout>;
    if (error) return <AdminLayout><Box sx={{ p: 4 }}><Alert severity="error">{error}</Alert></Box></AdminLayout>;
    if (!caseData) return <AdminLayout><Typography sx={{ p: 4 }}>Case not found.</Typography></AdminLayout>;

    const isClosed = caseData.status === 'closed';

    return (
        <AdminLayout title="Case Management Workbench">
            <Box sx={{ p: 4, maxWidth: 1400, margin: '0 auto' }}>
                {/* Header Navigation */}
                <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Button
                        startIcon={<ArrowBack />}
                        onClick={() => navigate('/b2b/surveillance/cases')}
                        sx={{ color: 'text.secondary' }}
                    >
                        Back to Cases
                    </Button>
                    <Box sx={{ display: 'flex', gap: 2 }}>
                        {!isClosed && (
                            <>
                                <Button
                                    variant="outlined"
                                    color="error"
                                    onClick={handleEscalate}
                                    disabled={caseData.status === 'escalated'}
                                >
                                    Escalate Case
                                </Button>
                                <Button
                                    variant="contained"
                                    color="success"
                                    onClick={() => setCloseDialogOpen(true)}
                                >
                                    Close Case
                                </Button>
                            </>
                        )}
                        {isClosed && (
                            <Chip label="ARCHIVED / CLOSED" color="success" variant="outlined" />
                        )}
                    </Box>
                </Box>

                <Grid container spacing={4}>
                    {/* Left Column: Metadata & Evidence */}
                    <Grid item xs={12} md={7}>
                        <Card sx={{ mb: 4, borderRadius: 2 }}>
                            <CardContent>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                                    <Typography variant="h5" fontWeight="700">
                                        {caseData.title}
                                    </Typography>
                                    <Chip
                                        label={caseData.status.toUpperCase()}
                                        color={STATUS_COLORS[caseData.status]}
                                        size="small"
                                        sx={{ fontWeight: 'bold' }}
                                    />
                                </Box>
                                <Typography variant="body1" color="text.secondary" paragraph>
                                    {caseData.description || "No description provided."}
                                </Typography>

                                <Box sx={{ display: 'flex', gap: 4, mt: 3 }}>
                                    <Box>
                                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>PRIORITY</Typography>
                                        <Typography variant="body2" fontWeight="600" sx={{ textTransform: 'capitalize' }}>
                                            {caseData.priority}
                                        </Typography>
                                    </Box>
                                    <Box>
                                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>ASSIGNEE</Typography>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                            <Person fontSize="small" />
                                            <Typography variant="body2">{caseData.assigned_to_user_id ? 'Analyst Assigned' : 'Unassigned'}</Typography>
                                        </Box>
                                    </Box>
                                    <Box>
                                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>SLA TARGET</Typography>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                            <AccessTime fontSize="small" color={caseData.target_closure_date ? 'error' : 'disabled'} />
                                            <Typography variant="body2">
                                                {caseData.target_closure_date ? new Date(caseData.target_closure_date).toLocaleDateString() : 'None'}
                                            </Typography>
                                        </Box>
                                    </Box>
                                </Box>
                            </CardContent>
                        </Card>

                        {/* Evidence Section */}
                        <Typography variant="h6" gutterBottom fontWeight="700" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <AttachFile fontSize="small" /> Evidence & Citations
                        </Typography>
                        <Paper sx={{ mb: 4, borderRadius: 2 }}>
                            <List>
                                {caseData.evidence?.length > 0 ? (
                                    caseData.evidence.map((ev, idx) => (
                                        <React.Fragment key={ev.id}>
                                            <ListItem alignItems="flex-start">
                                                <ListItemText
                                                    primary={`${ev.evidence_type.toUpperCase()}: ${ev.evidence_id}`}
                                                    secondary={ev.notes || "Linked as supporting evidence."}
                                                />
                                                <Button size="small">View Detail</Button>
                                            </ListItem>
                                            {idx < caseData.evidence.length - 1 && <Divider component="li" />}
                                        </React.Fragment>
                                    ))
                                ) : (
                                    <ListItem>
                                        <ListItemText secondary="No evidence linked to this case yet." />
                                    </ListItem>
                                )}
                            </List>
                        </Paper>

                        {isClosed && caseData.decision_rationale && (
                            <>
                                <Typography variant="h6" gutterBottom fontWeight="700" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <Gavel fontSize="small" /> Final Decision Rationale
                                </Typography>
                                <Paper sx={{ p: 3, mb: 4, bgcolor: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: 2 }}>
                                    <Typography variant="body1">{caseData.decision_rationale}</Typography>
                                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                                        Closed at: {new Date(caseData.closed_at).toLocaleString()}
                                    </Typography>
                                </Paper>
                            </>
                        )}
                    </Grid>

                    {/* Right Column: Discussion / Audit Trail */}
                    <Grid item xs={12} md={5}>
                        <Paper sx={{ p: 0, height: '100%', display: 'flex', flexDirection: 'column', minHeight: '600px', borderRadius: 2 }}>
                            <Box sx={{ p: 2, borderBottom: '1px solid #E5E7EB', display: 'flex', alignItems: 'center', gap: 1 }}>
                                <History color="action" />
                                <Typography variant="subtitle1" fontWeight="700">Internal Notes & Audit Trail</Typography>
                            </Box>

                            <Box sx={{ flex: 1, p: 2, overflowY: 'auto' }}>
                                <List sx={{ width: '100%' }}>
                                    {caseData.notes?.map((n) => (
                                        <ListItem
                                            key={n.id}
                                            alignItems="flex-start"
                                            sx={{
                                                mb: 2,
                                                bgcolor: n.author_id === caseData.assigned_to_user_id ? '#F3F4F6' : 'transparent',
                                                borderRadius: 2
                                            }}
                                        >
                                            <ListItemText
                                                primary={
                                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                                                        <Typography variant="subtitle2" fontWeight="700">Analyst</Typography>
                                                        <Typography variant="caption" color="text.secondary">{new Date(n.created_at).toLocaleString()}</Typography>
                                                    </Box>
                                                }
                                                secondary={
                                                    <Typography variant="body2" color="text.primary">{n.content}</Typography>
                                                }
                                            />
                                        </ListItem>
                                    ))}
                                    {(!caseData.notes || caseData.notes.length === 0) && (
                                        <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
                                            <Description sx={{ fontSize: 40, opacity: 0.3, mb: 1 }} />
                                            <Typography variant="body2">No notes added yet.</Typography>
                                        </Box>
                                    )}
                                </List>
                            </Box>

                            {!isClosed && (
                                <Box sx={{ p: 2, borderTop: '1px solid #E5E7EB' }}>
                                    <TextField
                                        fullWidth
                                        multiline
                                        rows={3}
                                        placeholder="Add an internal note..."
                                        value={note}
                                        onChange={(e) => setNote(e.target.value)}
                                        sx={{ mb: 1 }}
                                    />
                                    <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                                        <Button
                                            variant="contained"
                                            endIcon={<Send />}
                                            onClick={handleAddNote}
                                            disabled={!note.trim()}
                                        >
                                            Add Note
                                        </Button>
                                    </Box>
                                </Box>
                            )}
                        </Paper>
                    </Grid>
                </Grid>
            </Box>

            {/* Close Case Dialog */}
            <Dialog open={closeDialogOpen} onClose={() => setCloseDialogOpen(false)} fullWidth maxWidth="sm">
                <DialogTitle sx={{ fontWeight: 700 }}>Close Compliance Case</DialogTitle>
                <DialogContent>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Closing a case requires a final decision rationale for audit purposes. This action is immutable.
                    </Typography>
                    <TextField
                        fullWidth
                        multiline
                        rows={4}
                        label="Decision Rationale"
                        placeholder="Explain why this case is being closed (e.g., No violation found, remediation complete, etc.)"
                        value={rationale}
                        onChange={(e) => setRationale(e.target.value)}
                        required
                    />
                </DialogContent>
                <DialogActions sx={{ p: 3 }}>
                    <Button onClick={() => setCloseDialogOpen(false)}>Cancel</Button>
                    <Button
                        variant="contained"
                        color="success"
                        onClick={handleCloseCase}
                        disabled={!rationale.trim() || isClosing}
                    >
                        {isClosing ? <CircularProgress size={24} /> : "Record Decision & Close Case"}
                    </Button>
                </DialogActions>
            </Dialog>
        </AdminLayout>
    );
};

export default CaseDetailPage;

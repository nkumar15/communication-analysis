import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Box, Typography, Paper, Grid, Chip, Divider,
    TextField, Button, List, ListItem, ListItemText,
    CircularProgress, Alert, Card, CardContent, Dialog, DialogTitle,
    DialogContent, DialogActions, IconButton, Tooltip, Tabs, Tab,
    LinearProgress, Avatar, Stack
} from '@mui/material';
import {
    History, Assignment, Gavel, AccessTime,
    Send, CheckCircle, Warning, ArrowBack,
    Description, AttachFile, Person, Event,
    Public, PriorityHigh, FileDownload
} from '@mui/icons-material';
import AdminLayout from '../../../b2b/web/layouts/AdminLayout';
import b2bDomainClient from '../../../../core/api/b2bDomainClient';

const STATUS_COLORS = {
    'open': 'primary',
    'in_review': 'warning',
    'escalated': 'error',
    'closed': 'success',
};

const TAB_MAP = {
    0: 'Details',
    1: 'Timeline',
    2: 'Evidence Attachments'
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
    const [activeTab, setActiveTab] = useState(0);

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

    const calculateSLAPercentage = () => {
        if (!caseData?.target_closure_date) return 0;
        const start = new Date(caseData.created_at).getTime();
        const end = new Date(caseData.target_closure_date).getTime();
        const now = new Date().getTime();

        const total = end - start;
        const elapsed = now - start;
        return Math.min(Math.max((elapsed / total) * 100, 0), 100);
    };

    if (loading) return <AdminLayout><Box sx={{ display: 'flex', justifyContent: 'center', p: 8 }}><CircularProgress /></Box></AdminLayout>;
    if (error) return <AdminLayout><Box sx={{ p: 4 }}><Alert severity="error">{error}</Alert></Box></AdminLayout>;
    if (!caseData) return <AdminLayout><Typography sx={{ p: 4 }}>Case not found.</Typography></AdminLayout>;

    const isClosed = caseData.status === 'closed';
    const slaPercent = calculateSLAPercentage();

    return (
        <AdminLayout>
            <Box sx={{ p: 4, bgcolor: '#f8f9fa', minHeight: '100vh' }}>
                {/* Header Section */}
                <Paper sx={{ p: 3, mb: 3, borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.04)' }}>
                    <Box sx={{ mb: 2 }}>
                        <Button startIcon={<ArrowBack />} onClick={() => navigate('/b2b/surveillance/cases')} sx={{ mb: 2 }}>
                            Back to Queue
                        </Button>
                    </Box>

                    <Grid container spacing={4} alignItems="center">
                        <Grid item xs={12} md={4}>
                            <Typography variant="caption" color="textSecondary" sx={{ fontWeight: 700, letterSpacing: 1 }}>
                                CASE ID: CASE-{caseData.id.substring(0, 8).toUpperCase()}
                            </Typography>
                            <Typography variant="h4" sx={{ fontWeight: 800, mt: 0.5 }}>
                                {typeof caseData.title === 'object' ? (caseData.title.type || JSON.stringify(caseData.title)) : caseData.title}
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 1, mt: 1.5 }}>
                                <Chip label={caseData.priority.toUpperCase()} color={caseData.priority === 'high' || caseData.priority === 'critical' ? 'error' : 'default'} size="small" sx={{ fontWeight: 700 }} />
                                <Chip label={caseData.status.replace('_', ' ').toUpperCase()} color={STATUS_COLORS[caseData.status]} size="small" variant="outlined" sx={{ fontWeight: 700 }} />
                            </Box>
                        </Grid>

                        <Grid item xs={12} md={4}>
                            <Stack direction="row" spacing={2} alignItems="center">
                                <Avatar sx={{ bgcolor: '#eee', color: '#666' }}>
                                    <Person />
                                </Avatar>
                                <Box>
                                    <Typography variant="caption" color="textSecondary" display="block">OWNER</Typography>
                                    <Typography variant="body2" fontWeight="700">John Smith (Assigned)</Typography>
                                    <Button size="small" sx={{ p: 0, textTransform: 'none', fontSize: '0.75rem' }}>Change</Button>
                                </Box>
                            </Stack>
                        </Grid>

                        <Grid item xs={12} md={4}>
                            <Box>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                    <Typography variant="caption" color="textSecondary" sx={{ fontWeight: 700 }}>SLA REMAINING</Typography>
                                    <Typography variant="caption" color={slaPercent > 80 ? 'error' : 'textSecondary'} sx={{ fontWeight: 700 }}>
                                        {caseData.target_closure_date ? '3 Days Remaining' : 'No SLA'}
                                    </Typography>
                                </Box>
                                <LinearProgress
                                    variant="determinate"
                                    value={slaPercent}
                                    color={slaPercent > 80 ? 'error' : 'primary'}
                                    sx={{ height: 8, borderRadius: 4 }}
                                />
                            </Box>
                        </Grid>
                    </Grid>
                </Paper>

                {/* Tabs Navigation */}
                <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
                    <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)}>
                        <Tab label="Case Details" icon={<Description />} iconPosition="start" />
                        <Tab label="Timeline" icon={<History />} iconPosition="start" />
                        <Tab label="Evidence Attachments" icon={<AttachFile />} iconPosition="start" />
                    </Tabs>
                </Box>

                <Grid container spacing={3}>
                    {/* Main Content Area */}
                    <Grid item xs={12} md={8}>
                        {activeTab === 0 && (
                            <Paper sx={{ p: 4, borderRadius: 3 }}>
                                <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>Description</Typography>
                                <Typography variant="body1" color="text.primary" sx={{ whiteSpace: 'pre-wrap', mb: 4, lineHeight: 1.6 }}>
                                    {caseData.description || "No description provided."}
                                </Typography>

                                <Grid container spacing={4}>
                                    <Grid item xs={6}>
                                        <Typography variant="caption" color="textSecondary" sx={{ fontWeight: 700 }}>INCIDENT DATE</Typography>
                                        <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1 }}>
                                            <Event color="action" />
                                            <Typography variant="body1" fontWeight="600">{new Date(caseData.created_at).toLocaleDateString()}</Typography>
                                        </Stack>
                                    </Grid>
                                    <Grid item xs={6}>
                                        <Typography variant="caption" color="textSecondary" sx={{ fontWeight: 700 }}>IMPACT</Typography>
                                        <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1 }}>
                                            <PriorityHigh color="error" />
                                            <Typography variant="body1" fontWeight="600">High Risk / Financial</Typography>
                                        </Stack>
                                    </Grid>
                                    <Grid item xs={12}>
                                        <Typography variant="caption" color="textSecondary" sx={{ fontWeight: 700 }}>RELATED ENTITIES</Typography>
                                        <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                                            {['Internal-Desk-A', 'Market-Reg-X', 'External-Trade-Node'].map(tag => (
                                                <Chip key={tag} label={tag} variant="outlined" size="small" />
                                            ))}
                                        </Stack>
                                    </Grid>
                                </Grid>

                                {isClosed && caseData.decision_rationale && (
                                    <Box sx={{ mt: 6 }}>
                                        <Divider sx={{ mb: 4 }} />
                                        <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, color: 'success.main', display: 'flex', alignItems: 'center', gap: 1 }}>
                                            <Gavel /> Final Decision Rationale
                                        </Typography>
                                        <Paper sx={{ p: 3, bgcolor: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 2 }}>
                                            <Typography variant="body1">{caseData.decision_rationale}</Typography>
                                            <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
                                                Archived on {new Date(caseData.closed_at).toLocaleString()}
                                            </Typography>
                                        </Paper>
                                    </Box>
                                )}
                            </Paper>
                        )}

                        {activeTab === 1 && (
                            <Paper sx={{ p: 4, borderRadius: 3 }}>
                                <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>Audit Timeline</Typography>
                                <List sx={{ mb: 4 }}>
                                    {caseData.notes?.map((n) => (
                                        <ListItem key={n.id} sx={{ mb: 3, alignItems: 'flex-start', px: 0 }}>
                                            <Avatar sx={{ mr: 2, width: 32, height: 32, fontSize: '0.8rem' }}>{n.author_name?.charAt(0) || 'A'}</Avatar>
                                            <ListItemText
                                                primary={
                                                    <Stack direction="row" spacing={1} alignItems="center">
                                                        <Typography variant="subtitle2" fontWeight="700">{n.author_name || "Analyst"}</Typography>
                                                        <Typography variant="caption" color="textSecondary">{new Date(n.created_at).toLocaleString()}</Typography>
                                                    </Stack>
                                                }
                                                secondary={
                                                    <Typography variant="body2" sx={{ mt: 0.5, color: '#333' }}>{n.content}</Typography>
                                                }
                                            />
                                        </ListItem>
                                    ))}
                                </List>
                                {!isClosed && (
                                    <Box sx={{ mt: 4 }}>
                                        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 700 }}>Add Note</Typography>
                                        <TextField
                                            fullWidth
                                            multiline
                                            rows={4}
                                            placeholder="Type your internal investigation note here..."
                                            value={note}
                                            onChange={(e) => setNote(e.target.value)}
                                            sx={{ mb: 2 }}
                                        />
                                        <Button variant="contained" onClick={handleAddNote} disabled={!note.trim()}>Add Note</Button>
                                    </Box>
                                )}
                            </Paper>
                        )}

                        {activeTab === 2 && (
                            <Paper sx={{ p: 4, borderRadius: 3 }}>
                                <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>Supporting Evidence</Typography>
                                <Stack spacing={2}>
                                    {caseData.evidence?.map((ev) => (
                                        <Card key={ev.id} variant="outlined" sx={{ borderRadius: 2 }}>
                                            <CardContent sx={{ display: 'flex', alignItems: 'center', py: '16px !important' }}>
                                                <IconButton color="primary" sx={{ bgcolor: '#f0f7ff', mr: 2 }}>
                                                    <Description />
                                                </IconButton>
                                                <Box sx={{ flexGrow: 1 }}>
                                                    <Typography variant="subtitle2" fontWeight="700">
                                                        {ev.evidence_type.toUpperCase()}: {ev.evidence_id.substring(0, 8)}
                                                    </Typography>
                                                    <Typography variant="caption" color="textSecondary">
                                                        Linked on {new Date(ev.created_at).toLocaleDateString()}
                                                    </Typography>
                                                </Box>
                                                <Button startIcon={<FileDownload />} size="small">Download PDF</Button>
                                            </CardContent>
                                        </Card>
                                    ))}
                                    {(!caseData.evidence || caseData.evidence.length === 0) && (
                                        <Typography color="textSecondary">No attachments linked.</Typography>
                                    )}
                                </Stack>
                            </Paper>
                        )}
                    </Grid>

                    {/* Sidebar / Quick Actions */}
                    <Grid item xs={12} md={4}>
                        <Paper sx={{ p: 3, mb: 3, borderRadius: 3 }}>
                            <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>Quick Actions</Typography>
                            <Stack spacing={2}>
                                {!isClosed && (
                                    <>
                                        <Button
                                            variant="contained"
                                            color="success"
                                            fullWidth
                                            onClick={() => setCloseDialogOpen(true)}
                                            sx={{ py: 1.5, fontWeight: 700 }}
                                        >
                                            Update Case Status
                                        </Button>
                                        <Button
                                            variant="outlined"
                                            color="error"
                                            fullWidth
                                            startIcon={<Warning />}
                                            onClick={handleEscalate}
                                            disabled={caseData.status === 'escalated'}
                                        >
                                            Escalate to Legal
                                        </Button>
                                        <Button variant="outlined" fullWidth startIcon={<AttachFile />}>Add Evidence</Button>
                                    </>
                                )}
                                <Button variant="outlined" fullWidth startIcon={<Description />}>Generate Report</Button>
                            </Stack>
                        </Paper>

                        <Paper sx={{ p: 3, borderRadius: 3 }}>
                            <Typography variant="overline" color="textSecondary" sx={{ fontWeight: 800 }}>Audit Region</Typography>
                            <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1 }}>
                                <Public fontSize="small" color="action" />
                                <Typography variant="body2" fontWeight="600">Global / Singapore Hub</Typography>
                            </Stack>
                        </Paper>
                    </Grid>
                </Grid>
            </Box>

            {/* Close Case Modal */}
            <Dialog open={closeDialogOpen} onClose={() => setCloseDialogOpen(false)} fullWidth maxWidth="sm">
                <DialogTitle sx={{ fontWeight: 800 }}>Record Final Decision</DialogTitle>
                <DialogContent>
                    <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
                        Please provide the mandatory decision rationale to archive this case. This will be preserved for regulatory audits.
                    </Typography>
                    <TextField
                        fullWidth
                        multiline
                        rows={5}
                        label="Closure Rationale"
                        value={rationale}
                        onChange={(e) => setRationale(e.target.value)}
                        required
                        placeholder="Detail the investigative outcomes and final determination..."
                    />
                </DialogContent>
                <DialogActions sx={{ p: 3, pt: 0 }}>
                    <Button onClick={() => setCloseDialogOpen(false)}>Cancel</Button>
                    <Button variant="contained" color="success" onClick={handleCloseCase} disabled={!rationale.trim() || isClosing}>
                        {isClosing ? <CircularProgress size={24} /> : "Finalize & Close Case"}
                    </Button>
                </DialogActions>
            </Dialog>
        </AdminLayout>
    );
};

export default CaseDetailPage;

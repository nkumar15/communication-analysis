
import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AdminLayout from "../../../b2b/web/layouts/AdminLayout";
import b2bDomainClient from "../../../../core/api/b2bDomainClient";
import b2bClient from "../../../../core/api/b2bClient";
import {
    Box, Typography, Paper, Chip, Button, IconButton, TextField, MenuItem,
    Stack, CircularProgress, Divider, Breadcrumbs, Link, Container
} from "@mui/material";
import {
    Warning, Speed, DoneAll, ArrowBack, Person, History,
    Language, Event, Tag, Info
} from "@mui/icons-material";

const AlertDetailPage = () => {
    const { alertId } = useParams();
    const navigate = useNavigate();
    const [alert, setAlert] = useState(null);
    const [loading, setLoading] = useState(true);
    const [users, setUsers] = useState([]);
    const [aiReport, setAiReport] = useState(null);
    const [investigatingAI, setInvestigatingAI] = useState(false);

    useEffect(() => {
        const loadData = async () => {
            setLoading(true);
            try {
                const [fullAlert, usersData] = await Promise.all([
                    b2bDomainClient.getAlert(alertId),
                    b2bClient.listUsers()
                ]);
                setAlert(fullAlert);
                setUsers(usersData);

                if (fullAlert.metadata?.ai_analysis) {
                    setAiReport(fullAlert.metadata.ai_analysis);
                }
            } catch (err) {
                console.error("Failed to load alert details:", err);
            } finally {
                setLoading(false);
            }
        };
        loadData();
    }, [alertId]);

    const handleStatusUpdate = async (newStatus) => {
        try {
            if (newStatus === 'escalated') {
                await b2bDomainClient.escalateAlert(alertId);
            } else if (newStatus === 'closed') {
                await b2bDomainClient.closeAlert(alertId);
            } else {
                await b2bDomainClient.updateAlert(alertId, { status: newStatus });
            }
            navigate('/b2b/surveillance/alerts');
        } catch (error) {
            console.error("Update failed:", error);
        }
    };

    const handleAssign = async (userId) => {
        try {
            await b2bDomainClient.updateAlert(alertId, { assigned_to: userId });
            setAlert({ ...alert, assigned_to: userId });
        } catch (error) {
            console.error("Assignment failed:", error);
        }
    };

    const handleGenerateBriefing = async () => {
        setInvestigatingAI(true);
        try {
            const report = await b2bDomainClient.investigateAlert(alertId);
            setAiReport(report);
        } catch (error) {
            console.error("AI Investigation failed:", error);
        } finally {
            setInvestigatingAI(false);
        }
    };

    const getSeverityColor = (severity) => {
        switch (severity) {
            case "critical": return "error";
            case "high": return "warning";
            case "medium": return "info";
            default: return "default";
        }
    };

    const highlightText = (text, keywords) => {
        if (!keywords || keywords.length === 0 || !text) return text;
        const kwStrings = keywords.map(kw =>
            typeof kw === 'object' ? (kw.keyword || kw.text || JSON.stringify(kw)) : kw
        ).filter(kw => typeof kw === 'string' && kw.length > 0);

        if (kwStrings.length === 0) return text;
        const escapedKeywords = kwStrings.map(kw => kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
        const regex = new RegExp(`(${escapedKeywords.join('|')})`, 'gi');
        const parts = text.split(regex);

        return parts.map((part, i) =>
            kwStrings.some(kw => part.toLowerCase() === kw.toLowerCase()) ? (
                <Box key={i} component="span" sx={{
                    bgcolor: '#fff176', px: 0.5, mx: 0.1, borderRadius: 0.5, fontWeight: 800,
                    color: '#000', borderBottom: '2px solid #fbc02d'
                }}>
                    {part}
                </Box>
            ) : part
        );
    };

    if (loading) {
        return (
            <AdminLayout>
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
                    <CircularProgress size={60} thickness={4} />
                </Box>
            </AdminLayout>
        );
    }

    if (!alert) {
        return (
            <AdminLayout>
                <Box sx={{ p: 4, textAlign: 'center' }}>
                    <Typography variant="h5" color="error">Alert not found</Typography>
                    <Button startIcon={<ArrowBack />} onClick={() => navigate('/b2b/surveillance/alerts')} sx={{ mt: 2 }}>
                        Back to Queue
                    </Button>
                </Box>
            </AdminLayout>
        );
    }

    return (
        <AdminLayout>
            <Box sx={{ bgcolor: '#f4f7f9', minHeight: '100vh', pb: 10 }}>
                {/* Fixed Top Header */}
                <Paper square sx={{
                    position: 'sticky', top: 64, zIndex: 10,
                    borderBottom: '1px solid #e0e6ed', px: 4, py: 2,
                    boxShadow: '0 2px 4px rgba(0,0,0,0.02)'
                }}>
                    <Stack direction="row" spacing={3} alignItems="center">
                        <IconButton
                            onClick={() => navigate('/b2b/surveillance/alerts')}
                            sx={{ bgcolor: '#f1f5f9', '&:hover': { bgcolor: '#e2e8f0' } }}
                        >
                            <ArrowBack />
                        </IconButton>

                        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ flexGrow: 1 }}>
                            <Stack spacing={0.5}>
                                <Breadcrumbs sx={{ mb: 0.5 }}>
                                    <Link underline="hover" color="inherit" onClick={() => navigate('/b2b/surveillance/alerts')} sx={{ cursor: 'pointer', fontSize: '0.75rem' }}>
                                        ALERTS QUEUE
                                    </Link>
                                    <Typography color="text.primary" sx={{ fontSize: '0.75rem', fontWeight: 700 }}>
                                        INVESTIGATION: {alert.id.substring(0, 8)}
                                    </Typography>
                                </Breadcrumbs>
                                <Typography variant="h5" sx={{ fontWeight: 900, color: '#1a202c' }}>
                                    {alert.subject || "Flagged Communication"}
                                </Typography>
                            </Stack>

                            <Stack direction="row" spacing={2}>
                                <Button
                                    variant="outlined"
                                    color="error"
                                    startIcon={<Warning />}
                                    onClick={() => handleStatusUpdate('escalated')}
                                    disabled={['escalated', 'closed'].includes(alert.status)}
                                    sx={{ borderRadius: 2, fontWeight: 700, px: 3, border: '2px solid' }}
                                >
                                    Escalate
                                </Button>
                                <Button
                                    variant="contained"
                                    color="success"
                                    startIcon={<DoneAll />}
                                    onClick={() => handleStatusUpdate('closed')}
                                    disabled={alert.status === 'closed'}
                                    sx={{ borderRadius: 2, fontWeight: 700, px: 3, boxShadow: 'none' }}
                                >
                                    Close Alert
                                </Button>
                            </Stack>
                        </Stack>
                    </Stack>
                </Paper>

                <Container maxWidth="xl" sx={{ mt: 4 }}>
                    <Stack direction="row" spacing={4} alignItems="flex-start">

                        {/* LEFT COLUMN: Deep Investigation */}
                        <Box sx={{ flex: 3 }}>

                            {/* AI Insights Card */}
                            <Paper sx={{ mb: 4, borderRadius: 3, overflow: 'hidden', border: '1px solid #e0e6ed' }}>
                                <Box sx={{ p: 2, bgcolor: '#f8fafc', borderBottom: '1px solid #e0e6ed', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Stack direction="row" alignItems="center" spacing={1}>
                                        <Speed color="primary" />
                                        <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>Multi-Agent AI Briefing</Typography>
                                    </Stack>
                                    {!aiReport && !investigatingAI && (
                                        <Button
                                            size="small" variant="contained" color="primary"
                                            onClick={handleGenerateBriefing}
                                            sx={{ borderRadius: 2, fontWeight: 700 }}
                                        >
                                            🚀 Run Analysis
                                        </Button>
                                    )}
                                </Box>
                                <Box sx={{ p: 3 }}>
                                    {investigatingAI ? (
                                        <Box sx={{ textAlign: 'center', py: 4 }}>
                                            <CircularProgress size={40} sx={{ mb: 2 }} />
                                            <Typography variant="body2" color="textSecondary">
                                                Orchestrating specialized agents (Intent, Policy, Evasion)...
                                            </Typography>
                                        </Box>
                                    ) : aiReport ? (
                                        <Stack spacing={3}>
                                            <Paper elevation={0} sx={{ p: 2.5, bgcolor: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 2 }}>
                                                <Stack direction="row" spacing={3} alignItems="flex-start">
                                                    <Box sx={{
                                                        px: 2, py: 1, borderRadius: 1.5, fontWeight: 900,
                                                        bgcolor: aiReport.risk_level === 'high' ? '#ef4444' : aiReport.risk_level === 'medium' ? '#f59e0b' : '#10b981',
                                                        color: '#fff', textAlign: 'center', minWidth: 100
                                                    }}>
                                                        <Typography variant="h6" sx={{ lineHeight: 1, fontWeight: 900 }}>{aiReport.risk_level.toUpperCase()}</Typography>
                                                        <Typography variant="caption" sx={{ fontWeight: 700 }}>RISK LEVEL</Typography>
                                                    </Box>
                                                    <Box>
                                                        <Typography variant="body1" sx={{ fontWeight: 700, color: '#0c4a6e', mb: 1 }}>{aiReport.summary}</Typography>
                                                        <Divider sx={{ mb: 1, borderColor: '#bae6fd' }} />
                                                        <Typography variant="caption" sx={{ color: '#0369a1', fontWeight: 600 }}>
                                                            Generated at {new Date(aiReport.timestamp).toLocaleString()}
                                                        </Typography>
                                                    </Box>
                                                </Stack>
                                            </Paper>

                                            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 3 }}>
                                                {/* Agent Detail Cards */}
                                                {[
                                                    {
                                                        icon: "🧠", title: "INTENT",
                                                        value: aiReport.intent_verdict?.classification,
                                                        desc: aiReport.intent_verdict?.reasoning,
                                                        color: '#4f46e5'
                                                    },
                                                    {
                                                        icon: "📜", title: "POLICY",
                                                        value: aiReport.policy_verdict?.violation_citation || "Compliant",
                                                        desc: aiReport.policy_verdict?.reasoning,
                                                        color: aiReport.policy_verdict?.is_compliant ? '#16a34a' : '#dc2626'
                                                    },
                                                    {
                                                        icon: "🕵️", title: "EVASION",
                                                        value: aiReport.evasion_verdict?.evasion_type || "None",
                                                        desc: aiReport.evasion_verdict?.evidence,
                                                        color: aiReport.evasion_verdict?.is_evasion ? '#dc2626' : '#16a34a'
                                                    }
                                                ].map((agent, i) => (
                                                    <Paper key={i} variant="outlined" sx={{ p: 2, borderRadius: 2, border: `1px solid ${agent.color}20`, bgcolor: `${agent.color}05` }}>
                                                        <Typography variant="caption" sx={{ fontWeight: 900, color: agent.color, display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                                                            {agent.icon} {agent.title}
                                                        </Typography>
                                                        <Typography variant="body2" sx={{ fontWeight: 800, mb: 1, color: '#1f2937' }}>{agent.value}</Typography>
                                                        <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', lineHeight: 1.4 }}>
                                                            {agent.desc}
                                                        </Typography>
                                                    </Paper>
                                                ))}
                                            </Box>
                                        </Stack>
                                    ) : (
                                        <Box sx={{ textAlign: 'center', py: 2 }}>
                                            <Typography variant="body2" color="textSecondary">
                                                No AI investigation has been performed for this alert yet.
                                            </Typography>
                                        </Box>
                                    )}
                                </Box>
                            </Paper>

                            {/* Thread Section */}
                            <Typography variant="h6" sx={{ mb: 2, fontWeight: 800, color: '#334155' }}>Conversation Context</Typography>
                            <Box sx={{ borderLeft: '3px solid #e2e8f0', ml: 1, pl: 4 }}>
                                {(alert.conversation_thread || []).map((msg, idx) => (
                                    <Box key={idx} sx={{ mb: 5, position: 'relative' }}>
                                        {/* Thread connector dot */}
                                        <Box sx={{
                                            position: 'absolute', left: -43, top: 12, width: 18, height: 18,
                                            borderRadius: '50%', bgcolor: msg.is_trigger ? '#ef4444' : '#cbd5e1',
                                            border: '4px solid white', zIndex: 1, boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                                        }} />

                                        {msg.is_trigger && (
                                            <Stack direction="row" spacing={1} sx={{ mb: 1.5, p: 1, bgcolor: '#fef2f2', border: '1px solid #fecaca', borderRadius: 2, width: 'fit-content' }}>
                                                <Warning sx={{ fontSize: 18, color: '#ef4444' }} />
                                                <Typography variant="caption" sx={{ fontWeight: 900, color: '#991b1b', textTransform: 'uppercase' }}>
                                                    TRigger Match: {msg.risk_indicators.join(", ")}
                                                </Typography>
                                            </Stack>
                                        )}

                                        <Paper elevation={0} sx={{
                                            p: 3, borderRadius: 3,
                                            bgcolor: msg.is_trigger ? '#fff' : '#f8fafc',
                                            border: msg.is_trigger ? '2px solid #ef4444' : '1px solid #e2e8f0',
                                            boxShadow: msg.is_trigger ? '0 10px 25px -5px rgba(239, 68, 68, 0.1)' : 'none'
                                        }}>
                                            <Stack direction="row" justifyContent="space-between" sx={{ mb: 2 }}>
                                                <Typography variant="subtitle1" sx={{ fontWeight: 800, color: '#1e293b' }}>{msg.sender}</Typography>
                                                <Typography variant="caption" sx={{ fontWeight: 600, color: '#64748b' }}>
                                                    {new Date(msg.timestamp).toLocaleString([], { dateStyle: 'full', timeStyle: 'short' })}
                                                </Typography>
                                            </Stack>
                                            <Typography variant="body1" sx={{
                                                whiteSpace: 'pre-wrap', color: '#334155', lineHeight: 1.7,
                                                fontSize: '1.05rem', fontStyle: msg.is_trigger ? 'normal' : 'italic'
                                            }}>
                                                {highlightText(msg.content, msg.matched_keywords)}
                                            </Typography>
                                        </Paper>
                                    </Box>
                                ))}
                            </Box>
                        </Box>

                        {/* RIGHT SIDEBAR: Meta & Intelligence */}
                        <Box sx={{ flex: 1, position: 'sticky', top: 150 }}>
                            <Stack spacing={3}>

                                {/* Status & Assignment */}
                                <Paper sx={{ p: 3, borderRadius: 3, border: '1px solid #e0e6ed' }}>
                                    <Typography variant="caption" sx={{ fontWeight: 900, color: 'text.secondary', display: 'block', mb: 2 }}>CASE CONTROLS</Typography>

                                    <Stack spacing={2.5}>
                                        <Box>
                                            <Typography variant="caption" color="textSecondary" sx={{ fontWeight: 700, mb: 0.5, display: 'block' }}>ASSIGNED ANALYST</Typography>
                                            <TextField
                                                select fullWidth size="small"
                                                value={alert.assigned_to || ""}
                                                onChange={(e) => handleAssign(e.target.value)}
                                                sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
                                            >
                                                <MenuItem value=""><em>Unassigned</em></MenuItem>
                                                {users.map(u => <MenuItem key={u.id} value={u.id}>{u.name || u.email}</MenuItem>)}
                                            </TextField>
                                        </Box>
                                        <Box>
                                            <Typography variant="caption" color="textSecondary" sx={{ fontWeight: 700, mb: 0.5, display: 'block' }}>INVESTIGATION STATUS</Typography>
                                            <Chip
                                                label={alert.status.toUpperCase()}
                                                color={alert.status === 'open' ? "error" : alert.status === 'investigating' ? "warning" : "success"}
                                                sx={{ fontWeight: 900, borderRadius: 1.5, width: '100%' }}
                                            />
                                        </Box>
                                    </Stack>
                                </Paper>

                                {/* Alert Metadata */}
                                <Paper sx={{ p: 3, borderRadius: 3, border: '1px solid #e0e6ed' }}>
                                    <Typography variant="caption" sx={{ fontWeight: 900, color: 'text.secondary', display: 'block', mb: 2 }}>METADATA</Typography>
                                    <Stack spacing={2}>
                                        {[
                                            { icon: <Tag fontSize="inherit" />, label: "Risk Typology", value: alert.risk_type || "Standard" },
                                            { icon: <Language fontSize="inherit" />, label: "Region", value: alert.region || "Global" },
                                            { icon: <Event fontSize="inherit" />, label: "Detected At", value: new Date(alert.detected_at).toLocaleDateString() },
                                            { icon: <Info fontSize="inherit" />, label: "Alert ID", value: alert.id.substring(0, 8) }
                                        ].map((item, idx) => (
                                            <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                                                <Box sx={{ bgcolor: '#eff6ff', p: 0.7, borderRadius: 1, color: '#3b82f6', display: 'flex' }}>
                                                    {item.icon}
                                                </Box>
                                                <Box>
                                                    <Typography variant="caption" color="textSecondary" sx={{ fontWeight: 700, display: 'block', lineHeight: 1 }}>{item.label}</Typography>
                                                    <Typography variant="body2" sx={{ fontWeight: 800 }}>{item.value}</Typography>
                                                </Box>
                                            </Box>
                                        ))}
                                    </Stack>
                                </Paper>

                                {/* Keywords/Indicators */}
                                <Paper sx={{ p: 3, borderRadius: 3, border: '1px solid #e0e6ed' }}>
                                    <Typography variant="caption" sx={{ fontWeight: 900, color: 'text.secondary', display: 'block', mb: 2 }}>MATCH EVIDENCE</Typography>
                                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                                        {(alert.metadata?.matched_keywords || ["MTM", "Markup", "Off-channel"]).map((kw, i) => (
                                            <Chip key={i} label={kw} size="small" sx={{ fontWeight: 700, bgcolor: '#f1f5f9', color: '#475569' }} />
                                        ))}
                                    </Box>
                                </Paper>
                            </Stack>
                        </Box>

                    </Stack>
                </Container>
            </Box>
        </AdminLayout>
    );
};

export default AlertDetailPage;

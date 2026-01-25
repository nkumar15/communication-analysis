
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
    Language, Event, Tag, Info, ExpandMore
} from "@mui/icons-material";
import { Accordion, AccordionSummary, AccordionDetails } from "@mui/material";

const AlertDetailPage = () => {
    const { alertId } = useParams();
    const navigate = useNavigate();
    const [alert, setAlert] = useState(null);
    const [loading, setLoading] = useState(true);
    const [users, setUsers] = useState([]);
    const [aiReport, setAiReport] = useState(null);
    const [investigatingAI, setInvestigatingAI] = useState(false);
    const [expandedMessages, setExpandedMessages] = useState({});

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
                if (fullAlert.conversation_thread) {
                    const expanded = {};
                    fullAlert.conversation_thread.forEach((msg, idx) => {
                        if (msg.is_trigger) expanded[idx] = true;
                    });
                    setExpandedMessages(expanded);
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

    const handleToggleMessage = (idx) => {
        setExpandedMessages(prev => ({
            ...prev,
            [idx]: !prev[idx]
        }));
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
                                        INVESTIGATION: {alert.display_id || alert.id.substring(0, 8)}
                                    </Typography>
                                </Breadcrumbs>
                                <Typography variant="h5" sx={{ fontWeight: 900, color: '#1a202c', display: 'flex', alignItems: 'center', gap: 2 }}>
                                    {alert.subject || "Flagged Communication"}
                                    {alert.metadata?.ai_analysis?.risk_level && (
                                        <Chip
                                            label={`${alert.metadata.ai_analysis.risk_level.toUpperCase()} RISK`}
                                            size="small"
                                            sx={{
                                                fontWeight: 900, bgcolor: alert.metadata.ai_analysis.risk_level === 'high' ? '#fee2e2' : '#fef3c7',
                                                color: alert.metadata.ai_analysis.risk_level === 'high' ? '#dc2626' : '#d97706',
                                                border: '1px solid', borderColor: 'currentColor'
                                            }}
                                        />
                                    )}
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

                <Container maxWidth="xl" sx={{ mt: 14 }}>
                    <Stack direction="row" spacing={4} alignItems="flex-start">

                        {/* LEFT COLUMN: Metadata & Intelligence (Narrower) */}
                        <Box sx={{ flex: 1, position: 'sticky', top: 160 }}>
                            <Stack spacing={3}>
                                {/* Key Details Card */}
                                <Paper sx={{ p: 3, borderRadius: 3, border: '1px solid #e0e6ed' }}>
                                    <Typography variant="caption" sx={{ fontWeight: 900, color: 'text.secondary', display: 'block', mb: 2 }}>KEY DETAILS</Typography>
                                    <Stack spacing={2}>
                                        {[
                                            { icon: <Info fontSize="inherit" />, label: "Alert ID", value: alert.display_id || alert.id.substring(0, 8) },
                                            { icon: <Person fontSize="inherit" />, label: "Sender", value: alert.communication?.sender || "System" },
                                            { icon: <Language fontSize="inherit" />, label: "Region", value: alert.region || "Global" },
                                            { icon: <Tag fontSize="inherit" />, label: "Risk Typology", value: alert.risk_type || "Standard" },
                                            { icon: <Event fontSize="inherit" />, label: "Detected At", value: new Date(alert.detected_at).toLocaleDateString() }
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

                                {/* AI Briefing Card */}
                                <Paper sx={{ borderRadius: 3, overflow: 'hidden', border: '1px solid #e0e6ed' }}>
                                    <Box sx={{ p: 2, bgcolor: '#f8fafc', borderBottom: '1px solid #e0e6ed', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <Stack direction="row" alignItems="center" spacing={1}>
                                            <Speed color="primary" sx={{ fontSize: 20 }} />
                                            <Typography variant="caption" sx={{ fontWeight: 900, color: 'text.secondary' }}>AI BRIEFING</Typography>
                                        </Stack>
                                        {!aiReport && !investigatingAI && (
                                            <Button
                                                size="small" variant="contained" color="primary"
                                                onClick={handleGenerateBriefing}
                                                sx={{ borderRadius: 1.5, fontWeight: 700, px: 1.5, fontSize: '0.65rem' }}
                                            >
                                                🚀 Screening
                                            </Button>
                                        )}
                                    </Box>
                                    <Box sx={{ p: 2 }}>
                                        {investigatingAI ? (
                                            <Box sx={{ textAlign: 'center', py: 2 }}>
                                                <CircularProgress size={24} sx={{ mb: 1 }} />
                                                <Typography variant="caption" color="textSecondary" sx={{ display: 'block' }}>
                                                    Analyzing...
                                                </Typography>
                                            </Box>
                                        ) : aiReport ? (
                                            <Stack spacing={2}>
                                                <Box sx={{
                                                    p: 1.5, bgcolor: aiReport.risk_level === 'high' ? '#fef2f2' : '#f0f9ff',
                                                    border: '1px solid', borderColor: aiReport.risk_level === 'high' ? '#fee2e2' : '#bae6fd',
                                                    borderRadius: 2
                                                }}>
                                                    <Typography variant="h6" sx={{
                                                        fontWeight: 900, mb: 0.5,
                                                        color: aiReport.risk_level === 'high' ? '#dc2626' : '#0284c7'
                                                    }}>
                                                        {aiReport.risk_level.toUpperCase()} RISK
                                                    </Typography>
                                                    <Typography variant="body2" sx={{ color: 'text.primary', fontWeight: 500, lineHeight: 1.4, fontSize: '0.8rem' }}>
                                                        {aiReport.summary}
                                                    </Typography>
                                                </Box>
                                                <Stack spacing={1}>
                                                    {[
                                                        { title: "INTENT", value: aiReport.intent_verdict?.classification, color: '#4f46e5' },
                                                        { title: "POLICY", value: aiReport.policy_verdict?.violation_citation || "Compliant", color: aiReport.policy_verdict?.is_compliant ? '#16a34a' : '#dc2626' },
                                                        { title: "EVASION", value: aiReport.evasion_verdict?.evasion_type || "None", color: aiReport.evasion_verdict?.is_evasion ? '#dc2626' : '#16a34a' }
                                                    ].map((agent, i) => (
                                                        <Box key={i} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                            <Typography variant="caption" sx={{ fontWeight: 800, color: 'text.secondary' }}>{agent.title}</Typography>
                                                            <Typography variant="caption" sx={{ fontWeight: 900, color: agent.color }}>{agent.value}</Typography>
                                                        </Box>
                                                    ))}
                                                </Stack>
                                            </Stack>
                                        ) : (
                                            <Box sx={{ textAlign: 'center', py: 2 }}>
                                                <Typography variant="caption" color="textSecondary">
                                                    Action Required: Run AI Screening
                                                </Typography>
                                            </Box>
                                        )}
                                    </Box>
                                </Paper>

                                {/* Other Controls Case Controls */}
                                <Paper sx={{ p: 3, borderRadius: 3, border: '1px solid #e0e6ed' }}>
                                    <Stack spacing={2.5}>
                                        <Box>
                                            <Typography variant="caption" color="textSecondary" sx={{ fontWeight: 700, mb: 1, display: 'block' }}>ASSIGNED ANALYST</Typography>
                                            <Paper elevation={0} sx={{
                                                p: 1.5, bgcolor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 2,
                                                display: 'flex', alignItems: 'center', gap: 1.5
                                            }}>
                                                <Person sx={{ color: '#64748b', fontSize: 20 }} />
                                                <Typography variant="body2" sx={{ fontWeight: 800, color: '#1e293b' }}>
                                                    {alert.assignee_name || "Unassigned"}
                                                </Typography>
                                            </Paper>
                                        </Box>
                                        <Box>
                                            <Typography variant="caption" color="textSecondary" sx={{ fontWeight: 700, mb: 1, display: 'block' }}>INVESTIGATION STATUS</Typography>
                                            <Chip
                                                label={alert.status.toUpperCase()}
                                                color={alert.status === 'open' ? "error" : alert.status === 'investigating' ? "warning" : "success"}
                                                sx={{ fontWeight: 900, borderRadius: 1.5, width: '100%' }}
                                            />
                                        </Box>
                                        <Box>
                                            <Typography variant="caption" sx={{ fontWeight: 900, color: 'text.secondary', display: 'block', mb: 1.5 }}>MATCH EVIDENCE</Typography>
                                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                                                {(alert.metadata?.matched_keywords || ["MTM", "Markup", "Off-channel"]).map((kw, i) => (
                                                    <Chip key={i} label={kw} size="small" sx={{ fontWeight: 700, bgcolor: '#f1f5f9', color: '#475569' }} />
                                                ))}
                                            </Box>
                                        </Box>
                                    </Stack>
                                </Paper>
                            </Stack>
                        </Box>

                        {/* RIGHT COLUMN: Conversation Thread (Wider) */}
                        <Box sx={{ flex: 3, pt: 0 }}>
                            <Box sx={{ borderLeft: '3px solid #e2e8f0', ml: 1, pl: 4 }}>
                                {(alert.conversation_thread || []).map((msg, idx) => (
                                    <Box key={idx} sx={{ mb: 2, position: 'relative' }}>
                                        {/* Thread connector dot */}
                                        <Box sx={{
                                            position: 'absolute', left: -43, top: 20, width: 14, height: 14,
                                            borderRadius: '50%', bgcolor: msg.is_trigger ? '#ef4444' : '#cbd5e1',
                                            border: '3px solid white', zIndex: 1, boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                                        }} />

                                        <Accordion
                                            expanded={!!expandedMessages[idx]}
                                            onChange={() => handleToggleMessage(idx)}
                                            elevation={0}
                                            sx={{
                                                borderRadius: '12px !important',
                                                border: msg.is_trigger ? '2px solid #ef4444' : '1px solid #e2e8f0',
                                                bgcolor: msg.is_trigger ? '#fff' : '#f8fafc',
                                                '&:before': { display: 'none' },
                                                overflow: 'hidden'
                                            }}
                                        >
                                            <AccordionSummary expandIcon={<ExpandMore />}>
                                                <Stack direction="row" justifyContent="space-between" sx={{ width: '100%', pr: 2 }}>
                                                    <Stack direction="row" spacing={1.5} alignItems="center">
                                                        <Typography variant="subtitle2" sx={{ fontWeight: 800, color: '#1e293b' }}>{msg.sender}</Typography>
                                                        {msg.is_trigger && (
                                                            <Chip label="TRIGGER" size="small" color="error" sx={{ height: 20, fontSize: '0.6rem', fontWeight: 900 }} />
                                                        )}
                                                    </Stack>
                                                    <Typography variant="caption" sx={{ fontWeight: 600, color: '#64748b' }}>
                                                        {new Date(msg.timestamp).toLocaleString([], { hour: '2-digit', minute: '2-digit' })}
                                                    </Typography>
                                                </Stack>
                                            </AccordionSummary>
                                            <AccordionDetails sx={{ pt: 0, pb: 3, px: 3 }}>
                                                {msg.is_trigger && (
                                                    <Stack direction="row" spacing={1} sx={{ mb: 2, p: 1, bgcolor: '#fef2f2', border: '1px solid #fecaca', borderRadius: 1.5, width: 'fit-content' }}>
                                                        <Warning sx={{ fontSize: 16, color: '#ef4444' }} />
                                                        <Typography variant="caption" sx={{ fontWeight: 800, color: '#991b1b', textTransform: 'uppercase' }}>
                                                            {msg.risk_indicators.join(", ")}
                                                        </Typography>
                                                    </Stack>
                                                )}
                                                <Typography variant="body1" sx={{
                                                    whiteSpace: 'pre-wrap', color: '#334155', lineHeight: 1.6,
                                                    fontSize: '0.95rem', fontStyle: msg.is_trigger ? 'normal' : 'italic'
                                                }}>
                                                    {highlightText(msg.content, msg.matched_keywords)}
                                                </Typography>
                                            </AccordionDetails>
                                        </Accordion>
                                    </Box>
                                ))}
                            </Box>
                        </Box>
                    </Stack>
                </Container>
            </Box>
        </AdminLayout>
    );
};

export default AlertDetailPage;

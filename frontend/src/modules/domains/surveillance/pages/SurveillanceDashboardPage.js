import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, Card, CardContent, CardActions, Button, Grid, Chip, Container } from '@mui/material';
import { Assessment, Search, MenuBook, BarChart, ArrowForward, AccountTree, NotificationsActive, Forum } from '@mui/icons-material';
import AdminLayout from '../../../b2b/web/layouts/AdminLayout';

const SurveillanceDashboardPage = () => {
    const navigate = useNavigate();

    const features = [
        {
            icon: <NotificationsActive sx={{ fontSize: 48, color: 'error.main' }} />,
            title: 'Risk Alerts',
            description: 'Monitor and process AI-detected risk events, policy violations, and suspicious patterns across all channels.',
            status: 'active',
            path: '/b2b/surveillance/alerts',
            buttonText: 'Review Alerts',
            color: 'error'
        },
        {
            icon: <Forum sx={{ fontSize: 48, color: 'primary.main' }} />,
            title: 'Communications Archive',
            description: 'Browse and search through all archived communications with full tenant isolation and audit logging.',
            status: 'active',
            path: '/b2b/surveillance/communications',
            buttonText: 'Browse Archive',
            color: 'primary'
        },
        {
            icon: <Assessment sx={{ fontSize: 48, color: 'warning.main' }} />,
            title: 'Case Management',
            description: 'Enterprise-grade case lifecycle management. Track escalations, link evidence, and record final compliance decisions.',
            status: 'active',
            path: '/b2b/surveillance/cases',
            buttonText: 'Manage Cases',
            color: 'warning'
        },
        {
            icon: <MenuBook sx={{ fontSize: 48, color: 'secondary.main' }} />,
            title: 'Institutional Knowledge (RAG)',
            description: 'Semantic search over structured and unstructured data to identify historical patterns and regulatory context.',
            status: 'active',
            path: '/b2b/surveillance/knowledge-base',
            buttonText: 'Knowledge Base',
            color: 'secondary'
        },
        {
            icon: <AccountTree sx={{ fontSize: 48, color: 'success.main' }} />,
            title: 'Network Graph Analysis',
            description: 'Visualize communication patterns between employees and external parties to detect hidden cliques and collusion.',
            status: 'coming-soon',
            path: null,
            buttonText: 'Social Graph',
            color: 'success'
        },
        {
            icon: <BarChart sx={{ fontSize: 48, color: 'info.main' }} />,
            title: 'Analytics & Reporting',
            description: 'Comprehensive risk posture reports, compliance trends, and regional activity heatmaps.',
            status: 'coming-soon',
            path: null,
            buttonText: 'View Reports',
            color: 'info'
        }
    ];

    return (
        <AdminLayout title="Worldwide Bank Surveillance Workbench" subtitle="Strategic Intelligence & Multi-Channel Compliance Monitoring">
            <Box sx={{ p: 4 }}>
                <Container maxWidth="lg">
                    {/* Feature Cards Grid */}
                    <Box
                        sx={{
                            display: 'grid',
                            gridTemplateColumns: {
                                xs: '1fr',
                                md: 'repeat(2, 1fr)',
                                lg: 'repeat(3, 1fr)'
                            },
                            gap: 3,
                            mb: 4
                        }}
                    >
                        {features.map((feature, index) => (
                            <Card
                                key={index}
                                sx={{
                                    height: '100%',
                                    minHeight: 220,
                                    display: 'flex',
                                    flexDirection: 'column',
                                    transition: 'transform 0.2s, box-shadow 0.2s',
                                    '&:hover': feature.status === 'active' ? {
                                        transform: 'translateY(-4px)',
                                        boxShadow: 4
                                    } : {}
                                }}
                            >
                                <CardContent sx={{ flexGrow: 1 }}>
                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                                        {feature.icon}
                                        {feature.status === 'coming-soon' && (
                                            <Chip label="Coming Soon" size="small" color="default" variant="outlined" />
                                        )}
                                        {feature.status === 'active' && (
                                            <Chip label="Active" size="small" color="success" />
                                        )}
                                    </Box>

                                    <Typography variant="h6" gutterBottom fontWeight="700">
                                        {feature.title}
                                    </Typography>

                                    <Typography variant="body2" color="text.secondary">
                                        {feature.description}
                                    </Typography>
                                </CardContent>

                                <CardActions sx={{ p: 2, pt: 0 }}>
                                    <Button
                                        fullWidth
                                        variant={feature.status === 'active' ? 'contained' : 'outlined'}
                                        color={feature.color}
                                        endIcon={feature.status === 'active' ? <ArrowForward /> : null}
                                        onClick={() => feature.path && navigate(feature.path)}
                                        disabled={feature.status !== 'active'}
                                        sx={{ borderRadius: '8px', textTransform: 'none', fontWeight: 'bold' }}
                                    >
                                        {feature.buttonText}
                                    </Button>
                                </CardActions>
                            </Card>
                        ))}
                    </Box>

                    {/* Regional Context Summary (Mock) */}
                    <Box sx={{ p: 3, bgcolor: 'background.paper', borderRadius: 2, border: '1px solid #e0e0e0', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
                        <Typography variant="h6" gutterBottom color="primary.dark" fontWeight="700">
                            Regional Risk Posture
                        </Typography>
                        <Box sx={{
                            display: 'grid',
                            gridTemplateColumns: {
                                xs: '1fr',
                                sm: 'repeat(3, 1fr)'
                            },
                            gap: 4,
                            mt: 1
                        }}>
                            <Box>
                                <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                                    SINGAPORE HUB (HQ)
                                </Typography>
                                <Typography variant="h5" fontWeight="700" color="success.main">
                                    Low Risk
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Geo-fencing: Active
                                </Typography>
                            </Box>
                            <Box>
                                <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                                    EUROPE (UK/GER)
                                </Typography>
                                <Typography variant="h5" fontWeight="700" color="warning.main">
                                    Moderate
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    GDPR Compliance: Verified
                                </Typography>
                            </Box>
                            <Box>
                                <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                                    NORTH AMERICA
                                </Typography>
                                <Typography variant="h5" fontWeight="700" color="info.main">
                                    Standard
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    SEC Rules: Enforced
                                </Typography>
                            </Box>
                        </Box>
                    </Box>
                </Container>
            </Box>
        </AdminLayout>
    );
};

export default SurveillanceDashboardPage;


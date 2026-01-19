import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, Card, CardContent, CardActions, Button, Grid, Chip, Container } from '@mui/material';
import { Assessment, Search, MenuBook, BarChart, ArrowForward, AccountTree } from '@mui/icons-material';
import AdminLayout from './web/layouts/AdminLayout';

const EnronDashboard = () => {
    const navigate = useNavigate();

    const features = [
        {
            icon: <Assessment sx={{ fontSize: 48, color: 'primary.main' }} />,
            title: 'Email Investigation',
            description: 'Submit emails for comprehensive AI-powered fraud and compliance analysis using multi-agent detection.',
            status: 'active',
            path: '/b2b/c/enron/investigate',
            buttonText: 'Launch Investigation',
            color: 'primary'
        },
        {
            icon: <MenuBook sx={{ fontSize: 48, color: 'secondary.main' }} />,
            title: 'Knowledge Base (RAG)',
            description: 'Search through Enron email corpus and regulatory documents using advanced vector search.',
            status: 'active',
            path: '/b2b/c/enron/knowledge-base',
            buttonText: 'Browse Knowledge Base',
            color: 'secondary'
        },
        {
            icon: <AccountTree sx={{ fontSize: 48, color: 'success.main' }} />,
            title: 'Social Graph Analysis',
            description: 'Visualize communication networks, detect cliques, and identify key influencers in the email network.',
            status: 'active',
            path: '/b2b/c/enron/investigate',
            buttonText: 'View Network Graph',
            color: 'success'
        },
        {
            icon: <BarChart sx={{ fontSize: 48, color: 'info.main' }} />,
            title: 'Analytics & Reports',
            description: 'View investigation history, risk trends, and compliance dashboards.',
            status: 'coming-soon',
            path: null,
            buttonText: 'Coming Soon',
            color: 'info'
        }
    ];

    return (
        <AdminLayout title="Enron Surveillance System" subtitle="AI-powered email surveillance and compliance monitoring">
            <Box sx={{ p: 4 }}>
                {/* Feature Cards */}
                <Container maxWidth="lg">
                    <Box
                        sx={{
                            display: 'grid',
                            gridTemplateColumns: {
                                xs: '1fr',
                                md: 'repeat(2, 1fr)'
                            },
                            gap: 3
                        }}
                    >
                        {features.map((feature, index) => (
                            <Card
                                key={index}
                                sx={{
                                    height: '100%',
                                    minHeight: 240,
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
                                            <Chip label="Coming Soon" size="small" color="default" />
                                        )}
                                        {feature.status === 'active' && (
                                            <Chip label="Active" size="small" color="success" />
                                        )}
                                    </Box>

                                    <Typography variant="h6" gutterBottom>
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
                                    >
                                        {feature.buttonText}
                                    </Button>
                                </CardActions>
                            </Card>
                        ))}
                    </Box>

                    {/* Info Box */}
                    <Box sx={{ mt: 4, p: 3, bgcolor: 'info.lighter', borderRadius: 1 }}>
                        <Typography variant="h6" gutterBottom color="info.dark">
                            About This System
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            This POC demonstrates advanced AI techniques for detecting financial fraud in corporate communications.
                            The system uses Intent Classification, Policy Compliance, and Evasion Detection agents to provide
                            comprehensive email analysis and risk assessment.
                        </Typography>
                    </Box>
                </Container>
            </Box>
        </AdminLayout >
    );
};

export default EnronDashboard;

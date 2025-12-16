import React, { useState, useEffect } from 'react';
import {
    Card,
    CardContent,
    Typography,
    Button,
    Box,
    Grid,
    Chip,
    Alert,
    CircularProgress,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions
} from '@mui/material';
import {
    CheckCircle,
    Upgrade,
    People,
    AttachMoney
} from '@mui/icons-material';
import axios from 'axios';

const TIER_FEATURES = {
    starter: {
        name: 'Starter',
        description: 'Perfect for getting started',
        features: [
            'Up to 10 users',
            'Basic SSO integration',
            'Email support',
            'Standard features'
        ],
        color: '#2196F3'
    },
    professional: {
        name: 'Professional',
        description: 'For growing teams',
        features: [
            'Unlimited users',
            'Advanced SSO integration',
            'Priority email support',
            'Custom branding',
            'Advanced RBAC',
            'Audit logs'
        ],
        color: '#9C27B0'
    },
    enterprise: {
        name: 'Enterprise',
        description: 'For large organizations',
        features: [
            'Everything in Professional',
            '24/7 phone support',
            'Dedicated account manager',
            'Custom SLA',
            'Advanced security features',
            'On-premise deployment option'
        ],
        color: '#FF9800'
    }
};

const SubscriptionSettingsPage = () => {
    const [subscription, setSubscription] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [upgradeDialogOpen, setUpgradeDialogOpen] = useState(false);
    const [selectedTier, setSelectedTier] = useState(null);
    const [checkoutLoading, setCheckoutLoading] = useState(false);

    useEffect(() => {
        fetchSubscription();
    }, []);

    const fetchSubscription = async () => {
        try {
            setLoading(true);
            const response = await axios.get('/api/b2b/billing/subscription');
            setSubscription(response.data);
            setError(null);
        } catch (err) {
            console.error('Failed to fetch subscription:', err);
            setError('Failed to load subscription details');
        } finally {
            setLoading(false);
        }
    };

    const handleUpgradeClick = (tier) => {
        setSelectedTier(tier);
        setUpgradeDialogOpen(true);
    };

    const handleCheckout = async (billingInterval) => {
        try {
            setCheckoutLoading(true);
            const response = await axios.post('/api/b2b/billing/checkout', {
                tier: selectedTier,
                billing_interval: billingInterval
            });

            // Redirect to Stripe checkout
            window.location.href = response.data.checkout_url;
        } catch (err) {
            console.error('Checkout error:', err);
            alert('Failed to create checkout session. Please try again.');
            setCheckoutLoading(false);
        }
    };

    if (loading) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
                <CircularProgress />
            </Box>
        );
    }

    if (error) {
        return (
            <Box p={3}>
                <Alert severity="error">{error}</Alert>
            </Box>
        );
    }

    const currentTier = subscription?.tier || 'starter';
    const isStarterTier = currentTier === 'starter';

    return (
        <Box p={3}>
            <Typography variant="h4" gutterBottom>
                Subscription & Billing
            </Typography>

            {/* Current Subscription Card */}
            <Card sx={{ mb: 4 }}>
                <CardContent>
                    <Grid container spacing={3}>
                        <Grid item xs={12} md={6}>
                            <Typography variant="h6" gutterBottom>
                                Current Plan
                            </Typography>
                            <Box display="flex" alignItems="center" gap={2} mb={2}>
                                <Chip
                                    label={TIER_FEATURES[currentTier].name}
                                    color="primary"
                                    sx={{ backgroundColor: TIER_FEATURES[currentTier].color }}
                                />
                                <Chip
                                    label={subscription?.status || 'Active'}
                                    color={subscription?.status === 'active' ? 'success' : 'default'}
                                    icon={<CheckCircle />}
                                />
                            </Box>
                            <Typography variant="body2" color="text.secondary" gutterBottom>
                                {TIER_FEATURES[currentTier].description}
                            </Typography>
                        </Grid>

                        <Grid item xs={12} md={6}>
                            <Typography variant="h6" gutterBottom>
                                Pricing Details
                            </Typography>
                            <Box display="flex" gap={3}>
                                <Box>
                                    <Typography variant="body2" color="text.secondary">
                                        Seat Count
                                    </Typography>
                                    <Box display="flex" alignItems="center" gap={1}>
                                        <People fontSize="small" />
                                        <Typography variant="h6">
                                            {subscription?.seat_count || 0} users
                                        </Typography>
                                    </Box>
                                </Box>
                                <Box>
                                    <Typography variant="body2" color="text.secondary">
                                        Total Cost
                                    </Typography>
                                    <Box display="flex" alignItems="center" gap={1}>
                                        <AttachMoney fontSize="small" />
                                        <Typography variant="h6">
                                            ${((subscription?.total_amount_cents || 0) / 100).toFixed(2)}
                                            <Typography component="span" variant="body2" color="text.secondary">
                                                /{subscription?.billing_interval || 'month'}
                                            </Typography>
                                        </Typography>
                                    </Box>
                                </Box>
                            </Box>

                            {!isStarterTier && (
                                <Box mt={2}>
                                    <Typography variant="caption" color="text.secondary">
                                        Pricing: ${(subscription?.base_price_cents / 100).toFixed(2)} base +
                                        ${(subscription?.per_seat_price_cents / 100).toFixed(2)}/seat × {subscription?.seat_count} seats
                                    </Typography>
                                </Box>
                            )}
                        </Grid>
                    </Grid>

                    {subscription?.current_period_end && (
                        <Box mt={2}>
                            <Alert severity="info">
                                Next billing date: {new Date(subscription.current_period_end).toLocaleDateString()}
                            </Alert>
                        </Box>
                    )}
                </CardContent>
            </Card>

            {/* Upgrade Options */}
            <Typography variant="h5" gutterBottom>
                Available Plans
            </Typography>

            <Grid container spacing={3}>
                {Object.entries(TIER_FEATURES).map(([tier, details]) => {
                    const isCurrent = tier === currentTier;
                    const canUpgrade = !isCurrent && tier !== 'starter' &&
                        (currentTier === 'starter' ||
                            (currentTier === 'professional' && tier === 'enterprise'));

                    return (
                        <Grid item xs={12} md={4} key={tier}>
                            <Card
                                sx={{
                                    height: '100%',
                                    border: isCurrent ? `2px solid ${details.color}` : '1px solid #ddd',
                                    position: 'relative'
                                }}
                            >
                                {isCurrent && (
                                    <Box
                                        sx={{
                                            position: 'absolute',
                                            top: 0,
                                            right: 0,
                                            bgcolor: details.color,
                                            color: 'white',
                                            px: 2,
                                            py: 0.5,
                                            borderBottomLeftRadius: 8
                                        }}
                                    >
                                        <Typography variant="caption">Current Plan</Typography>
                                    </Box>
                                )}

                                <CardContent>
                                    <Typography variant="h5" gutterBottom sx={{ color: details.color }}>
                                        {details.name}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary" gutterBottom>
                                        {details.description}
                                    </Typography>

                                    <Box my={3}>
                                        {details.features.map((feature, idx) => (
                                            <Typography key={idx} variant="body2" sx={{ mb: 0.5 }}>
                                                ✓ {feature}
                                            </Typography>
                                        ))}
                                    </Box>

                                    {canUpgrade && (
                                        <Button
                                            variant="contained"
                                            fullWidth
                                            startIcon={<Upgrade />}
                                            onClick={() => handleUpgradeClick(tier)}
                                            sx={{ backgroundColor: details.color }}
                                        >
                                            Upgrade to {details.name}
                                        </Button>
                                    )}

                                    {isCurrent && (
                                        <Button variant="outlined" fullWidth disabled>
                                            Current Plan
                                        </Button>
                                    )}

                                    {tier === 'starter' && currentTier !== 'starter' && (
                                        <Button variant="outlined" fullWidth disabled>
                                            Cannot Downgrade
                                        </Button>
                                    )}
                                </CardContent>
                            </Card>
                        </Grid>
                    );
                })}
            </Grid>

            {/* Upgrade Dialog */}
            <Dialog open={upgradeDialogOpen} onClose={() => !checkoutLoading && setUpgradeDialogOpen(false)}>
                <DialogTitle>
                    Upgrade to {selectedTier && TIER_FEATURES[selectedTier]?.name}
                </DialogTitle>
                <DialogContent>
                    <Typography variant="body1" gutterBottom>
                        Choose your billing interval:
                    </Typography>

                    <Box my={2}>
                        <Typography variant="body2" color="text.secondary">
                            Current seat count: {subscription?.seat_count} users
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Pricing will be calculated based on your active user count
                        </Typography>
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setUpgradeDialogOpen(false)} disabled={checkoutLoading}>
                        Cancel
                    </Button>
                    <Button
                        onClick={() => handleCheckout('monthly')}
                        variant="contained"
                        disabled={checkoutLoading}
                    >
                        {checkoutLoading ? <CircularProgress size={24} /> : 'Monthly Billing'}
                    </Button>
                    <Button
                        onClick={() => handleCheckout('yearly')}
                        variant="contained"
                        color="secondary"
                        disabled={checkoutLoading}
                    >
                        {checkoutLoading ? <CircularProgress size={24} /> : 'Yearly Billing (Save 15%)'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default SubscriptionSettingsPage;

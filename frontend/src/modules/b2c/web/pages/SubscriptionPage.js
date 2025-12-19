import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import B2CLayout from '../layouts/B2CLayout';
import b2cWorkspaceClient from '../../../../core/api/b2cWorkspaceClient';

const SubscriptionPage = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [currentSubscription, setCurrentSubscription] = useState(null);
    const [plans, setPlans] = useState([]);
    const [loading, setLoading] = useState(true);
    const [billingInterval, setBillingInterval] = useState('monthly');
    const [workspaceId, setWorkspaceId] = useState(null);
    const [upgradingTier, setUpgradingTier] = useState(null);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        try {
            // Load Workspace & Subscription
            let wsId = searchParams.get('workspace_id');
            if (!wsId) {
                const workspacesData = await b2cWorkspaceClient.getWorkspaces();
                const personalWs = workspacesData.workspaces.find(w => w.type === 'personal');
                if (personalWs) wsId = personalWs.id;
                else if (workspacesData.workspaces.length > 0) wsId = workspacesData.workspaces[0].id;
            }

            if (wsId) {
                setWorkspaceId(wsId);
                const subData = await b2cWorkspaceClient.getSubscription(wsId);
                setCurrentSubscription(subData);
            }

            // Load Plans
            const plansData = await b2cWorkspaceClient.getPlans();
            setPlans(plansData);

        } catch (error) {
            console.error('Failed to load data:', error);
        } finally {
            setLoading(false);
        }
    };

    const formatFeatures = (plan) => {
        const featuresList = [];

        // Limits
        if (plan.limits) {
            if (plan.limits.projects === null) featuresList.push('Unlimited projects');
            else featuresList.push(`${plan.limits.projects} projects`);

            if (plan.limits.team_members) featuresList.push(`${plan.limits.team_members} team members`);
            if (plan.limits.storage_gb) featuresList.push(`${plan.limits.storage_gb} GB storage`);
        }

        // Feature flags
        if (plan.features) {
            if (plan.features.priority_support) featuresList.push('Priority support');
            if (plan.features.custom_branding) featuresList.push('Custom branding');
            if (plan.features.sso) featuresList.push('SSO & advanced security');
            if (plan.features.api_access) featuresList.push('API access');
            if (plan.features.audit_logs) featuresList.push('Audit logs');
        }

        // Add default/basic features for look and feel if list is short
        if (plan.tier_key === 'free') {
            featuresList.push('Basic support');
            featuresList.push('Community access');
        }

        return featuresList;
    };

    const handleUpgrade = async (tier) => {
        // If current plan, do nothing
        if (tier === currentSubscription?.tier) return;
        // If free, strictly speaking we should "downgrade" via portal or api, but for now 
        // the checkout flow mostly handles upgrades. 
        // If downgrading to free, usually we send them to portal or handle cancel.
        // For this UI, let's assume we use portal for downgrades if active is not free.

        if (tier === 'free') {
            // Redirect to portal to cancel/downgrade?
            handleManageBilling();
            return;
        }

        setUpgradingTier(tier);
        try {
            const data = await b2cWorkspaceClient.createCheckoutSession({
                workspace_id: workspaceId,
                tier: tier,
                billing_interval: billingInterval,
                success_url: `${window.location.origin}/subscription?success=true`,
                cancel_url: `${window.location.origin}/subscription?canceled=true`
            });

            window.location.href = data.checkout_url;
        } catch (error) {
            console.error('Checkout error:', error);
            alert('Failed to start checkout');
            setUpgradingTier(null);
        }
    };

    const handleManageBilling = async () => {
        try {
            const data = await b2cWorkspaceClient.createPortalSession(window.location.href);
            window.location.href = data.portal_url;
        } catch (error) {
            console.error('Portal error:', error);
        }
    };

    if (loading) {
        return (
            <B2CLayout>
                <div style={{ textAlign: 'center', padding: '60px' }}>
                    <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</div>
                    <p>Loading plans...</p>
                </div>
            </B2CLayout>
        );
    }

    const activeTier = currentSubscription?.tier || 'free';

    return (
        <B2CLayout>
            <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                {/* Header */}
                <div style={{ textAlign: 'center', marginBottom: '48px' }}>
                    <h1 style={{ fontSize: '40px', fontWeight: '700', color: '#111827', marginBottom: '16px' }}>
                        Choose Your Plan
                    </h1>
                    <p style={{ fontSize: '18px', color: '#6B7280', marginBottom: '32px' }}>
                        Select the perfect plan for your needs
                    </p>

                    {/* Success Message */}
                    {searchParams.get('success') && (
                        <div style={{ padding: '16px 24px', backgroundColor: '#D1FAE5', color: '#065F46', borderRadius: '8px', marginBottom: '32px', border: '1px solid #A7F3D0' }}>
                            ✅ Subscription activated successfully!
                        </div>
                    )}

                    {/* Billing Interval Toggle */}
                    <div style={{ display: 'inline-flex', backgroundColor: '#F3F4F6', borderRadius: '10px', padding: '4px' }}>
                        <button
                            onClick={() => setBillingInterval('monthly')}
                            style={{
                                padding: '10px 24px',
                                borderRadius: '8px',
                                border: 'none',
                                backgroundColor: billingInterval === 'monthly' ? '#FFFFFF' : 'transparent',
                                color: billingInterval === 'monthly' ? '#111827' : '#6B7280',
                                fontWeight: billingInterval === 'monthly' ? '600' : '500',
                                cursor: 'pointer',
                                boxShadow: billingInterval === 'monthly' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
                            }}
                        >
                            Monthly
                        </button>
                        <button
                            onClick={() => setBillingInterval('yearly')}
                            style={{
                                padding: '10px 24px',
                                borderRadius: '8px',
                                border: 'none',
                                backgroundColor: billingInterval === 'yearly' ? '#FFFFFF' : 'transparent',
                                color: billingInterval === 'yearly' ? '#111827' : '#6B7280',
                                fontWeight: billingInterval === 'yearly' ? '600' : '500',
                                cursor: 'pointer',
                                boxShadow: billingInterval === 'yearly' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
                            }}
                        >
                            Yearly <span style={{ color: '#10B981', fontSize: '13px' }}>(Save 20%)</span>
                        </button>
                    </div>
                </div>

                {/* Pricing Cards */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                    gap: '24px',
                    marginBottom: '48px'
                }}>
                    {plans.map((plan) => {
                        const isActive = activeTier === plan.tier_key;
                        const isFree = plan.tier_key === 'free';
                        // Prices are in cents
                        const monthlyPriceCents = plan.price_monthly || 0;
                        const yearlyPriceCents = plan.price_yearly || 0;

                        const displayPrice = billingInterval === 'monthly'
                            ? (monthlyPriceCents / 100)
                            : (yearlyPriceCents / 100 / 12).toFixed(0); // Show monthly equivalent for yearly

                        const yearlyTotal = (yearlyPriceCents / 100);

                        const highlight = plan.tier_key === 'premium'; // Hardcoded highlights for now
                        const badge = plan.tier_key === 'premium' ? 'Most Popular' : (plan.tier_key === 'ultimate' ? 'Enterprise' : null);

                        const featuresList = formatFeatures(plan);

                        return (
                            <div
                                key={plan.id}
                                style={{
                                    backgroundColor: 'white',
                                    borderRadius: '16px',
                                    padding: '32px',
                                    border: highlight ? '3px solid #6366F1' : '2px solid #E5E7EB',
                                    position: 'relative',
                                    boxShadow: highlight ? '0 10px 40px rgba(99, 102, 241, 0.2)' : 'none',
                                    transform: highlight ? 'scale(1.05)' : 'scale(1)',
                                    transition: 'transform 0.2s',
                                    zIndex: highlight ? 10 : 1
                                }}
                            >
                                {badge && (
                                    <div style={{
                                        position: 'absolute',
                                        top: '-12px',
                                        left: '50%',
                                        transform: 'translateX(-50%)',
                                        backgroundColor: highlight ? '#6366F1' : '#10B981',
                                        color: 'white',
                                        padding: '6px 20px',
                                        borderRadius: '9999px',
                                        fontSize: '13px',
                                        fontWeight: '600'
                                    }}>
                                        {badge}
                                    </div>
                                )}

                                <h3 style={{ fontSize: '24px', fontWeight: '700', color: '#111827', marginBottom: '8px', marginTop: badge ? '8px' : '0' }}>
                                    {plan.name}
                                </h3>

                                <div style={{ marginBottom: '24px' }}>
                                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                                        <span style={{ fontSize: '48px', fontWeight: '700', color: '#111827' }}>
                                            ${displayPrice}
                                        </span>
                                        <span style={{ fontSize: '16px', color: '#6B7280' }}>
                                            /mo
                                        </span>
                                    </div>
                                    {billingInterval === 'yearly' && !isFree && (
                                        <div style={{ fontSize: '14px', color: '#10B981', marginTop: '4px' }}>
                                            Billed ${yearlyTotal} yearly
                                        </div>
                                    )}
                                </div>

                                <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 32px 0' }}>
                                    {featuresList.map((feature, idx) => (
                                        <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '12px', fontSize: '15px', color: '#374151' }}>
                                            <span style={{ color: '#10B981', fontSize: '18px' }}>✓</span>
                                            <span>{feature}</span>
                                        </li>
                                    ))}
                                </ul>

                                <button
                                    onClick={() => handleUpgrade(plan.tier_key)}
                                    disabled={isActive || upgradingTier !== null}
                                    style={{
                                        width: '100%',
                                        padding: '16px',
                                        borderRadius: '10px',
                                        border: 'none',
                                        background: isActive ? '#9CA3AF' : (highlight ? 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)' : '#E5E7EB'),
                                        color: isActive || !highlight ? (isActive ? 'white' : '#111827') : 'white',
                                        fontSize: '16px',
                                        fontWeight: '600',
                                        cursor: isActive || upgradingTier !== null ? 'not-allowed' : 'pointer',
                                    }}
                                >
                                    {isActive ? 'Current Plan' : (isFree ? 'Downgrade via Portal' : (upgradingTier === plan.tier_key ? 'Processing...' : `Upgrade to ${plan.name}`))}
                                </button>
                            </div>
                        );
                    })}
                </div>

                {/* Payment Method Card */}
                {currentSubscription?.payment_method_info ? (
                    <div style={{
                        backgroundColor: 'white',
                        borderRadius: '12px',
                        padding: '24px',
                        border: '1px solid #E5E7EB',
                        marginBottom: '24px',
                        maxWidth: '600px', // Constrain width
                        margin: '0 auto 24px auto', // Center
                        textAlign: 'left' // Reset text align (parent is centered?)
                    }}>
                        <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px', color: '#111827' }}>Payment Method</h3>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                            <div style={{
                                width: '50px',
                                height: '32px',
                                border: '1px solid #E5E7EB',
                                borderRadius: '6px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                backgroundColor: '#F9FAFB',
                                flexShrink: 0
                            }}>
                                <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase' }}>
                                    {currentSubscription.payment_method_info.card_brand}
                                </span>
                            </div>
                            <div>
                                <div style={{ fontSize: '16px', color: '#111827', fontWeight: '500' }}>
                                    •••• •••• •••• {currentSubscription.payment_method_info.card_last4}
                                </div>
                                <div style={{ fontSize: '13px', color: '#6B7280' }}>
                                    Expires {currentSubscription.payment_method_info.exp_month}/{currentSubscription.payment_method_info.exp_year}
                                </div>
                            </div>
                        </div>
                        <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#EFF6FF', borderLeft: '4px solid #3B82F6', borderRadius: '6px' }}>
                            <span style={{ fontSize: '13px', color: '#1E40AF' }}>
                                ℹ️ Payment method is managed securely via Stripe.
                            </span>
                        </div>
                    </div>
                ) : (
                    <div style={{
                        backgroundColor: 'white',
                        borderRadius: '12px',
                        padding: '24px',
                        border: '1px solid #E5E7EB',
                        marginBottom: '24px',
                        maxWidth: '600px', // Constrain width
                        margin: '0 auto 24px auto', // Center
                        textAlign: 'left'
                    }}>
                        <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px', color: '#111827' }}>Payment Method</h3>
                        <div style={{
                            padding: '24px',
                            backgroundColor: '#F9FAFB',
                            borderRadius: '8px',
                            border: '1px dashed #D1D5DB',
                            textAlign: 'center'
                        }}>
                            <div style={{ fontSize: '32px', marginBottom: '12px' }}>💳</div>
                            <div style={{ fontSize: '16px', fontWeight: '600', color: '#374151', marginBottom: '8px' }}>
                                No Payment Method Required
                            </div>
                            <div style={{ fontSize: '14px', color: '#6B7280', lineHeight: '1.5' }}>
                                {activeTier === 'free' ? (
                                    <>You're on the free plan. Upgrade to Premium or Ultimate to add a payment method.</>
                                ) : (
                                    <>Payment method information will appear here after you complete the checkout process.</>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {activeTier !== 'free' && (
                    <div style={{ backgroundColor: 'white', borderRadius: '12px', padding: '28px', border: '1px solid #E5E7EB', textAlign: 'center' }}>
                        <h3 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '12px' }}>Manage Your Subscription</h3>
                        <p style={{ color: '#6B7280', marginBottom: '20px' }}>Update payment method, view invoices, or cancel subscription</p>
                        <button
                            onClick={handleManageBilling}
                            style={{ padding: '12px 32px', borderRadius: '8px', border: '2px solid #6366F1', backgroundColor: 'white', color: '#6366F1', fontSize: '15px', fontWeight: '600', cursor: 'pointer' }}
                        >
                            Open Billing Portal
                        </button>
                    </div>
                )}
            </div>
        </B2CLayout>
    );
};

export default SubscriptionPage;

import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { auth } from '../../../../core/firebase/b2c-config';
import B2CLayout from '../layouts/B2CLayout';

const PLANS = [
    {
        tier: 'free',
        name: 'Free',
        price: { monthly: 0, yearly: 0 },
        features: [
            '1 workspace',
            '5 projects',
            '100 MB storage',
            'Basic support',
            'Community access'
        ],
        highlight: false
    },
    {
        tier: 'premium',
        name: 'Premium',
        price: { monthly: 15, yearly: 144 }, // $12/mo when paid yearly
        features: [
            'Unlimited workspaces',
            'Unlimited projects',
            '10 GB storage',
            'Priority support',
            'Advanced analytics',
            'Custom branding',
            'API access'
        ],
        highlight: true,
        badge: 'Most Popular'
    },
    {
        tier: 'ultimate',
        name: 'Ultimate',
        price: { monthly: 30, yearly: 288 }, // $24/mo when paid yearly
        features: [
            'Everything in Premium',
            'Unlimited storage',
            '24/7 phone support',
            'Dedicated account manager',
            'Custom integrations',
            'SSO & advanced security',
            'SLA guarantee'
        ],
        highlight: false,
        badge: 'Enterprise'
    }
];

const SubscriptionPage = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [currentSubscription, setCurrentSubscription] = useState(null);
    const [loading, setLoading] = useState(true);
    const [billingInterval, setBillingInterval] = useState('monthly');
    const [workspaceId, setWorkspaceId] = useState(null);
    const [upgrading, setUpgrading] = useState(false);

    useEffect(() => {
        loadSubscription();
    }, []);

    const loadSubscription = async () => {
        setLoading(true);
        try {
            const user = auth.currentUser;
            if (!user) {
                navigate('/login');
                return;
            }

            const token = await user.getIdToken();

            // For now, get first workspace ID (in production, user would select)
            const wsId = searchParams.get('workspace_id') || 'default-workspace';
            setWorkspaceId(wsId);

            const response = await fetch(`/api/b2c/billing/subscription?workspace_id=${wsId}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                setCurrentSubscription(data);
            }
        } catch (error) {
            console.error('Failed to load subscription:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleUpgrade = async (tier) => {
        if (tier === 'free' || tier === currentSubscription?.tier) return;

        setUpgrading(true);
        try {
            const user = auth.currentUser;
            const token = await user.getIdToken();

            const response = await fetch('/api/b2c/billing/checkout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    workspace_id: workspaceId,
                    tier: tier,
                    billing_interval: billingInterval,
                    success_url: `${window.location.origin}/subscription?success=true`,
                    cancel_url: `${window.location.origin}/subscription?canceled=true`
                })
            });

            if (response.ok) {
                const data = await response.json();
                // Redirect to Stripe Checkout
                window.location.href = data.checkout_url;
            } else {
                alert('Failed to start checkout');
            }
        } catch (error) {
            console.error('Checkout error:', error);
            alert('Failed to start checkout');
        } finally {
            setUpgrading(false);
        }
    };

    const handleManageBilling = async () => {
        try {
            const user = auth.currentUser;
            const token = await user.getIdToken();

            const response = await fetch('/api/b2c/billing/portal', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    return_url: window.location.href
                })
            });

            if (response.ok) {
                const data = await response.json();
                window.location.href = data.portal_url;
            }
        } catch (error) {
            console.error('Portal error:', error);
        }
    };

    if (loading) {
        return (
            <B2CLayout>
                <div style={{ textAlign: 'center', padding: '60px' }}>
                    <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</div>
                    <p>Loading subscription...</p>
                </div>
            </B2CLayout>
        );
    }

    const activeTier = currentSubscription?.tier || 'free';
    const isYearlySavings = billingInterval === 'yearly';

    return (
        <B2CLayout>
            <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                {/* Header */}
                <div style={{ textAlign: 'center', marginBottom: '48px' }}>
                    <h1 style={{
                        fontSize: '40px',
                        fontWeight: '700',
                        color: '#111827',
                        marginBottom: '16px'
                    }}>
                        Choose Your Plan
                    </h1>
                    <p style={{
                        fontSize: '18px',
                        color: '#6B7280',
                        marginBottom: '32px'
                    }}>
                        Select the perfect plan for your needs
                    </p>

                    {/* Success Message */}
                    {searchParams.get('success') && (
                        <div style={{
                            padding: '16px 24px',
                            backgroundColor: '#D1FAE5',
                            color: '#065F46',
                            borderRadius: '8px',
                            marginBottom: '32px',
                            border: '1px solid #A7F3D0'
                        }}>
                            ✅ Subscription activated successfully!
                        </div>
                    )}

                    {/* Billing Interval Toggle */}
                    <div style={{
                        display: 'inline-flex',
                        backgroundColor: '#F3F4F6',
                        borderRadius: '10px',
                        padding: '4px'
                    }}>
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
                            Month monthly
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
                    {PLANS.map((plan) => {
                        const isActive = activeTier === plan.tier;
                        const price = plan.price[billingInterval];
                        const monthlyPrice = billingInterval === 'yearly' ? price / 12 : price;

                        return (
                            <div
                                key={plan.tier}
                                style={{
                                    backgroundColor: 'white',
                                    borderRadius: '16px',
                                    padding: '32px',
                                    border: plan.highlight ? '3px solid #6366F1' : '2px solid #E5E7EB',
                                    position: 'relative',
                                    boxShadow: plan.highlight ? '0 10px 40px rgba(99, 102, 241, 0.2)' : 'none',
                                    transform: plan.highlight ? 'scale(1.05)' : 'scale(1)',
                                    transition: 'transform 0.2s'
                                }}
                            >
                                {/* Badge */}
                                {plan.badge && (
                                    <div style={{
                                        position: 'absolute',
                                        top: '-12px',
                                        left: '50%',
                                        transform: 'translateX(-50%)',
                                        backgroundColor: plan.highlight ? '#6366F1' : '#10B981',
                                        color: 'white',
                                        padding: '6px 20px',
                                        borderRadius: '9999px',
                                        fontSize: '13px',
                                        fontWeight: '600'
                                    }}>
                                        {plan.badge}
                                    </div>
                                )}

                                {/* Plan Name */}
                                <h3 style={{
                                    fontSize: '24px',
                                    fontWeight: '700',
                                    color: '#111827',
                                    marginBottom: '8px',
                                    marginTop: plan.badge ? '8px' : '0'
                                }}>
                                    {plan.name}
                                </h3>

                                {/* Price */}
                                <div style={{ marginBottom: '24px' }}>
                                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                                        <span style={{
                                            fontSize: '48px',
                                            fontWeight: '700',
                                            color: '#111827'
                                        }}>
                                            ${Math.round(monthlyPrice)}
                                        </span>
                                        <span style={{ fontSize: '16px', color: '#6B7280' }}>
                                            /month
                                        </span>
                                    </div>
                                    {billingInterval === 'yearly' && plan.tier !== 'free' && (
                                        <div style={{ fontSize: '14px', color: '#10B981', marginTop: '4px' }}>
                                            Billed ${price} annually
                                        </div>
                                    )}
                                </div>

                                {/* Features */}
                                <ul style={{
                                    listStyle: 'none',
                                    padding: 0,
                                    margin: '0 0 32px 0'
                                }}>
                                    {plan.features.map((feature, idx) => (
                                        <li key={idx} style={{
                                            display: 'flex',
                                            alignItems: 'flex-start',
                                            gap: '12px',
                                            marginBottom: '12px',
                                            fontSize: '15px',
                                            color: '#374151'
                                        }}>
                                            <span style={{ color: '#10B981', fontSize: '18px' }}>✓</span>
                                            <span>{feature}</span>
                                        </li>
                                    ))}
                                </ul>

                                {/* CTA Button */}
                                <button
                                    onClick={() => handleUpgrade(plan.tier)}
                                    disabled={isActive || upgrading || plan.tier === 'free'}
                                    style={{
                                        width: '100%',
                                        padding: '16px',
                                        borderRadius: '10px',
                                        border: 'none',
                                        background: isActive
                                            ? '#9CA3AF'
                                            : plan.highlight
                                                ? 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)'
                                                : plan.tier === 'free'
                                                    ? '#E5E7EB'
                                                    : '#6366F1',
                                        color: isActive || plan.tier === 'free' ? '#6B7280' : 'white',
                                        fontSize: '16px',
                                        fontWeight: '600',
                                        cursor: isActive || plan.tier === 'free' || upgrading ? 'not-allowed' : 'pointer',
                                        boxShadow: isActive || plan.tier === 'free' ? 'none' : '0 4px 12px rgba(99, 102, 241, 0.3)'
                                    }}
                                >
                                    {isActive ? '✓ Current Plan' : plan.tier === 'free' ? 'Free Forever' : upgrading ? 'Processing...' : `Upgrade to ${plan.name}`}
                                </button>
                            </div>
                        );
                    })}
                </div>

                {/* Manage Billing */}
                {activeTier !== 'free' && (
                    <div style={{
                        backgroundColor: 'white',
                        borderRadius: '12px',
                        padding: '28px',
                        border: '1px solid #E5E7EB',
                        textAlign: 'center'
                    }}>
                        <h3 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '12px' }}>
                            Manage Your Subscription
                        </h3>
                        <p style={{ color: '#6B7280', marginBottom: '20px' }}>
                            Update payment method, view invoices, or cancel subscription
                        </p>
                        <button
                            onClick={handleManageBilling}
                            style={{
                                padding: '12px 32px',
                                borderRadius: '8px',
                                border: '2px solid #6366F1',
                                backgroundColor: 'white',
                                color: '#6366F1',
                                fontSize: '15px',
                                fontWeight: '600',
                                cursor: 'pointer'
                            }}
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

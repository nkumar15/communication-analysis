import React, { useState } from 'react';
import './PricingPage.css';

const PRICING_TIERS = {
    free: {
        name: 'Free',
        price: { monthly: 0, yearly: 0 },
        description: 'Perfect for trying out',
        features: [
            '5 projects',
            '1 GB storage',
            '2 team members (view only)',
            'Basic features',
            'Community support',
        ],
    },
    premium: {
        name: 'Premium',
        price: { monthly: 19, yearly: 190 },
        description: 'For growing teams',
        features: [
            'Unlimited projects',
            '10 GB storage',
            'Up to 10 team members',
            '3 team workspaces',
            'Priority support',
            'Custom branding',
            'Data export',
        ],
        popular: true,
    },
    ultimate: {
        name: 'Ultimate',
        price: { monthly: 49, yearly: 490 },
        description: 'For large organizations',
        features: [
            'Everything in Premium',
            '100 GB storage',
            'Unlimited team members',
            'Unlimited team workspaces',
            'SSO (SAML/OIDC)',
            'Advanced analytics',
            'Audit logs',
            'API access',
            'Dedicated support',
        ],
    },
};

const PricingPage = () => {
    const [billingInterval, setBillingInterval] = useState('monthly');
    const [couponCode, setCouponCode] = useState('');
    const [couponValid, setCouponValid] = useState(null);
    const [validatingCoupon, setValidatingCoupon] = useState(false);
    const [loading, setLoading] = useState(null);

    const handleUpgrade = async (tier) => {
        if (tier === 'free') {
            alert('You are currently on the free tier.');
            return;
        }

        setLoading(tier);

        try {
            const token = localStorage.getItem('authToken');
            if (!token) {
                alert('Please log in to upgrade.');
                window.location.href = '/login';
                return;
            }

            const workspaceId = localStorage.getItem('currentWorkspaceId');
            if (!workspaceId) {
                alert('No workspace found. Please create a workspace first.');
                return;
            }

            const response = await fetch('http://localhost:8002/api/b2c/billing/checkout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    workspace_id: workspaceId,
                    tier: tier,
                    billing_interval: billingInterval,
                    coupon_code: couponCode || undefined,
                    success_url: `${window.location.origin}/billing/subscription`,
                    cancel_url: `${window.location.origin}/pricing`,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to create checkout session');
            }

            // Redirect to Stripe Checkout
            window.location.href = data.checkout_url;

        } catch (error) {
            console.error('Checkout error:', error);
            alert(error.message || 'Failed to start checkout');
        } finally {
            setLoading(null);
        }
    };

    const validateCoupon = async () => {
        if (!couponCode.trim()) {
            setCouponValid(null);
            return;
        }

        setValidatingCoupon(true);

        try {
            const token = localStorage.getItem('authToken');
            const response = await fetch('http://localhost:8002/api/b2c/billing/coupons/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    code: couponCode,
                }),
            });

            const data = await response.json();

            if (response.ok) {
                setCouponValid(data);
            } else {
                setCouponValid(null);
                alert(data.detail || 'This coupon is not valid');
            }
        } catch (error) {
            console.error('Coupon validation error:', error);
            setCouponValid(null);
        } finally {
            setValidatingCoupon(false);
        }
    };

    const calculateSavings = (tier) => {
        const monthly = PRICING_TIERS[tier].price.monthly;
        const yearly = PRICING_TIERS[tier].price.yearly;
        if (monthly === 0) return 0;
        return Math.round(((monthly * 12 - yearly) / (monthly * 12)) * 100);
    };

    return (
        <div className="pricing-page">
            <div className="pricing-header">
                <h1>Choose Your Plan</h1>
                <p className="subtitle">Upgrade anytime. Cancel anytime. No hidden fees.</p>
            </div>

            {/* Billing Interval Toggle */}
            <div className="billing-toggle">
                <button
                    className={`toggle-btn ${billingInterval === 'monthly' ? 'active' : ''}`}
                    onClick={() => setBillingInterval('monthly')}
                >
                    Monthly
                </button>
                <button
                    className={`toggle-btn ${billingInterval === 'yearly' ? 'active' : ''}`}
                    onClick={() => setBillingInterval('yearly')}
                >
                    Yearly
                    <span className="savings-badge">Save up to 20%</span>
                </button>
            </div>

            {/* Coupon Code */}
            <div className="coupon-section">
                <input
                    type="text"
                    className="coupon-input"
                    placeholder="Have a coupon code?"
                    value={couponCode}
                    onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                />
                <button
                    className="apply-btn"
                    onClick={validateCoupon}
                    disabled={validatingCoupon || !couponCode.trim()}
                >
                    {validatingCoupon ? 'Validating...' : 'Apply'}
                </button>
            </div>

            {couponValid && (
                <div className="coupon-success">
                    ✓ {couponValid.description || 'Coupon applied successfully'}
                </div>
            )}

            {/* Pricing Cards */}
            <div className="pricing-grid">
                {Object.entries(PRICING_TIERS).map(([tierId, tier]) => {
                    const price = tier.price[billingInterval];
                    const savings = calculateSavings(tierId);

                    return (
                        <div
                            key={tierId}
                            className={`pricing-card ${tier.popular ? 'popular' : ''}`}
                        >
                            {tier.popular && <div className="popular-badge">MOST POPULAR</div>}

                            <h3 className="tier-name">{tier.name}</h3>
                            <p className="tier-description">{tier.description}</p>

                            <div className="price-container">
                                <span className="currency">$</span>
                                <span className="price">{price}</span>
                                <span className="period">/{billingInterval === 'monthly' ? 'month' : 'year'}</span>
                            </div>

                            {savings > 0 && billingInterval === 'yearly' && (
                                <p className="savings-text">Save {savings}% with yearly billing</p>
                            )}

                            <ul className="features-list">
                                {tier.features.map((feature, index) => (
                                    <li key={index}>
                                        <svg className="checkmark" viewBox="0 0 20 20" fill="currentColor">
                                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                        </svg>
                                        {feature}
                                    </li>
                                ))}
                            </ul>

                            <button
                                className={`upgrade-btn ${tier.popular ? 'popular-btn' : ''} ${tierId === 'free' ? 'free-btn' : ''}`}
                                onClick={() => handleUpgrade(tierId)}
                                disabled={loading === tierId || tierId === 'free'}
                            >
                                {loading === tierId ? (
                                    <span className="spinner"></span>
                                ) : tierId === 'free' ? (
                                    'Current Plan'
                                ) : (
                                    'Upgrade Now'
                                )}
                            </button>
                        </div>
                    );
                })}
            </div>

            {/* Footer */}
            <div className="pricing-footer">
                <p>All plans include SSL, automatic backups, and 99.9% uptime SLA.</p>
                <p>Need enterprise features? <a href="/contact">Contact sales</a> for custom pricing.</p>
            </div>
        </div>
    );
};

export default PricingPage;

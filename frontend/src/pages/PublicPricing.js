import React, { useState } from 'react';
import './PublicPricing.css';

const PublicPricing = () => {
    const [billingPeriod, setBillingPeriod] = useState('monthly');

    const tiers = [
        {
            id: 'free',
            name: 'Free',
            tagline: 'Perfect for getting started',
            price: { monthly: 0, yearly: 0 },
            features: [
                '5 projects',
                '1 GB storage',
                '2 team members',
                'Basic features',
                'Community support',
            ],
            cta: 'Get Started Free',
            ctaLink: '/signup',
            popular: false,
        },
        {
            id: 'premium',
            name: 'Premium',
            tagline: 'For growing teams',
            price: { monthly: 19, yearly: 190 },
            features: [
                'Unlimited projects',
                '10 GB storage',
                'Up to 10 team members',
                '3 team workspaces',
                'Priority email support',
                'Custom branding',
                'Data export',
            ],
            cta: 'Start Free Trial',
            ctaLink: '/signup?plan=premium',
            popular: true,
        },
        {
            id: 'ultimate',
            name: 'Ultimate',
            tagline: 'For large organizations',
            price: { monthly: 49, yearly: 490 },
            features: [
                'Everything in Premium',
                '100 GB storage',
                'Unlimited team members',
                'Unlimited workspaces',
                'SSO (SAML/OIDC)',
                'Advanced analytics',
                'Audit logs',
                'API access',
                'Dedicated support',
            ],
            cta: 'Start Free Trial',
            ctaLink: '/signup?plan=ultimate',
            popular: false,
        },
    ];

    const calculateSavings = (tier) => {
        if (tier.price.monthly === 0) return 0;
        const monthlyCost = tier.price.monthly * 12;
        const yearlyCost = tier.price.yearly;
        return Math.round(((monthlyCost - yearlyCost) / monthlyCost) * 100);
    };

    return (
        <div className="public-pricing">
            {/* Hero Section */}
            <div className="pricing-hero">
                <h1>Simple, transparent pricing</h1>
                <p className="hero-subtitle">
                    Choose the plan that fits your needs. No hidden fees. Cancel anytime.
                </p>

                {/* Billing Toggle */}
                <div className="billing-toggle">
                    <button
                        className={billingPeriod === 'monthly' ? 'active' : ''}
                        onClick={() => setBillingPeriod('monthly')}
                    >
                        Monthly
                    </button>
                    <button
                        className={billingPeriod === 'yearly' ? 'active' : ''}
                        onClick={() => setBillingPeriod('yearly')}
                    >
                        Yearly
                        <span className="save-badge">Save up to 20%</span>
                    </button>
                </div>
            </div>

            {/* Pricing Cards */}
            <div className="pricing-cards">
                {tiers.map((tier) => {
                    const price = tier.price[billingPeriod];
                    const savings = calculateSavings(tier);

                    return (
                        <div
                            key={tier.id}
                            className={`pricing-card ${tier.popular ? 'popular' : ''}`}
                        >
                            {tier.popular && <div className="popular-badge">Most Popular</div>}

                            <div className="card-header">
                                <h3>{tier.name}</h3>
                                <p className="tagline">{tier.tagline}</p>
                            </div>

                            <div className="card-price">
                                <span className="currency">$</span>
                                <span className="amount">{price}</span>
                                <span className="period">
                                    /{billingPeriod === 'monthly' ? 'mo' : 'yr'}
                                </span>
                            </div>

                            {savings > 0 && billingPeriod === 'yearly' && (
                                <div className="savings">Save {savings}% annually</div>
                            )}

                            <a
                                href={tier.ctaLink}
                                className={`cta-button ${tier.popular ? 'primary' : 'secondary'}`}
                            >
                                {tier.cta}
                            </a>

                            <div className="features">
                                <p className="features-title">What's included:</p>
                                <ul>
                                    {tier.features.map((feature, index) => (
                                        <li key={index}>
                                            <svg className="check-icon" viewBox="0 0 20 20" fill="currentColor">
                                                <path
                                                    fillRule="evenodd"
                                                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                                    clipRule="evenodd"
                                                />
                                            </svg>
                                            {feature}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* FAQ Section */}
            <div className="pricing-faq">
                <h2>Frequently Asked Questions</h2>
                <div className="faq-grid">
                    <div className="faq-item">
                        <h3>Can I change plans later?</h3>
                        <p>Yes! You can upgrade, downgrade, or cancel your plan at any time. Changes take effect at the start of your next billing cycle.</p>
                    </div>
                    <div className="faq-item">
                        <h3>Is there a free trial?</h3>
                        <p>Yes, Premium and Ultimate plans come with a 14-day free trial. No credit card required to start.</p>
                    </div>
                    <div className="faq-item">
                        <h3>What payment methods do you accept?</h3>
                        <p>We accept all major credit cards (Visa, Mastercard, American Express) through our secure payment processor Stripe.</p>
                    </div>
                    <div className="faq-item">
                        <h3>Do you offer refunds?</h3>
                        <p>Yes, we offer a 30-day money-back guarantee. If you're not satisfied, contact us for a full refund.</p>
                    </div>
                </div>
            </div>

            {/* Trust Section */}
            <div className="trust-section">
                <p>✓ Secure 256-bit SSL encryption</p>
                <p>✓ 99.9% uptime SLA</p>
                <p>✓ GDPR & SOC 2 compliant</p>
            </div>

            {/* CTA Section */}
            <div className="final-cta">
                <h2>Ready to get started?</h2>
                <p>Join thousands of teams already using our platform</p>
                <a href="/signup" className="cta-button primary large">
                    Start Free Trial
                </a>
                <p className="cta-subtext">No credit card required • Cancel anytime</p>
            </div>
        </div>
    );
};

export default PublicPricing;

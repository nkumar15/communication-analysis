import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './LandingPage.css';

const LandingPage = () => {
    const navigate = useNavigate();
    const [billingPeriod, setBillingPeriod] = useState('monthly');

    const tiers = [
        {
            id: 'free',
            name: 'Free',
            tagline: 'Perfect for getting started',
            price: { monthly: 0, yearly: 0 },
            features: ['5 projects', '1 GB storage', '2 members', 'Basic features'],
            cta: 'Get Started',
        },
        {
            id: 'premium',
            name: 'Premium',
            tagline: 'For growing teams',
            price: { monthly: 19, yearly: 190 },
            features: ['Unlimited projects', '10 GB storage', '10 members', 'Priority support'],
            cta: 'Start Trial',
            popular: true,
        },
        {
            id: 'ultimate',
            name: 'Ultimate',
            tagline: 'For enterprises',
            price: { monthly: 49, yearly: 490 },
            features: ['Everything in Premium', '100 GB storage', 'Unlimited members', 'SSO & API'],
            cta: 'Start Trial',
        },
    ];

    const handleGetStarted = (tier) => {
        navigate(`/signup?plan=${tier}`);
    };

    return (
        <div className="landing-page">
            {/* Navigation */}
            <nav className="landing-nav">
                <div className="nav-container">
                    <div className="logo">YourApp</div>
                    <div className="nav-links">
                        <button onClick={() => navigate('/login')} className="nav-link">
                            Log In
                        </button>
                        <button onClick={() => navigate('/signup')} className="nav-button">
                            Sign Up Free
                        </button>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="hero">
                <div className="hero-content">
                    <h1 className="hero-title">
                        Build better, together
                    </h1>
                    <p className="hero-subtitle">
                        Collaborate seamlessly with your team. Start free, upgrade as you grow.
                    </p>
                    <div className="hero-ctas">
                        <button onClick={() => navigate('/signup')} className="cta-primary">
                            Get Started Free
                        </button>
                        <button onClick={() => navigate('/login')} className="cta-secondary">
                            Log In
                        </button>
                    </div>
                    <p className="hero-note">No credit card required • Free forever</p>
                </div>
            </section>

            {/* Pricing Section */}
            <section className="pricing" id="pricing">
                <div className="pricing-header">
                    <h2>Simple, transparent pricing</h2>
                    <p>Choose the plan that fits your needs</p>

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
                            <span className="save-label">Save 20%</span>
                        </button>
                    </div>
                </div>

                <div className="pricing-tiers">
                    {tiers.map((tier) => (
                        <div key={tier.id} className={`tier-card ${tier.popular ? 'popular' : ''}`}>
                            {tier.popular && <div className="popular-badge">Popular</div>}

                            <h3>{tier.name}</h3>
                            <p className="tier-tagline">{tier.tagline}</p>

                            <div className="tier-price">
                                <span className="currency">$</span>
                                <span className="amount">{tier.price[billingPeriod]}</span>
                                <span className="period">/{billingPeriod === 'monthly' ? 'mo' : 'yr'}</span>
                            </div>

                            <button
                                onClick={() => handleGetStarted(tier.id)}
                                className={`tier-cta ${tier.popular ? 'primary' : 'secondary'}`}
                            >
                                {tier.cta}
                            </button>

                            <ul className="tier-features">
                                {tier.features.map((feature, i) => (
                                    <li key={i}>
                                        <svg className="check" viewBox="0 0 20 20" fill="currentColor">
                                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                        </svg>
                                        {feature}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>
            </section>

            {/* Social Proof */}
            <section className="social-proof">
                <p className="proof-stat">✓ Trusted by 10,000+ teams</p>
                <p className="proof-stat">✓ 99.9% uptime guaranteed</p>
                <p className="proof-stat">✓ GDPR & SOC 2 compliant</p>
            </section>

            {/* Footer CTA */}
            <section className="footer-cta">
                <h2>Ready to get started?</h2>
                <p>Join thousands of teams already using our platform</p>
                <button onClick={() => navigate('/signup')} className="cta-primary large">
                    Start Free Trial
                </button>
            </section>
        </div>
    );
};

export default LandingPage;

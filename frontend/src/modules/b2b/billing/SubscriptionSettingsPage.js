import React, { useState, useEffect } from 'react';
import apiService from '../../../core/api/b2bClient';
import AdminLayout from '../web/layouts/AdminLayout';

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
        color: '#FF9800',
        contactRequired: true
    }
};

const SubscriptionSettingsPage = () => {
    const [subscription, setSubscription] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [upgradeDialogOpen, setUpgradeDialogOpen] = useState(false);
    const [selectedTier, setSelectedTier] = useState(null);
    const [checkoutLoading, setCheckoutLoading] = useState(false);
    const [couponCode, setCouponCode] = useState('');
    const [billingProfile, setBillingProfile] = useState({
        tax_id: '',
        vat_number: '',
        billing_address: '',
        billing_email: ''
    });
    const [profileLoading, setProfileLoading] = useState(false);

    useEffect(() => {
        fetchSubscription();
        fetchBillingProfile();
    }, []);

    const fetchBillingProfile = async () => {
        try {
            const data = await apiService.get('/api/b2b/billing/profile');
            // Populate if data exists
            if (data) {
                setBillingProfile({
                    tax_id: data.tax_id || '',
                    vat_number: data.vat_number || '',
                    billing_address: data.billing_address || '',
                    billing_email: data.billing_email || ''
                });
            }
        } catch (err) {
            console.error('Failed to fetch billing profile:', err);
        }
    };

    const handleUpdateProfile = async (e) => {
        e.preventDefault();
        setProfileLoading(true);
        try {
            await apiService.patch('/api/b2b/billing/profile', billingProfile);
            alert("Billing details updated successfully.");
        } catch (err) {
            console.error('Profile update error:', err);
            alert('Failed to update billing details.');
        } finally {
            setProfileLoading(false);
        }
    };

    const fetchSubscription = async () => {
        try {
            setLoading(true);
            const data = await apiService.get('/api/b2b/billing/subscription');
            setSubscription(data);
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
            const data = await apiService.post('/api/b2b/billing/checkout', {
                tier: selectedTier,
                billing_interval: billingInterval,
                coupon_code: couponCode || undefined
            });

            // Redirect to Stripe checkout
            window.location.href = data.checkout_url;
        } catch (err) {
            console.error('Checkout error:', err);
            alert('Failed to create checkout session. Please try again.');
            setCheckoutLoading(false);
        }
    };

    if (loading) {
        return (
            <AdminLayout title="Subscription & Billing" subtitle="Manage your plan and billing">
                <div style={{ padding: '60px', textAlign: 'center' }}>
                    <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</div>
                    <p style={{ color: '#6B7280' }}>Loading...</p>
                </div>
            </AdminLayout>
        );
    }

    if (error) {
        return (
            <AdminLayout title="Subscription & Billing" subtitle="Manage your plan and billing">
                <div style={{ padding: '32px' }}>
                    <div style={{ backgroundColor: '#FEF2F2', border: '1px solid #FCA5A5', borderRadius: '8px', padding: '12px 16px', color: '#DC2626' }}>
                        {error}
                    </div>
                </div>
            </AdminLayout>
        );
    }

    const currentTier = subscription?.tier || 'starter';
    const isStarterTier = currentTier === 'starter';

    return (
        <AdminLayout title="Subscription & Billing" subtitle="Manage your plan and billing">
            <div style={{ padding: '32px', maxWidth: '1400px', margin: '0 auto' }}>
                {/* Current Subscription Card */}
                <div style={{
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    padding: '24px',
                    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                    border: '1px solid #E5E7EB',
                    marginBottom: '24px'
                }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
                        <div>
                            <h3 style={{ margin: 0, marginBottom: '16px', fontSize: '18px', fontWeight: '600', color: '#111827' }}>Current Plan</h3>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                                <span style={{
                                    padding: '6px 12px',
                                    backgroundColor: TIER_FEATURES[currentTier].color + '20',
                                    color: TIER_FEATURES[currentTier].color,
                                    borderRadius: '6px',
                                    fontSize: '14px',
                                    fontWeight: '600'
                                }}>
                                    {TIER_FEATURES[currentTier].name}
                                </span>
                                <span style={{
                                    padding: '6px 12px',
                                    backgroundColor: '#D1FAE5',
                                    color: '#059669',
                                    borderRadius: '6px',
                                    fontSize: '14px',
                                    fontWeight: '600',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '4px'
                                }}>
                                    <span>✓</span>
                                    {subscription?.status || 'Active'}
                                </span>
                            </div>
                            <p style={{ margin: 0, fontSize: '14px', color: '#6B7280' }}>
                                {TIER_FEATURES[currentTier].description}
                            </p>
                        </div>

                        <div>
                            <h3 style={{ margin: 0, marginBottom: '16px', fontSize: '18px', fontWeight: '600', color: '#111827' }}>Pricing Details</h3>
                            <div style={{ display: 'flex', gap: '24px' }}>
                                <div>
                                    <div style={{ fontSize: '12px', color: '#6B7280', marginBottom: '4px' }}>Seat Count</div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <span style={{ fontSize: '20px' }}>👥</span>
                                        <span style={{ fontSize: '20px', fontWeight: '600', color: '#111827' }}>
                                            {subscription?.seat_count || 0} users
                                        </span>
                                    </div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '12px', color: '#6B7280', marginBottom: '4px' }}>Total Cost</div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <span style={{ fontSize: '20px' }}>💵</span>
                                        <span style={{ fontSize: '20px', fontWeight: '600', color: '#111827' }}>
                                            ${((subscription?.total_amount_cents || 0) / 100).toFixed(2)}
                                            <span style={{ fontSize: '14px', color: '#6B7280', fontWeight: '400' }}>
                                                /{subscription?.billing_interval || 'month'}
                                            </span>
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {!isStarterTier && (
                                <div style={{ marginTop: '12px', fontSize: '12px', color: '#6B7280' }}>
                                    Pricing: ${(subscription?.base_price_cents / 100).toFixed(2)} base +
                                    ${(subscription?.per_seat_price_cents / 100).toFixed(2)}/seat × {subscription?.seat_count} seats
                                </div>
                            )}
                        </div>
                    </div>

                    {subscription?.current_period_end && (
                        <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#EFF6FF', borderLeft: '4px solid #3B82F6', borderRadius: '6px' }}>
                            <span style={{ fontSize: '14px', color: '#1E40AF' }}>
                                ℹ️ Next billing date: {new Date(subscription.current_period_end).toLocaleDateString()}
                            </span>
                        </div>
                    )}
                </div>

                {/* Payment Method Card */}
                {subscription?.payment_mode === 'card' && subscription?.payment_method_info ? (
                    <div style={{
                        backgroundColor: 'white',
                        borderRadius: '12px',
                        padding: '24px',
                        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                        border: '1px solid #E5E7EB',
                        marginBottom: '24px'
                    }}>
                        <h3 style={{ margin: 0, marginBottom: '16px', fontSize: '18px', fontWeight: '600', color: '#111827' }}>Payment Method</h3>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                            <div style={{
                                width: '50px',
                                height: '32px',
                                border: '1px solid #E5E7EB',
                                borderRadius: '6px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                backgroundColor: '#F9FAFB'
                            }}>
                                <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase' }}>
                                    {subscription.payment_method_info.card_brand}
                                </span>
                            </div>
                            <div>
                                <div style={{ fontSize: '16px', color: '#111827' }}>
                                    •••• •••• •••• {subscription.payment_method_info.card_last4}
                                </div>
                                <div style={{ fontSize: '13px', color: '#6B7280' }}>
                                    Expires {subscription.payment_method_info.exp_month}/{subscription.payment_method_info.exp_year}
                                </div>
                            </div>
                        </div>
                        <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#EFF6FF', borderLeft: '4px solid #3B82F6', borderRadius: '6px' }}>
                            <span style={{ fontSize: '14px', color: '#1E40AF' }}>
                                ℹ️ Payment method is managed through Stripe. Contact support to update your card.
                            </span>
                        </div>
                    </div>
                ) : (
                    <div style={{
                        backgroundColor: 'white',
                        borderRadius: '12px',
                        padding: '24px',
                        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                        border: '1px solid #E5E7EB',
                        marginBottom: '24px'
                    }}>
                        <h3 style={{ margin: 0, marginBottom: '16px', fontSize: '18px', fontWeight: '600', color: '#111827' }}>Payment Method</h3>
                        <div style={{
                            padding: '24px',
                            backgroundColor: '#F9FAFB',
                            borderRadius: '8px',
                            border: '1px dashed #D1D5DB',
                            textAlign: 'center'
                        }}>
                            <div style={{ fontSize: '48px', marginBottom: '12px' }}>💳</div>
                            <div style={{ fontSize: '16px', fontWeight: '600', color: '#374151', marginBottom: '8px' }}>
                                No Payment Method Required
                            </div>
                            <div style={{ fontSize: '14px', color: '#6B7280', lineHeight: '1.5' }}>
                                {isStarterTier ? (
                                    <>You're on the free Starter plan. Upgrade to Professional or Enterprise to add a payment method.</>
                                ) : (
                                    <>Payment method information will appear here after you complete the checkout process.</>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* Billing Details Card */}
                <div style={{
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    padding: '24px',
                    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                    border: '1px solid #E5E7EB',
                    marginBottom: '24px'
                }}>
                    <h3 style={{ margin: 0, marginBottom: '16px', fontSize: '18px', fontWeight: '600', color: '#111827' }}>Billing Details</h3>
                    <form onSubmit={handleUpdateProfile}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
                            <div>
                                <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: '#374151' }}>Tax ID / EIN</label>
                                <input
                                    type="text"
                                    value={billingProfile.tax_id}
                                    onChange={(e) => setBillingProfile({ ...billingProfile, tax_id: e.target.value })}
                                    className="form-input"
                                    style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB' }}
                                />
                            </div>
                            <div>
                                <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: '#374151' }}>VAT Number</label>
                                <input
                                    type="text"
                                    value={billingProfile.vat_number}
                                    onChange={(e) => setBillingProfile({ ...billingProfile, vat_number: e.target.value })}
                                    style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB' }}
                                />
                            </div>
                        </div>
                        <div style={{ marginBottom: '20px' }}>
                            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: '#374151' }}>Billing Email</label>
                            <input
                                type="email"
                                value={billingProfile.billing_email}
                                onChange={(e) => setBillingProfile({ ...billingProfile, billing_email: e.target.value })}
                                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB' }}
                            />
                        </div>
                        <div style={{ marginBottom: '20px' }}>
                            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: '#374151' }}>Billing Address</label>
                            <textarea
                                value={billingProfile.billing_address}
                                onChange={(e) => setBillingProfile({ ...billingProfile, billing_address: e.target.value })}
                                rows="3"
                                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #D1D5DB' }}
                            />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                            <button
                                type="submit"
                                disabled={profileLoading}
                                style={{
                                    padding: '8px 16px',
                                    borderRadius: '6px',
                                    backgroundColor: '#4F46E5',
                                    color: 'white',
                                    border: 'none',
                                    fontWeight: '600',
                                    cursor: profileLoading ? 'not-allowed' : 'pointer',
                                    opacity: profileLoading ? 0.7 : 1
                                }}
                            >
                                {profileLoading ? 'Saving...' : 'Save Details'}
                            </button>
                        </div>
                    </form>
                </div>

                {/* Available Plans */}
                <h2 style={{ fontSize: '20px', fontWeight: '600', color: '#111827', marginBottom: '20px' }}>Available Plans</h2>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
                    {Object.entries(TIER_FEATURES).map(([tier, details]) => {
                        const isCurrent = tier === currentTier;
                        const canUpgrade = !isCurrent && tier !== 'starter' &&
                            (currentTier === 'starter' ||
                                (currentTier === 'professional' && tier === 'enterprise'));

                        return (
                            <div
                                key={tier}
                                style={{
                                    backgroundColor: 'white',
                                    borderRadius: '12px',
                                    padding: '24px',
                                    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                                    border: isCurrent ? `2px solid ${details.color}` : '1px solid #E5E7EB',
                                    position: 'relative',
                                    display: 'flex',
                                    flexDirection: 'column'
                                }}
                            >
                                {isCurrent && (
                                    <div style={{
                                        position: 'absolute',
                                        top: 0,
                                        right: 0,
                                        backgroundColor: details.color,
                                        color: 'white',
                                        padding: '6px 12px',
                                        borderBottomLeftRadius: '8px',
                                        fontSize: '12px',
                                        fontWeight: '600'
                                    }}>
                                        Current Plan
                                    </div>
                                )}

                                <h3 style={{ margin: 0, marginBottom: '8px', fontSize: '24px', fontWeight: '700', color: details.color }}>
                                    {details.name}
                                </h3>
                                <p style={{ margin: 0, marginBottom: '20px', fontSize: '14px', color: '#6B7280' }}>
                                    {details.description}
                                </p>

                                <div style={{ flex: 1, marginBottom: '20px' }}>
                                    {details.features.map((feature, idx) => (
                                        <div key={idx} style={{ marginBottom: '8px', fontSize: '14px', color: '#374151', display: 'flex', alignItems: 'start', gap: '8px' }}>
                                            <span style={{ color: '#10B981', fontSize: '16px' }}>✓</span>
                                            <span>{feature}</span>
                                        </div>
                                    ))}
                                </div>

                                {canUpgrade && (
                                    details.contactRequired ? (
                                        <button
                                            onClick={() => window.location.href = 'mailto:sales@enterprisesso.com'}
                                            style={{
                                                padding: '12px 20px',
                                                borderRadius: '8px',
                                                border: '1px solid ' + details.color,
                                                backgroundColor: 'white',
                                                color: details.color,
                                                fontSize: '14px',
                                                fontWeight: '600',
                                                cursor: 'pointer',
                                                transition: 'all 0.2s',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                gap: '8px'
                                            }}
                                            onMouseEnter={(e) => e.target.style.backgroundColor = details.color + '10'}
                                            onMouseLeave={(e) => e.target.style.backgroundColor = 'white'}
                                        >
                                            <span style={{ fontSize: '16px' }}>📞</span> Contact Sales
                                        </button>
                                    ) : (
                                        <button
                                            onClick={() => handleUpgradeClick(tier)}
                                            style={{
                                                padding: '12px 20px',
                                                borderRadius: '8px',
                                                border: 'none',
                                                backgroundColor: details.color,
                                                color: 'white',
                                                fontSize: '14px',
                                                fontWeight: '600',
                                                cursor: 'pointer',
                                                transition: 'all 0.2s'
                                            }}
                                            onMouseEnter={(e) => e.target.style.opacity = '0.9'}
                                            onMouseLeave={(e) => e.target.style.opacity = '1'}
                                        >
                                            🚀 Upgrade to {details.name}
                                        </button>
                                    )
                                )}

                                {isCurrent && (
                                    <div style={{
                                        padding: '12px 20px',
                                        border: `1px solid ${details.color}`,
                                        borderRadius: '8px',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        color: details.color,
                                        textAlign: 'center'
                                    }}>
                                        Current Plan
                                    </div>
                                )}

                                {tier === 'starter' && currentTier !== 'starter' && (
                                    <div style={{
                                        padding: '12px 20px',
                                        border: '1px solid #D1D5DB',
                                        borderRadius: '8px',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        color: '#9CA3AF',
                                        textAlign: 'center'
                                    }}>
                                        Cannot Downgrade
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* Upgrade Dialog */}
                {upgradeDialogOpen && (
                    <div style={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        backgroundColor: 'rgba(0, 0, 0, 0.5)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 1000
                    }}>
                        <div style={{
                            backgroundColor: 'white',
                            borderRadius: '12px',
                            padding: '32px',
                            maxWidth: '500px',
                            width: '90%'
                        }}>
                            <h2 style={{ margin: 0, marginBottom: '16px', fontSize: '24px', fontWeight: '700', color: '#111827' }}>
                                Upgrade to {selectedTier && TIER_FEATURES[selectedTier]?.name}
                            </h2>
                            <p style={{ margin: 0, marginBottom: '16px', fontSize: '16px', color: '#374151' }}>
                                Choose your billing interval:
                            </p>

                            <div style={{ marginBottom: '24px', padding: '16px', backgroundColor: '#F9FAFB', borderRadius: '8px' }}>
                                <p style={{ margin: 0, marginBottom: '4px', fontSize: '14px', color: '#374151' }}>
                                    Current seat count: {subscription?.seat_count} users
                                </p>
                                <p style={{ margin: 0, fontSize: '13px', color: '#6B7280' }}>
                                    Pricing will be calculated based on your active user count
                                </p>
                            </div>

                            <div style={{ marginBottom: '24px' }}>
                                <label style={{ display: 'block', fontSize: '13px', color: '#374151', marginBottom: '4px' }}>Coupon Code (Optional)</label>
                                <input
                                    type="text"
                                    value={couponCode}
                                    onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                                    placeholder="PROMO123"
                                    style={{
                                        width: '100%',
                                        padding: '8px 12px',
                                        borderRadius: '6px',
                                        border: '1px solid #D1D5DB',
                                        fontSize: '14px'
                                    }}
                                />
                            </div>

                            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                                <button
                                    onClick={() => !checkoutLoading && setUpgradeDialogOpen(false)}
                                    disabled={checkoutLoading}
                                    style={{
                                        padding: '12px 20px',
                                        borderRadius: '8px',
                                        border: '1px solid #D1D5DB',
                                        backgroundColor: 'white',
                                        color: '#374151',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        cursor: checkoutLoading ? 'not-allowed' : 'pointer',
                                        opacity: checkoutLoading ? 0.5 : 1
                                    }}
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={() => handleCheckout('monthly')}
                                    disabled={checkoutLoading}
                                    style={{
                                        padding: '12px 20px',
                                        borderRadius: '8px',
                                        border: 'none',
                                        backgroundColor: '#4F46E5',
                                        color: 'white',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        cursor: checkoutLoading ? 'not-allowed' : 'pointer',
                                        opacity: checkoutLoading ? 0.5 : 1
                                    }}
                                >
                                    {checkoutLoading ? '⏳ Processing...' : 'Monthly Billing'}
                                </button>
                                <button
                                    onClick={() => handleCheckout('yearly')}
                                    disabled={checkoutLoading}
                                    style={{
                                        padding: '12px 20px',
                                        borderRadius: '8px',
                                        border: 'none',
                                        backgroundColor: '#8B5CF6',
                                        color: 'white',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        cursor: checkoutLoading ? 'not-allowed' : 'pointer',
                                        opacity: checkoutLoading ? 0.5 : 1
                                    }}
                                >
                                    {checkoutLoading ? '⏳ Processing...' : 'Yearly Billing (Save 15%)'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </AdminLayout>
    );
};

export default SubscriptionSettingsPage;

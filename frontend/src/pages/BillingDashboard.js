import React, { useState, useEffect } from 'react';
import './BillingDashboard.css';

const BillingDashboard = () => {
    const [subscription, setSubscription] = useState(null);
    const [invoices, setInvoices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [canceling, setCanceling] = useState(false);

    useEffect(() => {
        fetchSubscriptionDetails();
        fetchInvoices();
    }, []);

    const fetchSubscriptionDetails = async () => {
        try {
            const token = localStorage.getItem('authToken');
            const workspaceId = localStorage.getItem('currentWorkspaceId');

            const response = await fetch(
                `http://localhost:8002/api/b2c/billing/subscription?workspace_id=${workspaceId}`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );

            if (response.ok) {
                const data = await response.json();
                setSubscription(data);
            } else if (response.status === 404) {
                // No subscription found - user is on free tier
                setSubscription({
                    tier: 'free',
                    status: 'active',
                });
            }
        } catch (error) {
            console.error('Error fetching subscription:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchInvoices = async () => {
        try {
            const token = localStorage.getItem('authToken');

            const response = await fetch('http://localhost:8002/api/b2c/billing/invoices?limit=10', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (response.ok) {
                const data = await response.json();
                setInvoices(data.invoices || []);
            }
        } catch (error) {
            console.error('Error fetching invoices:', error);
        }
    };

    const openCustomerPortal = async () => {
        try {
            const token = localStorage.getItem('authToken');

            const response = await fetch('http://localhost:8002/api/b2c/billing/portal', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    return_url: window.location.href,
                }),
            });

            if (response.ok) {
                const data = await response.json();
                window.location.href = data.portal_url;
            } else {
                alert('Failed to open customer portal');
            }
        } catch (error) {
            console.error('Error opening portal:', error);
            alert('Failed to open customer portal');
        }
    };

    const cancelSubscription = async (immediate = false) => {
        const confirmMessage = immediate
            ? 'Are you sure you want to cancel your subscription immediately? You will lose access to premium features right away.'
            : 'Are you sure you want to cancel your subscription? You will retain access until the end of your billing period.';

        if (!window.confirm(confirmMessage)) {
            return;
        }

        setCanceling(true);

        try {
            const token = localStorage.getItem('authToken');
            const workspaceId = localStorage.getItem('currentWorkspaceId');

            const response = await fetch(
                `http://localhost:8002/api/b2c/billing/subscription/cancel?workspace_id=${workspaceId}&immediate=${immediate}`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );

            if (response.ok) {
                alert('Subscription canceled successfully');
                fetchSubscriptionDetails();
            } else {
                const data = await response.json();
                alert(data.detail || 'Failed to cancel subscription');
            }
        } catch (error) {
            console.error('Error canceling subscription:', error);
            alert('Failed to cancel subscription');
        } finally {
            setCanceling(false);
        }
    };

    const downloadInvoice = (invoiceId) => {
        const token = localStorage.getItem('authToken');
        window.open(
            `http://localhost:8002/api/b2c/billing/invoices/${invoiceId}/download?token=${token}`,
            '_blank'
        );
    };

    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        });
    };

    const formatAmount = (cents, currency = 'USD') => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency,
        }).format(cents / 100);
    };

    const getStatusBadgeClass = (status) => {
        switch (status?.toLowerCase()) {
            case 'active':
            case 'trialing':
                return 'status-active';
            case 'past_due':
                return 'status-warning';
            case 'canceled':
            case 'incomplete':
            case 'unpaid':
                return 'status-error';
            default:
                return 'status-default';
        }
    };

    if (loading) {
        return (
            <div className="billing-dashboard">
                <div className="loading-spinner">Loading...</div>
            </div>
        );
    }

    const isFreeTier = subscription?.tier === 'free';
    const isPaidTier = !isFreeTier && subscription?.status === 'active';

    return (
        <div className="billing-dashboard">
            <div className="dashboard-header">
                <h1>Billing & Subscription</h1>
                <p>Manage your subscription, invoices, and payment methods</p>
            </div>

            {/* Current Plan */}
            <div className="section current-plan">
                <h2>Current Plan</h2>
                <div className="plan-card">
                    <div className="plan-info">
                        <div className="plan-tier">
                            <span className="tier-name">{subscription?.tier?.toUpperCase() || 'FREE'}</span>
                            <span className={`status-badge ${getStatusBadgeClass(subscription?.status)}`}>
                                {subscription?.status || 'Active'}
                            </span>
                        </div>

                        {isPaidTier && (
                            <>
                                <p className="plan-amount">
                                    {formatAmount(subscription.amount_cents, subscription.currency)}
                                    <span className="period">
                                        /{subscription.billing_interval === 'monthly' ? 'month' : 'year'}
                                    </span>
                                </p>
                                <p className="plan-dates">
                                    Current period: {formatDate(subscription.current_period_start)} - {formatDate(subscription.current_period_end)}
                                </p>
                                {subscription.cancel_at_period_end && (
                                    <p className="cancellation-notice">
                                        ⚠️ Your subscription will be canceled on {formatDate(subscription.current_period_end)}
                                    </p>
                                )}
                            </>
                        )}

                        {isFreeTier && (
                            <p className="free-tier-message">
                                You're currently on the free tier. <a href="/pricing">Upgrade now</a> to unlock premium features.
                            </p>
                        )}
                    </div>

                    <div className="plan-actions">
                        {isPaidTier && (
                            <>
                                <button className="btn btn-primary" onClick={openCustomerPortal}>
                                    Manage Payment Method
                                </button>
                                {!subscription.cancel_at_period_end && (
                                    <button
                                        className="btn btn-secondary"
                                        onClick={() => cancelSubscription(false)}
                                        disabled={canceling}
                                    >
                                        {canceling ? 'Canceling...' : 'Cancel Subscription'}
                                    </button>
                                )}
                            </>
                        )}
                        {isFreeTier && (
                            <a href="/pricing" className="btn btn-primary">
                                Upgrade Plan
                            </a>
                        )}
                    </div>
                </div>
            </div>

            {/* Usage & Limits */}
            <div className="section usage-limits">
                <h2>Usage & Limits</h2>
                <div className="limits-grid">
                    <div className="limit-card">
                        <div className="limit-header">
                            <span className="limit-label">Projects</span>
                            <span className="limit-value">
                                {subscription?.tier === 'free' ? '5' : 'Unlimited'}
                            </span>
                        </div>
                        <div className="limit-bar">
                            <div className="limit-progress" style={{ width: '40%' }}></div>
                        </div>
                        <p className="limit-subtext">2 of 5 used</p>
                    </div>

                    <div className="limit-card">
                        <div className="limit-header">
                            <span className="limit-label">Storage</span>
                            <span className="limit-value">
                                {subscription?.tier === 'free' ? '1 GB' : subscription?.tier === 'premium' ? '10 GB' : '100 GB'}
                            </span>
                        </div>
                        <div className="limit-bar">
                            <div className="limit-progress" style={{ width: '25%' }}></div>
                        </div>
                        <p className="limit-subtext">256 MB used</p>
                    </div>

                    <div className="limit-card">
                        <div className="limit-header">
                            <span className="limit-label">Team Members</span>
                            <span className="limit-value">
                                {subscription?.tier === 'free' ? '2' : subscription?.tier === 'premium' ? '10' : 'Unlimited'}
                            </span>
                        </div>
                        <div className="limit-bar">
                            <div className="limit-progress" style={{ width: '50%' }}></div>
                        </div>
                        <p className="limit-subtext">1 of 2 used</p>
                    </div>
                </div>
            </div>

            {/* Invoice History */}
            <div className="section invoices">
                <h2>Invoice History</h2>
                {invoices.length === 0 ? (
                    <p className="empty-state">No invoices yet</p>
                ) : (
                    <div className="invoice-table">
                        <table>
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Amount</th>
                                    <th>Status</th>
                                    <th>Invoice</th>
                                </tr>
                            </thead>
                            <tbody>
                                {invoices.map((invoice) => (
                                    <tr key={invoice.id}>
                                        <td>{formatDate(invoice.invoice_date)}</td>
                                        <td>{formatAmount(invoice.amount_paid, invoice.currency)}</td>
                                        <td>
                                            <span className={`status-badge ${getStatusBadgeClass(invoice.status)}`}>
                                                {invoice.status}
                                            </span>
                                        </td>
                                        <td>
                                            <button
                                                className="btn btn-link"
                                                onClick={() => downloadInvoice(invoice.id)}
                                            >
                                                Download PDF
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Quick Actions */}
            <div className="section quick-actions">
                <h2>Quick Actions</h2>
                <div className="actions-grid">
                    <button className="action-card" onClick={() => window.location.href = '/pricing'}>
                        <div className="action-icon">📊</div>
                        <h3>View Plans</h3>
                        <p>Compare pricing tiers</p>
                    </button>

                    {isPaidTier && (
                        <button className="action-card" onClick={openCustomerPortal}>
                            <div className="action-icon">💳</div>
                            <h3>Update Payment</h3>
                            <p>Manage payment methods</p>
                        </button>
                    )}

                    <button className="action-card" onClick={() => alert('Contact support')}>
                        <div className="action-icon">💬</div>
                        <h3>Contact Support</h3>
                        <p>Get help with billing</p>
                    </button>
                </div>
            </div>
        </div>
    );
};

export default BillingDashboard;

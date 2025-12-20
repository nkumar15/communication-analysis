import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth } from '../../../../core/firebase/b2c-config';
import B2CLayout from '../layouts/B2CLayout';

const BillingHistoryPage = () => {
    const navigate = useNavigate();
    const [invoices, setInvoices] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadInvoices();
    }, []);

    const loadInvoices = async () => {
        setLoading(true);
        try {
            const user = auth.currentUser;
            if (!user) {
                navigate('/login');
                return;
            }

            const token = await user.getIdToken();
            const response = await fetch('/api/b2c/billing/invoices?limit=50', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                setInvoices(data.invoices || []);
            }
        } catch (error) {
            console.error('Failed to load invoices:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = async (invoiceId) => {
        try {
            const user = auth.currentUser;
            const token = await user.getIdToken();

            const response = await fetch(`/api/b2c/billing/invoices/${invoiceId}/download`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                // Open PDF in new tab
                window.open(data.url || data.invoice_pdf_url, '_blank');
            }
        } catch (error) {
            console.error('Failed to download invoice:', error);
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'paid': return '#10B981';
            case 'open': return '#F59E0B';
            case 'void': return '#6B7280';
            case 'uncollectible': return '#EF4444';
            default: return '#6B7280';
        }
    };

    const getStatusLabel = (status) => {
        return status.charAt(0).toUpperCase() + status.slice(1);
    };

    const formatCurrency = (cents, currency = 'USD') => {
        const amount = cents / 100;
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(amount);
    };

    const formatDate = (dateString) => {
        if (!dateString) return '-';
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    if (loading) {
        return (
            <B2CLayout>
                <div style={{ textAlign: 'center', padding: '60px' }}>
                    <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</div>
                    <p>Loading invoices...</p>
                </div>
            </B2CLayout>
        );
    }

    return (
        <B2CLayout>
            <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
                {/* Header */}
                <div style={{ marginBottom: '32px' }}>
                    <h1 style={{
                        fontSize: '32px',
                        fontWeight: '700',
                        color: '#111827',
                        marginBottom: '8px'
                    }}>
                        Billing History
                    </h1>
                    <p style={{
                        fontSize: '16px',
                        color: '#6B7280'
                    }}>
                        View and download your invoices
                    </p>
                </div>

                {/* Invoices Table */}
                {invoices.length > 0 ? (
                    <div style={{
                        backgroundColor: 'white',
                        borderRadius: '12px',
                        border: '1px solid #E5E7EB',
                        overflow: 'hidden'
                    }}>
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{
                                width: '100%',
                                borderCollapse: 'collapse'
                            }}>
                                <thead>
                                    <tr style={{
                                        backgroundColor: '#F9FAFB',
                                        borderBottom: '2px solid #E5E7EB'
                                    }}>
                                        <th style={{
                                            padding: '16px 20px',
                                            textAlign: 'left',
                                            fontSize: '13px',
                                            fontWeight: '600',
                                            color: '#6B7280',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.5px'
                                        }}>
                                            Date
                                        </th>
                                        <th style={{
                                            padding: '16px 20px',
                                            textAlign: 'left',
                                            fontSize: '13px',
                                            fontWeight: '600',
                                            color: '#6B7280',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.5px'
                                        }}>
                                            Invoice ID
                                        </th>
                                        <th style={{
                                            padding: '16px 20px',
                                            textAlign: 'left',
                                            fontSize: '13px',
                                            fontWeight: '600',
                                            color: '#6B7280',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.5px'
                                        }}>
                                            Amount
                                        </th>
                                        <th style={{
                                            padding: '16px 20px',
                                            textAlign: 'left',
                                            fontSize: '13px',
                                            fontWeight: '600',
                                            color: '#6B7280',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.5px'
                                        }}>
                                            Status
                                        </th>
                                        <th style={{
                                            padding: '16px 20px',
                                            textAlign: 'right',
                                            fontSize: '13px',
                                            fontWeight: '600',
                                            color: '#6B7280',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.5px'
                                        }}>
                                            Actions
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {invoices.map((invoice) => (
                                        <tr
                                            key={invoice.id}
                                            style={{
                                                borderBottom: '1px solid #F3F4F6'
                                            }}
                                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#F9FAFB'}
                                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}
                                        >
                                            <td style={{
                                                padding: '20px',
                                                fontSize: '14px',
                                                color: '#374151'
                                            }}>
                                                {formatDate(invoice.invoice_date || invoice.created_at)}
                                            </td>
                                            <td style={{
                                                padding: '20px',
                                                fontSize: '14px',
                                                color: '#6B7280',
                                                fontFamily: 'monospace'
                                            }}>
                                                {invoice.id.substring(0, 12)}...
                                            </td>
                                            <td style={{
                                                padding: '20px',
                                                fontSize: '15px',
                                                fontWeight: '600',
                                                color: '#111827'
                                            }}>
                                                {formatCurrency(invoice.amount_paid || invoice.amount_due, invoice.currency)}
                                            </td>
                                            <td style={{ padding: '20px' }}>
                                                <span style={{
                                                    padding: '4px 12px',
                                                    borderRadius: '9999px',
                                                    fontSize: '12px',
                                                    fontWeight: '600',
                                                    backgroundColor: `${getStatusColor(invoice.status)}20`,
                                                    color: getStatusColor(invoice.status),
                                                    textTransform: 'capitalize'
                                                }}>
                                                    {getStatusLabel(invoice.status)}
                                                </span>
                                            </td>
                                            <td style={{
                                                padding: '20px',
                                                textAlign: 'right'
                                            }}>
                                                <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                                                    {invoice.hosted_invoice_url && (
                                                        <a
                                                            href={invoice.hosted_invoice_url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            style={{
                                                                padding: '8px 16px',
                                                                borderRadius: '6px',
                                                                border: '1px solid #E5E7EB',
                                                                backgroundColor: 'white',
                                                                color: '#6366F1',
                                                                fontSize: '13px',
                                                                fontWeight: '500',
                                                                textDecoration: 'none',
                                                                cursor: 'pointer'
                                                            }}
                                                        >
                                                            View
                                                        </a>
                                                    )}
                                                    {invoice.invoice_pdf_url && (
                                                        <button
                                                            onClick={() => handleDownload(invoice.id)}
                                                            style={{
                                                                padding: '8px 16px',
                                                                borderRadius: '6px',
                                                                border: '1px solid #6366F1',
                                                                backgroundColor: '#6366F1',
                                                                color: 'white',
                                                                fontSize: '13px',
                                                                fontWeight: '500',
                                                                cursor: 'pointer'
                                                            }}
                                                        >
                                                            Download PDF
                                                        </button>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                ) : (
                    <div style={{
                        backgroundColor: 'white',
                        borderRadius: '12px',
                        padding: '60px 24px',
                        border: '1px solid #E5E7EB',
                        textAlign: 'center'
                    }}>
                        <div style={{ fontSize: '64px', marginBottom: '16px', opacity: 0.8 }}>
                            🧾
                        </div>
                        <h3 style={{
                            fontSize: '20px',
                            fontWeight: '600',
                            color: '#111827',
                            marginBottom: '8px'
                        }}>
                            No invoices yet
                        </h3>
                        <p style={{
                            fontSize: '14px',
                            color: '#6B7280',
                            marginBottom: '24px'
                        }}>
                            Invoices will appear here when you have an active subscription
                        </p>
                        <button
                            onClick={() => navigate('/subscription')}
                            style={{
                                padding: '12px 24px',
                                borderRadius: '8px',
                                border: 'none',
                                backgroundColor: '#6366F1',
                                color: 'white',
                                fontSize: '14px',
                                fontWeight: '600',
                                cursor: 'pointer'
                            }}
                        >
                            Explore Plans
                        </button>
                    </div>
                )}

                {/* Summary Card */}
                {invoices.length > 0 && (
                    <div style={{
                        backgroundColor: 'white',
                        borderRadius: '12px',
                        padding: '24px',
                        border: '1px solid #E5E7EB',
                        marginTop: '24px'
                    }}>
                        <h3 style={{
                            fontSize: '16px',
                            fontWeight: '600',
                            color: '#111827',
                            marginBottom: '16px'
                        }}>
                            Summary
                        </h3>
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                            gap: '16px'
                        }}>
                            <div>
                                <div style={{ fontSize: '13px', color: '#6B7280', marginBottom: '4px' }}>
                                    Total Invoices
                                </div>
                                <div style={{ fontSize: '24px', fontWeight: '700', color: '#111827' }}>
                                    {invoices.length}
                                </div>
                            </div>
                            <div>
                                <div style={{ fontSize: '13px', color: '#6B7280', marginBottom: '4px' }}>
                                    Total Paid
                                </div>
                                <div style={{ fontSize: '24px', fontWeight: '700', color: '#10B981' }}>
                                    {formatCurrency(
                                        invoices
                                            .filter(i => i.status === 'paid')
                                            .reduce((sum, i) => sum + (i.amount_paid || 0), 0)
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </B2CLayout>
    );
};

export default BillingHistoryPage;

import { useState, useEffect } from 'react';
import platformApiService from '../../../../core/api/platformClient';
import { useProduct } from '../layouts/SuperAdminLayout';
import '../styles/platform.css';

function BillingCouponsPage() {
    const { selectedProduct } = useProduct(); // Use global product selector
    const [coupons, setCoupons] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [showCreateForm, setShowCreateForm] = useState(false);

    // Form State
    const [newCoupon, setNewCoupon] = useState({
        code: '',
        discount_type: 'percentage',
        discount_percent: '',
        discount_amount_cents: '',
        max_redemptions: '',
        valid_until: '',
        description: ''
    });

    useEffect(() => {
        fetchCoupons();
    }, [selectedProduct]); // Refetch when product selection changes

    const fetchCoupons = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await platformApiService.getCoupons(selectedProduct);
            setCoupons(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateCoupon = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const payload = {
                code: newCoupon.code,
                discount_type: newCoupon.discount_type,
                discount_percent: newCoupon.discount_type === 'percentage' ? parseInt(newCoupon.discount_percent) : null,
                discount_amount_cents: newCoupon.discount_type === 'fixed_amount' ? parseInt(newCoupon.discount_amount_cents) : null,
                currency: 'USD', // Default
                max_redemptions: newCoupon.max_redemptions ? parseInt(newCoupon.max_redemptions) : null,
                valid_until: newCoupon.valid_until ? new Date(newCoupon.valid_until).toISOString() : null,
                description: newCoupon.description
            };

            await platformApiService.createCoupon(payload, selectedProduct);
            setShowCreateForm(false);
            setNewCoupon({
                code: '',
                discount_type: 'percentage',
                discount_percent: '',
                discount_amount_cents: '',
                max_redemptions: '',
                valid_until: '',
                description: ''
            });
            fetchCoupons(); // Refresh
        } catch (err) {
            alert("Failed to create coupon: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="platform-page">
            <div className="platform-page-header">
                <div>
                    <h1 className="platform-page-title">Coupons</h1>
                    <p className="platform-page-subtitle">Manage promotional codes for {selectedProduct.toUpperCase()}</p>
                </div>
                <button
                    className="platform-btn platform-btn-primary"
                    onClick={() => setShowCreateForm(!showCreateForm)}
                >
                    + Create Coupon
                </button>
            </div>


            {/* Create Form Modal */}
            {showCreateForm && (
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
                    zIndex: 1000,
                    padding: '20px'
                }}>
                    <div style={{
                        width: '100%',
                        maxWidth: '600px',
                        backgroundColor: '#FFFFFF',
                        borderRadius: '16px',
                        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                        overflow: 'hidden'
                    }}>
                        {/* Header */}
                        <div style={{
                            background: 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)',
                            padding: '24px',
                            color: 'white'
                        }}>
                            <h2 style={{
                                margin: 0,
                                fontSize: '24px',
                                fontWeight: '700',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '10px'
                            }}>
                                <span style={{ fontSize: '28px' }}>🎟️</span>
                                Create New {selectedProduct.toUpperCase()} Coupon
                            </h2>
                            <p style={{
                                margin: '8px 0 0 0',
                                fontSize: '14px',
                                opacity: 0.9
                            }}>
                                Create a promotional code for {selectedProduct.toUpperCase()} subscriptions
                            </p>
                        </div>

                        {/* Form */}
                        <form onSubmit={handleCreateCoupon} style={{ padding: '28px' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
                                <div>
                                    <label style={{
                                        display: 'block',
                                        marginBottom: '8px',
                                        fontWeight: '600',
                                        fontSize: '14px',
                                        color: '#374151'
                                    }}>
                                        Coupon Code <span style={{ color: '#EF4444' }}>*</span>
                                    </label>
                                    <input
                                        type="text" required
                                        value={newCoupon.code}
                                        onChange={(e) => setNewCoupon({ ...newCoupon, code: e.target.value.toUpperCase() })}
                                        placeholder="e.g. WELCOME20"
                                        style={{
                                            width: '100%',
                                            padding: '12px 16px',
                                            border: '2px solid #E5E7EB',
                                            borderRadius: '8px',
                                            fontSize: '14px',
                                            backgroundColor: '#F9FAFB',
                                            color: '#111827',
                                            outline: 'none'
                                        }}
                                        onFocus={(e) => {
                                            e.target.style.borderColor = '#6366F1';
                                            e.target.style.backgroundColor = 'white';
                                        }}
                                        onBlur={(e) => {
                                            e.target.style.borderColor = '#E5E7EB';
                                            e.target.style.backgroundColor = '#F9FAFB';
                                        }}
                                    />
                                </div>
                                <div>
                                    <label style={{
                                        display: 'block',
                                        marginBottom: '8px',
                                        fontWeight: '600',
                                        fontSize: '14px',
                                        color: '#374151'
                                    }}>
                                        Description
                                    </label>
                                    <input
                                        type="text"
                                        value={newCoupon.description}
                                        onChange={(e) => setNewCoupon({ ...newCoupon, description: e.target.value })}
                                        placeholder="Internal note"
                                        style={{
                                            width: '100%',
                                            padding: '12px 16px',
                                            border: '2px solid #E5E7EB',
                                            borderRadius: '8px',
                                            fontSize: '14px',
                                            backgroundColor: '#F9FAFB',
                                            color: '#111827',
                                            outline: 'none'
                                        }}
                                        onFocus={(e) => {
                                            e.target.style.borderColor = '#6366F1';
                                            e.target.style.backgroundColor = 'white';
                                        }}
                                        onBlur={(e) => {
                                            e.target.style.borderColor = '#E5E7EB';
                                            e.target.style.backgroundColor = '#F9FAFB';
                                        }}
                                    />
                                </div>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginBottom: '20px' }}>
                                <div>
                                    <label style={{
                                        display: 'block',
                                        marginBottom: '8px',
                                        fontWeight: '600',
                                        fontSize: '14px',
                                        color: '#374151'
                                    }}>
                                        Discount Type
                                    </label>
                                    <select
                                        value={newCoupon.discount_type}
                                        onChange={(e) => setNewCoupon({ ...newCoupon, discount_type: e.target.value })}
                                        style={{
                                            width: '100%',
                                            padding: '12px 16px',
                                            border: '2px solid #E5E7EB',
                                            borderRadius: '8px',
                                            fontSize: '14px',
                                            backgroundColor: '#F9FAFB',
                                            color: '#111827',
                                            outline: 'none'
                                        }}
                                        onFocus={(e) => {
                                            e.target.style.borderColor = '#6366F1';
                                            e.target.style.backgroundColor = 'white';
                                        }}
                                        onBlur={(e) => {
                                            e.target.style.borderColor = '#E5E7EB';
                                            e.target.style.backgroundColor = '#F9FAFB';
                                        }}
                                    >
                                        <option value="percentage">Percentage Off</option>
                                        <option value="fixed_amount">Fixed Amount Off</option>
                                    </select>
                                </div>
                                {newCoupon.discount_type === 'percentage' ? (
                                    <div>
                                        <label style={{
                                            display: 'block',
                                            marginBottom: '8px',
                                            fontWeight: '600',
                                            fontSize: '14px',
                                            color: '#374151'
                                        }}>
                                            Percentage (%) <span style={{ color: '#EF4444' }}>*</span>
                                        </label>
                                        <input
                                            type="number" required min="1" max="100"
                                            value={newCoupon.discount_percent}
                                            onChange={(e) => setNewCoupon({ ...newCoupon, discount_percent: e.target.value })}
                                            style={{
                                                width: '100%',
                                                padding: '12px 16px',
                                                border: '2px solid #E5E7EB',
                                                borderRadius: '8px',
                                                fontSize: '14px',
                                                backgroundColor: '#F9FAFB',
                                                color: '#111827',
                                                outline: 'none'
                                            }}
                                            onFocus={(e) => {
                                                e.target.style.borderColor = '#6366F1';
                                                e.target.style.backgroundColor = 'white';
                                            }}
                                            onBlur={(e) => {
                                                e.target.style.borderColor = '#E5E7EB';
                                                e.target.style.backgroundColor = '#F9FAFB';
                                            }}
                                        />
                                    </div>
                                ) : (
                                    <div>
                                        <label style={{
                                            display: 'block',
                                            marginBottom: '8px',
                                            fontWeight: '600',
                                            fontSize: '14px',
                                            color: '#374151'
                                        }}>
                                            Amount (Cents) <span style={{ color: '#EF4444' }}>*</span>
                                        </label>
                                        <input
                                            type="number" required min="1"
                                            value={newCoupon.discount_amount_cents}
                                            onChange={(e) => setNewCoupon({ ...newCoupon, discount_amount_cents: e.target.value })}
                                            placeholder="e.g. 1000 for $10"
                                            style={{
                                                width: '100%',
                                                padding: '12px 16px',
                                                border: '2px solid #E5E7EB',
                                                borderRadius: '8px',
                                                fontSize: '14px',
                                                backgroundColor: '#F9FAFB',
                                                color: '#111827',
                                                outline: 'none'
                                            }}
                                            onFocus={(e) => {
                                                e.target.style.borderColor = '#6366F1';
                                                e.target.style.backgroundColor = 'white';
                                            }}
                                            onBlur={(e) => {
                                                e.target.style.borderColor = '#E5E7EB';
                                                e.target.style.backgroundColor = '#F9FAFB';
                                            }}
                                        />
                                    </div>
                                )}
                                <div>
                                    <label style={{
                                        display: 'block',
                                        marginBottom: '8px',
                                        fontWeight: '600',
                                        fontSize: '14px',
                                        color: '#374151'
                                    }}>
                                        Max Redemptions
                                    </label>
                                    <input
                                        type="number" min="1"
                                        value={newCoupon.max_redemptions}
                                        onChange={(e) => setNewCoupon({ ...newCoupon, max_redemptions: e.target.value })}
                                        placeholder="Optional"
                                        style={{
                                            width: '100%',
                                            padding: '12px 16px',
                                            border: '2px solid #E5E7EB',
                                            borderRadius: '8px',
                                            fontSize: '14px',
                                            backgroundColor: '#F9FAFB',
                                            color: '#111827',
                                            outline: 'none'
                                        }}
                                        onFocus={(e) => {
                                            e.target.style.borderColor = '#6366F1';
                                            e.target.style.backgroundColor = 'white';
                                        }}
                                        onBlur={(e) => {
                                            e.target.style.borderColor = '#E5E7EB';
                                            e.target.style.backgroundColor = '#F9FAFB';
                                        }}
                                    />
                                </div>
                            </div>

                            <div style={{ marginBottom: '28px' }}>
                                <label style={{
                                    display: 'block',
                                    marginBottom: '8px',
                                    fontWeight: '600',
                                    fontSize: '14px',
                                    color: '#374151'
                                }}>
                                    Valid Until
                                </label>
                                <input
                                    type="date"
                                    value={newCoupon.valid_until}
                                    onChange={(e) => setNewCoupon({ ...newCoupon, valid_until: e.target.value })}
                                    style={{
                                        width: '50%',
                                        padding: '12px 16px',
                                        border: '2px solid #E5E7EB',
                                        borderRadius: '8px',
                                        fontSize: '14px',
                                        backgroundColor: '#F9FAFB',
                                        color: '#111827',
                                        outline: 'none'
                                    }}
                                    onFocus={(e) => {
                                        e.target.style.borderColor = '#6366F1';
                                        e.target.style.backgroundColor = 'white';
                                    }}
                                    onBlur={(e) => {
                                        e.target.style.borderColor = '#E5E7EB';
                                        e.target.style.backgroundColor = '#F9FAFB';
                                    }}
                                />
                            </div>

                            {/* Actions */}
                            <div style={{
                                display: 'flex',
                                gap: '12px',
                                justifyContent: 'flex-end'
                            }}>
                                <button
                                    type="button"
                                    onClick={() => setShowCreateForm(false)}
                                    style={{
                                        padding: '12px 24px',
                                        borderRadius: '8px',
                                        border: '2px solid #E5E7EB',
                                        background: 'white',
                                        color: '#374151',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        cursor: 'pointer'
                                    }}
                                    onMouseEnter={(e) => e.target.style.background = '#F3F4F6'}
                                    onMouseLeave={(e) => e.target.style.background = 'white'}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={loading}
                                    style={{
                                        padding: '12px 28px',
                                        borderRadius: '8px',
                                        border: 'none',
                                        background: loading ? '#9CA3AF' : 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)',
                                        color: 'white',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        cursor: loading ? 'not-allowed' : 'pointer',
                                        boxShadow: loading ? 'none' : '0 4px 12px rgba(99, 102, 241, 0.4)'
                                    }}
                                >
                                    {loading ? '⏳ Creating...' : '🎟️ Create Coupon'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Coupons List */}
            <div className="platform-card">
                {error && <p className="text-red-400 mb-4">{error}</p>}
                {loading && !coupons.length && <p>Loading...</p>}

                <div className="platform-table-container">
                    <table className="platform-table">
                        <thead>
                            <tr>
                                <th>Code</th>
                                <th>Discount</th>
                                <th>Redeemed</th>
                                <th>Active</th>
                                <th>Provider ID</th>
                            </tr>
                        </thead>
                        <tbody>
                            {coupons.length === 0 && !loading && (
                                <tr>
                                    <td colSpan="5" className="text-center text-gray-500 py-4">No coupons found</td>
                                </tr>
                            )}
                            {coupons.map(coupon => (
                                <tr key={coupon.id}>
                                    <td className="font-mono font-bold text-white">{coupon.code}</td>
                                    <td>
                                        {coupon.discount_type === 'percentage'
                                            ? `${coupon.discount_percent}%`
                                            : `$${(coupon.discount_amount_cents / 100).toFixed(2)}`}
                                    </td>
                                    <td>{coupon.times_redeemed}</td>
                                    <td>
                                        <span className={`px-2 py-1 rounded text-xs ${coupon.is_active ? 'bg-green-900 text-green-200' : 'bg-red-900 text-red-200'}`}>
                                            {coupon.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </td>
                                    <td className="font-mono text-xs text-gray-500">{coupon.provider_coupon_id || '-'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

export default BillingCouponsPage;

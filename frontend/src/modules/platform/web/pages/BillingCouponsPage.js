import { useState, useEffect } from 'react';
import platformApiService from '../../../../core/api/platformClient';
import '../styles/platform.css';

function BillingCouponsPage() {
    const [activeTab, setActiveTab] = useState('b2b'); // 'b2b' or 'b2c'
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
    }, [activeTab]);

    const fetchCoupons = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await platformApiService.getCoupons(activeTab);
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

            await platformApiService.createCoupon(payload, activeTab);
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
                    <p className="platform-page-subtitle">Manage promotional codes for {activeTab.toUpperCase()}</p>
                </div>
                <button
                    className="platform-btn platform-btn-primary"
                    onClick={() => setShowCreateForm(!showCreateForm)}
                >
                    + Create Coupon
                </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-gray-700 mb-6">
                <button
                    className={`px-4 py-2 font-medium text-sm ${activeTab === 'b2b' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-gray-400 hover:text-white'}`}
                    onClick={() => setActiveTab('b2b')}
                >
                    B2B Coupons
                </button>
                <button
                    className={`px-4 py-2 font-medium text-sm ${activeTab === 'b2c' ? 'text-green-400 border-b-2 border-green-400' : 'text-gray-400 hover:text-white'}`}
                    onClick={() => setActiveTab('b2c')}
                >
                    B2C Coupons
                </button>
            </div>

            {/* Create Form */}
            {showCreateForm && (
                <div className="platform-card mb-6 border border-gray-600">
                    <h3 className="text-lg font-semibold mb-4">Create New {activeTab.toUpperCase()} Coupon</h3>
                    <form onSubmit={handleCreateCoupon} className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs text-gray-400 mb-1">Coupon Code</label>
                                <input
                                    type="text" required
                                    className="platform-input w-full"
                                    placeholder="e.g. WELCOME20"
                                    value={newCoupon.code}
                                    onChange={(e) => setNewCoupon({ ...newCoupon, code: e.target.value.toUpperCase() })}
                                />
                            </div>
                            <div>
                                <label className="block text-xs text-gray-400 mb-1">Description</label>
                                <input
                                    type="text"
                                    className="platform-input w-full"
                                    placeholder="Internal note"
                                    value={newCoupon.description}
                                    onChange={(e) => setNewCoupon({ ...newCoupon, description: e.target.value })}
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-3 gap-4">
                            <div>
                                <label className="block text-xs text-gray-400 mb-1">Type</label>
                                <select
                                    className="platform-select w-full"
                                    value={newCoupon.discount_type}
                                    onChange={(e) => setNewCoupon({ ...newCoupon, discount_type: e.target.value })}
                                >
                                    <option value="percentage">Percentage Off</option>
                                    <option value="fixed_amount">Fixed Amount Off</option>
                                </select>
                            </div>
                            {newCoupon.discount_type === 'percentage' ? (
                                <div>
                                    <label className="block text-xs text-gray-400 mb-1">Percentage (%)</label>
                                    <input
                                        type="number" required min="1" max="100"
                                        className="platform-input w-full"
                                        value={newCoupon.discount_percent}
                                        onChange={(e) => setNewCoupon({ ...newCoupon, discount_percent: e.target.value })}
                                    />
                                </div>
                            ) : (
                                <div>
                                    <label className="block text-xs text-gray-400 mb-1">Amount (Cents)</label>
                                    <input
                                        type="number" required min="1"
                                        className="platform-input w-full"
                                        placeholder="e.g. 1000 for $10"
                                        value={newCoupon.discount_amount_cents}
                                        onChange={(e) => setNewCoupon({ ...newCoupon, discount_amount_cents: e.target.value })}
                                    />
                                </div>
                            )}
                            <div>
                                <label className="block text-xs text-gray-400 mb-1">Max Redemptions (Optional)</label>
                                <input
                                    type="number" min="1"
                                    className="platform-input w-full"
                                    value={newCoupon.max_redemptions}
                                    onChange={(e) => setNewCoupon({ ...newCoupon, max_redemptions: e.target.value })}
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs text-gray-400 mb-1">Valid Until (Optional)</label>
                                <input
                                    type="date"
                                    className="platform-input w-full"
                                    value={newCoupon.valid_until}
                                    onChange={(e) => setNewCoupon({ ...newCoupon, valid_until: e.target.value })}
                                />
                            </div>
                        </div>

                        <div className="flex justify-end gap-2 pt-2">
                            <button
                                type="button"
                                className="platform-btn platform-btn-secondary"
                                onClick={() => setShowCreateForm(false)}
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                className="platform-btn platform-btn-primary"
                                disabled={loading}
                            >
                                {loading ? 'Creating...' : 'Create Coupon'}
                            </button>
                        </div>
                    </form>
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

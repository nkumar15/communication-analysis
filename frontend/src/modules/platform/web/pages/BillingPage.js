import { useState } from 'react';
import platformApiService from '../../../../core/api/platformClient';
import '../styles/platform.css';

function BillingPage() {
    const [searchQuery, setSearchQuery] = useState('');
    const [searchType, setSearchType] = useState(''); // 'tenant' or 'user' or ''
    const [searchResults, setSearchResults] = useState([]);
    const [selectedProfile, setSelectedProfile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [actionLoading, setActionLoading] = useState(false);

    // Search
    const handleSearch = async (e) => {
        e.preventDefault();
        if (!searchQuery.trim()) return;

        setLoading(true);
        setError(null);
        setSelectedProfile(null);
        try {
            const response = await platformApiService.searchBillingProfiles(searchQuery, searchType || undefined);
            setSearchResults(response.items || []);
        } catch (err) {
            console.error(err);
            setError('Failed to search profiles');
        } finally {
            setLoading(false);
        }
    };

    // Select Profile & Fetch Details
    const handleSelectProfile = async (item) => {
        setLoading(true);
        setError(null);
        try {
            const details = await platformApiService.getBillingProfile(item.id, item.type);
            setSelectedProfile(details);
            setSearchResults([]); // Clear results or keep them? Clear for cleaner view
        } catch (err) {
            console.error(err);
            setError('Failed to fetch profile details');
        } finally {
            setLoading(false);
        }
    };

    // Actions
    const handleCancelSubscription = async () => {
        if (!selectedProfile?.subscription?.id) return;
        if (!window.confirm("Are you sure you want to cancel this subscription?")) return;

        setActionLoading(true);
        try {
            await platformApiService.cancelSubscription(
                selectedProfile.subscription.id,
                selectedProfile.type,
                "Admin cancelled via console",
                false // immediate? Let's assume standard cancel for now or ask.
            );
            alert("Subscription cancelled.");
            // Refresh
            handleSelectProfile({ id: selectedProfile.id, type: selectedProfile.type });
        } catch (err) {
            alert("Failed to cancel: " + err.message);
        } finally {
            setActionLoading(false);
        }
    };

    const handleExtendTrial = async () => {
        const days = prompt("Enter days to extend trial:", "14");
        if (!days) return;

        setActionLoading(true);
        try {
            await platformApiService.extendTrial(
                selectedProfile.subscription.id,
                selectedProfile.type,
                parseInt(days)
            );
            alert("Trial extended.");
            // Refresh
            handleSelectProfile({ id: selectedProfile.id, type: selectedProfile.type });
        } catch (err) {
            alert("Failed to extend trial: " + err.message);
        } finally {
            setActionLoading(false);
        }
    };

    return (
        <div className="platform-page">
            <div className="platform-page-header">
                <div>
                    <h1 className="platform-page-title">Billing & Revenue</h1>
                    <p className="platform-page-subtitle">Manage subscriptions, invoices, and billing profiles</p>
                </div>
            </div>

            {/* Search Section */}
            <div className="platform-card" style={{ marginBottom: '2rem' }}>
                <form onSubmit={handleSearch} style={{ display: 'flex', gap: '1rem' }}>
                    <input
                        type="text"
                        className="platform-input"
                        placeholder="Search by name, email, or domain..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        style={{ flex: 1 }}
                    />
                    <select
                        className="platform-select"
                        value={searchType}
                        onChange={(e) => setSearchType(e.target.value)}
                        style={{ width: '150px' }}
                    >
                        <option value="">All Types</option>
                        <option value="tenant">B2B Tenants</option>
                        <option value="user">B2C Users</option>
                    </select>
                    <button type="submit" className="platform-btn platform-btn-primary" disabled={loading}>
                        {loading ? 'Searching...' : 'Search'}
                    </button>
                </form>
            </div>

            {error && <div className="platform-alert-error" style={{ marginBottom: '1rem' }}>{error}</div>}

            {/* Search Results */}
            {searchResults.length > 0 && (
                <div className="platform-card">
                    <h3 className="text-lg font-semibold mb-4">Search Results</h3>
                    <div className="platform-table-container">
                        <table className="platform-table">
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Type</th>
                                    <th>Detail</th>
                                    <th>Status</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {searchResults.map((item) => (
                                    <tr key={item.id}>
                                        <td>
                                            <div className="font-medium">{item.name}</div>
                                            <div className="text-xs text-gray-500">{item.email || item.domain}</div>
                                        </td>
                                        <td>
                                            <span className={`px-2 py-1 rounded text-xs ${item.type === 'tenant' ? 'bg-blue-900 text-blue-200' : 'bg-green-900 text-green-200'}`}>
                                                {item.type.toUpperCase()}
                                            </span>
                                        </td>
                                        <td>{item.email || item.domain}</td>
                                        <td>{item.status}</td>
                                        <td>
                                            <button
                                                className="platform-btn platform-btn-sm platform-btn-secondary"
                                                onClick={() => handleSelectProfile(item)}
                                            >
                                                View Profile
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Profile Detail View */}
            {selectedProfile && (
                <div className="platform-card">
                    <div className="flex justify-between items-start mb-6">
                        <div>
                            <h2 className="text-xl font-bold">{selectedProfile.name}</h2>
                            <p className="text-gray-400">{selectedProfile.type === 'tenant' ? '🏢 Tenant' : '👤 User'} • {selectedProfile.email}</p>
                            {selectedProfile.tax_id && <p className="text-xs text-gray-500 mt-1">Tax ID: {selectedProfile.tax_id}</p>}
                        </div>
                        <button onClick={() => setSelectedProfile(null)} className="text-gray-400 hover:text-white">✕ Close</button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Subscription Card */}
                        <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
                            <h3 className="font-semibold mb-3 border-b border-gray-700 pb-2">Subscription</h3>
                            {selectedProfile.subscription ? (
                                <div className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-gray-400">Status:</span>
                                        <span className={`px-2 py-0.5 rounded text-xs ${selectedProfile.subscription.status === 'active' ? 'bg-green-900 text-green-200' : 'bg-gray-700'}`}>
                                            {selectedProfile.subscription.status?.toUpperCase()}
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-400">Plan:</span>
                                        <span>{selectedProfile.subscription.tier} ({selectedProfile.subscription.billing_interval})</span>
                                    </div>
                                    {selectedProfile.subscription.amount_cents > 0 && (
                                        <div className="flex justify-between">
                                            <span className="text-gray-400">Amount:</span>
                                            <span>{(selectedProfile.subscription.amount_cents / 100).toLocaleString('en-US', { style: 'currency', currency: selectedProfile.subscription.currency })}</span>
                                        </div>
                                    )}
                                    {selectedProfile.subscription.trial_ends_at && (
                                        <div className="flex justify-between">
                                            <span className="text-gray-400">Trial Ends:</span>
                                            <span className="text-yellow-400">{new Date(selectedProfile.subscription.trial_ends_at).toLocaleDateString()}</span>
                                        </div>
                                    )}
                                    {selectedProfile.subscription.current_period_end && (
                                        <div className="flex justify-between">
                                            <span className="text-gray-400">Renews:</span>
                                            <span>{new Date(selectedProfile.subscription.current_period_end).toLocaleDateString()}</span>
                                        </div>
                                    )}

                                    <div className="pt-4 flex gap-2">
                                        <button
                                            onClick={handleExtendTrial}
                                            disabled={actionLoading}
                                            className="platform-btn platform-btn-sm platform-btn-secondary flex-1"
                                        >
                                            Extend Trial
                                        </button>
                                        <button
                                            onClick={handleCancelSubscription}
                                            disabled={actionLoading}
                                            className="platform-btn platform-btn-sm platform-btn-danger flex-1"
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <p className="text-gray-500 italic">No active subscription</p>
                            )}
                        </div>

                        {/* Invoices Card */}
                        <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
                            <h3 className="font-semibold mb-3 border-b border-gray-700 pb-2">Invoices</h3>
                            {selectedProfile.invoices && selectedProfile.invoices.length > 0 ? (
                                <div className="space-y-3 max-h-60 overflow-y-auto">
                                    {selectedProfile.invoices.map(inv => (
                                        <div key={inv.id} className="flex justify-between items-center text-sm">
                                            <div>
                                                <div className="font-medium">{(inv.amount_due / 100).toLocaleString('en-US', { style: 'currency', currency: inv.currency })}</div>
                                                <div className="text-xs text-gray-500">{new Date(inv.created_at).toLocaleDateString()}</div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <span className={`px-2 py-0.5 rounded text-xs ${inv.status === 'paid' ? 'bg-green-900 text-green-200' : 'bg-yellow-900 text-yellow-200'}`}>
                                                    {inv.status}
                                                </span>
                                                {inv.invoice_pdf_url && (
                                                    <a href={inv.invoice_pdf_url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 text-xs">PDF</a>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-gray-500 italic">No invoices found</p>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default BillingPage;

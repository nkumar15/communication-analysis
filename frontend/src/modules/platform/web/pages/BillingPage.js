import { useState, useEffect } from 'react';
import platformApiService from '../../../../core/api/platformClient';
import { useProduct } from '../layouts/SuperAdminLayout';
import '../styles/platform.css';

function BillingPage() {
    const { selectedProduct } = useProduct(); // Use global product selector
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [selectedProfile, setSelectedProfile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [actionLoading, setActionLoading] = useState(false);

    // Pagination
    const [currentPage, setCurrentPage] = useState(1);
    const itemsPerPage = 10;

    // Calculate pagination
    const totalPages = Math.ceil(searchResults.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const currentItems = searchResults.slice(startIndex, endIndex);

    // Load all profiles on mount and when product changes
    useEffect(() => {
        fetchAllProfiles();
    }, [selectedProduct]);

    // Refetch all profiles when search is cleared
    useEffect(() => {
        if (searchQuery === '' && searchResults.length > 0) {
            fetchAllProfiles();
        }
    }, [searchQuery]);

    const fetchAllProfiles = async () => {
        setLoading(true);
        setError(null);
        try {
            const type = selectedProduct === 'b2b' ? 'tenant' : 'user';
            const response = await platformApiService.searchBillingProfiles('', type);
            setSearchResults(response.items || []);
            setCurrentPage(1); // Reset to first page
        } catch (err) {
            console.error(err);
            setError('Failed to load profiles');
        } finally {
            setLoading(false);
        }
    };

    // Search
    const handleSearch = async (e) => {
        e.preventDefault();
        if (!searchQuery.trim()) {
            // If empty, refetch all
            fetchAllProfiles();
            return;
        }

        setLoading(true);
        setError(null);
        setSelectedProfile(null);
        try {
            // Use selectedProduct to determine type: b2b -> tenant, b2c -> user
            const type = selectedProduct === 'b2b' ? 'tenant' : 'user';
            const response = await platformApiService.searchBillingProfiles(searchQuery, type);
            setSearchResults(response.items || []);
            setCurrentPage(1); // Reset to first page on new search
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
                    <button type="submit" className="platform-btn platform-btn-primary" disabled={loading}>
                        {loading ? 'Searching...' : 'Search'}
                    </button>
                </form>
            </div>

            {error && <div className="platform-alert-error" style={{ marginBottom: '1rem' }}>{error}</div>}

            {/* Search Results */}
            {searchResults.length > 0 && (
                <div className="platform-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                        <h3 className="text-lg font-semibold">
                            {searchQuery ? `Search Results (${searchResults.length})` : `All ${selectedProduct.toUpperCase()} Profiles (${searchResults.length})`}
                        </h3>
                        {totalPages > 1 && (
                            <div style={{ fontSize: '14px', color: '#6B7280' }}>
                                Page {currentPage} of {totalPages}
                            </div>
                        )}
                    </div>
                    <div className="platform-table-container">
                        <table className="platform-table">
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Type</th>
                                    <th>Email/Domain</th>
                                    <th>Status</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {currentItems.map((item) => (
                                    <tr key={item.id}>
                                        <td>
                                            <div className="font-medium">{item.name}</div>
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

                    {/* Pagination Controls */}
                    {totalPages > 1 && (
                        <div style={{
                            display: 'flex',
                            justifyContent: 'center',
                            alignItems: 'center',
                            gap: '8px',
                            marginTop: '20px',
                            paddingTop: '20px',
                            borderTop: '1px solid #E5E7EB'
                        }}>
                            <button
                                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                disabled={currentPage === 1}
                                style={{
                                    padding: '8px 16px',
                                    borderRadius: '6px',
                                    border: '1px solid #D1D5DB',
                                    background: currentPage === 1 ? '#F3F4F6' : 'white',
                                    color: currentPage === 1 ? '#9CA3AF' : '#374151',
                                    fontSize: '14px',
                                    fontWeight: '600',
                                    cursor: currentPage === 1 ? 'not-allowed' : 'pointer'
                                }}
                            >
                                ← Previous
                            </button>
                            <span style={{ fontSize: '14px', color: '#6B7280', minWidth: '100px', textAlign: 'center' }}>
                                Page {currentPage} of {totalPages}
                            </span>
                            <button
                                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                disabled={currentPage === totalPages}
                                style={{
                                    padding: '8px 16px',
                                    borderRadius: '6px',
                                    border: '1px solid #D1D5DB',
                                    background: currentPage === totalPages ? '#F3F4F6' : 'white',
                                    color: currentPage === totalPages ? '#9CA3AF' : '#374151',
                                    fontSize: '14px',
                                    fontWeight: '600',
                                    cursor: currentPage === totalPages ? 'not-allowed' : 'pointer'
                                }}
                            >
                                Next →
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* Profile Detail View */}
            {selectedProfile && (
                <div className="platform-card animate-fadeIn">
                    {/* Header */}
                    <div className="platform-profile-header">
                        <div className="platform-profile-title-group">
                            <div className="platform-profile-avatar" style={{
                                backgroundColor: selectedProfile.type === 'tenant' ? '#e0e7ff' : '#d1fae5',
                                color: selectedProfile.type === 'tenant' ? '#4338ca' : '#065f46'
                            }}>
                                {selectedProfile.name.charAt(0).toUpperCase()}
                            </div>
                            <div className="platform-profile-info">
                                <h2>
                                    {selectedProfile.name}
                                    <span className="platform-status-badge" style={{
                                        backgroundColor: selectedProfile.type === 'tenant' ? '#EEF2FF' : '#ECFDF5',
                                        color: selectedProfile.type === 'tenant' ? '#4F46E5' : '#059669',
                                        border: '1px solid currentColor'
                                    }}>
                                        {selectedProfile.type}
                                    </span>
                                </h2>
                                <div className="platform-profile-meta">
                                    <span>📧 {selectedProfile.email}</span>
                                    {selectedProfile.tax_id && <span>🆔 {selectedProfile.tax_id}</span>}
                                </div>
                            </div>
                        </div>
                        <button
                            onClick={() => setSelectedProfile(null)}
                            className="platform-btn platform-btn-outline"
                            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                        >
                            <span>←</span> Back to List
                        </button>
                    </div>

                    <div className="platform-profile-grid">
                        {/* Subscriptions */}
                        <div className="platform-section-card">
                            <div className="platform-section-title">
                                <span>💎</span> Subscription
                            </div>

                            {selectedProfile.subscription ? (
                                <div>
                                    <div className="platform-detail-row">
                                        <span className="platform-detail-label">Plan</span>
                                        <span className="platform-detail-value">{selectedProfile.subscription.tier}</span>
                                    </div>
                                    <div className="platform-detail-row">
                                        <span className="platform-detail-label">Status</span>
                                        <span className={`platform-status-badge ${selectedProfile.subscription.status === 'active' ? 'platform-status-active' : 'platform-status-inactive'}`}>
                                            {selectedProfile.subscription.status?.toUpperCase()}
                                        </span>
                                    </div>
                                    <div className="platform-detail-row">
                                        <span className="platform-detail-label">Billing</span>
                                        <span className="platform-detail-value" style={{ textTransform: 'capitalize' }}>{selectedProfile.subscription.billing_interval}</span>
                                    </div>

                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '1rem' }}>
                                        <button
                                            onClick={handleExtendTrial}
                                            disabled={actionLoading}
                                            className="platform-btn platform-btn-secondary"
                                            style={{ fontSize: '12px' }}
                                        >
                                            Extend Trial
                                        </button>
                                        <button
                                            onClick={handleCancelSubscription}
                                            disabled={actionLoading}
                                            className="platform-btn"
                                            style={{
                                                backgroundColor: '#FEF2F2',
                                                color: '#EF4444',
                                                border: '1px solid #FECACA',
                                                fontSize: '12px'
                                            }}
                                        >
                                            Cancel Sub
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div className="platform-empty-state">
                                    <div style={{ fontSize: '24px', marginBottom: '8px' }}>🌑</div>
                                    <p>No active subscription found</p>
                                </div>
                            )}
                        </div>

                        {/* Invoices */}
                        <div className="platform-section-card">
                            <div className="platform-section-title">
                                <span>📄</span> Invoice History
                            </div>

                            {selectedProfile.invoices && selectedProfile.invoices.length > 0 ? (
                                <div className="platform-table-container">
                                    <table className="platform-table">
                                        <thead>
                                            <tr>
                                                <th>Date</th>
                                                <th>Amount</th>
                                                <th>Status</th>
                                                <th>Action</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {selectedProfile.invoices.map((inv) => (
                                                <tr key={inv.id}>
                                                    <td>{new Date(inv.created_at).toLocaleDateString()}</td>
                                                    <td style={{ fontWeight: '600' }}>
                                                        {(inv.amount_due / 100).toLocaleString('en-US', { style: 'currency', currency: inv.currency })}
                                                    </td>
                                                    <td>
                                                        <span className={`platform-status-badge ${inv.status === 'paid' ? 'platform-status-active' : 'platform-status-inactive'}`}>
                                                            {inv.status}
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                                            {inv.invoice_pdf_url ? (
                                                                <a href={inv.invoice_pdf_url} target="_blank" rel="noopener noreferrer" className="platform-btn platform-btn-outline" style={{ padding: '4px 8px', fontSize: '12px', minHeight: 'unset' }}>
                                                                    PDF
                                                                </a>
                                                            ) : (
                                                                <span style={{ fontSize: '12px', color: '#9CA3AF', padding: '4px 8px' }}>-</span>
                                                            )}

                                                            <button
                                                                onClick={async () => {
                                                                    if (!window.confirm('Send invoice email to tenant contact?')) return;
                                                                    try {
                                                                        await platformClient.sendInvoice(inv.id, selectedProfile.type);
                                                                        alert('Invoice email sent!');
                                                                    } catch (err) {
                                                                        alert(err.message);
                                                                    }
                                                                }}
                                                                className="platform-btn platform-btn-secondary"
                                                                style={{ padding: '4px 8px', fontSize: '12px', minHeight: 'unset' }}
                                                                title="Email Invoice"
                                                            >
                                                                ✉️ Email
                                                            </button>

                                                            {inv.status === 'paid' && (
                                                                <button
                                                                    onClick={async () => {
                                                                        const reason = window.prompt('Reason for refund:');
                                                                        if (!reason) return;
                                                                        try {
                                                                            await platformClient.refundInvoice(inv.id, selectedProfile.type, reason);
                                                                            alert('Refund initiated successfully');
                                                                            loadProfile(selectedProfile.id, selectedProfile.type); // Refresh
                                                                        } catch (err) {
                                                                            alert(err.message);
                                                                        }
                                                                    }}
                                                                    className="platform-btn"
                                                                    style={{
                                                                        backgroundColor: '#EFF6FF', color: '#1D4ED8', border: '1px solid #BFDBFE',
                                                                        padding: '4px 8px', fontSize: '12px', minHeight: 'unset'
                                                                    }}
                                                                    title="Refund Invoice"
                                                                >
                                                                    💸 Refund
                                                                </button>
                                                            )}
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            ) : (
                                <div className="platform-empty-state">
                                    <div style={{ fontSize: '24px', marginBottom: '8px' }}>📄</div>
                                    <p>No invoices generated yet</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default BillingPage;

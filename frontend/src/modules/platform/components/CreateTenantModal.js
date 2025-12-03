import { useState } from 'react';
import platformApiService from '../../../core/api/platformClient';

function CreateTenantModal({ onClose, onCreated }) {
    const [formData, setFormData] = useState({
        company_name: '',
        domain: '',
        owner_email: '',
        oidc_provider: 'auth0',
        oidc_client_id: '',
        oidc_client_secret: '',
        oidc_issuer: ''
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [showOidcConfig, setShowOidcConfig] = useState(true);

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const result = await platformApiService.onboardTenant(formData);
            setSuccess(result);
            // Don't close immediately - show success message with activation link
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        if (success) {
            onCreated(); // Refresh list
        }
        onClose();
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
        alert('Copied to clipboard!');
    };

    return (
        <div className="modal-overlay" style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000, overflowY: 'auto', padding: '20px'
        }} onClick={(e) => e.target.className === 'modal-overlay' && handleClose()}>
            <div className="modal-content" style={{
                background: '#2d2d44', padding: '2rem', borderRadius: '12px',
                width: '100%', maxWidth: '600px', border: '1px solid rgba(255,255,255,0.1)',
                maxHeight: '90vh', overflowY: 'auto'
            }} onClick={(e) => e.stopPropagation()}>
                <h2 style={{ marginBottom: '1.5rem' }}>
                    {success ? '✅ Tenant Onboarded Successfully' : 'Onboard New Tenant'}
                </h2>

                {error && (
                    <div className="error-message" style={{
                        marginBottom: '1rem',
                        padding: '1rem',
                        background: '#dc2626',
                        borderRadius: '8px',
                        color: 'white'
                    }}>
                        {error}
                    </div>
                )}

                {success ? (
                    <div style={{ background: '#065f46', padding: '1.5rem', borderRadius: '8px', marginBottom: '1rem' }}>
                        <p style={{ marginBottom: '1rem', color: '#d1fae5' }}>
                            Tenant <strong>{success.tenant_name}</strong> has been created successfully!
                        </p>
                        <p style={{ marginBottom: '1rem', fontSize: '0.9rem', color: '#d1fae5' }}>
                            Activation email sent to: <strong>{success.owner_email}</strong>
                        </p>

                        <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '6px', marginTop: '1rem' }}>
                            <label style={{ fontSize: '0.85rem', color: '#d1fae5', display: 'block', marginBottom: '0.5rem' }}>
                                Activation URL (valid for 48 hours):
                            </label>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <input
                                    type="text"
                                    readOnly
                                    value={success.activation_url}
                                    style={{
                                        flex: 1,
                                        padding: '0.5rem',
                                        background: '#1a1a2e',
                                        border: '1px solid rgba(255,255,255,0.2)',
                                        borderRadius: '4px',
                                        color: 'white',
                                        fontSize: '0.85rem'
                                    }}
                                />
                                <button
                                    onClick={() => copyToClipboard(success.activation_url)}
                                    style={{
                                        padding: '0.5rem 1rem',
                                        background: '#10b981',
                                        border: 'none',
                                        borderRadius: '4px',
                                        color: 'white',
                                        cursor: 'pointer',
                                        fontSize: '0.85rem'
                                    }}
                                >
                                    Copy
                                </button>
                            </div>
                        </div>

                        <button
                            onClick={handleClose}
                            style={{
                                marginTop: '1.5rem',
                                width: '100%',
                                padding: '0.75rem',
                                background: '#4f46e5',
                                border: 'none',
                                borderRadius: '8px',
                                color: 'white',
                                fontSize: '1rem',
                                cursor: 'pointer'
                            }}
                        >
                            Done
                        </button>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit}>
                        {/* Basic Information */}
                        <div style={{ marginBottom: '1.5rem' }}>
                            <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: '#a78bfa' }}>Basic Information</h3>

                            <div className="form-group" style={{ marginBottom: '1rem' }}>
                                <label style={{ fontSize: '0.9rem', marginBottom: '0.5rem', display: 'block' }}>
                                    Company Name <span style={{ color: '#ef4444' }}>*</span>
                                </label>
                                <input
                                    type="text"
                                    name="company_name"
                                    className="email-input"
                                    value={formData.company_name}
                                    onChange={handleChange}
                                    placeholder="e.g., Acme Corporation"
                                    required
                                />
                            </div>

                            <div className="form-group" style={{ marginBottom: '1rem' }}>
                                <label style={{ fontSize: '0.9rem', marginBottom: '0.5rem', display: 'block' }}>
                                    Domain <span style={{ color: '#ef4444' }}>*</span>
                                </label>
                                <input
                                    type="text"
                                    name="domain"
                                    className="email-input"
                                    value={formData.domain}
                                    onChange={handleChange}
                                    placeholder="e.g., acme.com"
                                    required
                                />
                            </div>

                            <div className="form-group">
                                <label style={{ fontSize: '0.9rem', marginBottom: '0.5rem', display: 'block' }}>
                                    Owner Email <span style={{ color: '#ef4444' }}>*</span>
                                </label>
                                <input
                                    type="email"
                                    name="owner_email"
                                    className="email-input"
                                    value={formData.owner_email}
                                    onChange={handleChange}
                                    placeholder="admin@acme.com"
                                    required
                                />
                            </div>
                        </div>

                        {/* OIDC Configuration */}
                        <div style={{ marginBottom: '1.5rem', border: '1px solid rgba(167,139,250,0.3)', borderRadius: '8px', padding: '1rem' }}>
                            <div
                                onClick={() => setShowOidcConfig(!showOidcConfig)}
                                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', marginBottom: showOidcConfig ? '1rem' : 0 }}
                            >
                                <h3 style={{ fontSize: '1rem', color: '#a78bfa', margin: 0 }}>
                                    SSO Configuration (OIDC)
                                </h3>
                                <span style={{ fontSize: '1.2rem' }}>{showOidcConfig ? '▼' : '▶'}</span>
                            </div>

                            {showOidcConfig && (
                                <>
                                    <div className="form-group" style={{ marginBottom: '1rem' }}>
                                        <label style={{ fontSize: '0.9rem', marginBottom: '0.5rem', display: 'block' }}>
                                            Provider Type <span style={{ color: '#ef4444' }}>*</span>
                                        </label>
                                        <select
                                            name="oidc_provider"
                                            className="email-input"
                                            value={formData.oidc_provider}
                                            onChange={handleChange}
                                            required
                                        >
                                            <option value="auth0">Auth0</option>
                                            <option value="okta">Okta</option>
                                            <option value="google">Google Workspace</option>
                                            <option value="azure">Azure AD</option>
                                        </select>
                                    </div>

                                    <div className="form-group" style={{ marginBottom: '1rem' }}>
                                        <label style={{ fontSize: '0.9rem', marginBottom: '0.5rem', display: 'block' }}>
                                            Client ID <span style={{ color: '#ef4444' }}>*</span>
                                        </label>
                                        <input
                                            type="text"
                                            name="oidc_client_id"
                                            className="email-input"
                                            value={formData.oidc_client_id}
                                            onChange={handleChange}
                                            placeholder="Your OIDC client ID"
                                            required
                                        />
                                    </div>

                                    <div className="form-group" style={{ marginBottom: '1rem' }}>
                                        <label style={{ fontSize: '0.9rem', marginBottom: '0.5rem', display: 'block' }}>
                                            Client Secret <span style={{ color: '#ef4444' }}>*</span>
                                        </label>
                                        <input
                                            type="password"
                                            name="oidc_client_secret"
                                            className="email-input"
                                            value={formData.oidc_client_secret}
                                            onChange={handleChange}
                                            placeholder="Your OIDC client secret"
                                            required
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label style={{ fontSize: '0.9rem', marginBottom: '0.5rem', display: 'block' }}>
                                            Issuer URL <span style={{ color: '#ef4444' }}>*</span>
                                        </label>
                                        <input
                                            type="url"
                                            name="oidc_issuer"
                                            className="email-input"
                                            value={formData.oidc_issuer}
                                            onChange={handleChange}
                                            placeholder="https://your-domain.auth0.com/"
                                            required
                                        />
                                        <p style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '0.25rem' }}>
                                            The base URL of your identity provider
                                        </p>
                                    </div>
                                </>
                            )}
                        </div>

                        <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
                            <button
                                type="button"
                                onClick={handleClose}
                                className="saas-btn saas-btn-outline"
                                style={{ flex: 1 }}
                                disabled={loading}
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                className="submit-button"
                                style={{ flex: 1, margin: 0 }}
                                disabled={loading}
                            >
                                {loading ? 'Creating Tenant...' : 'Onboard Tenant'}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}

export default CreateTenantModal;

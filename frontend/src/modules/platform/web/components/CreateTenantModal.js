import { useState } from 'react';
import platformApiService from '../../../../core/api/platformClient';

function CreateTenantModal({ onClose, onCreated }) {
    const [formData, setFormData] = useState({
        company_name: '',
        domain: '',
        owner_email: '',
        oidc_provider: 'oidc',
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

    // Inline styles
    const modalOverlayStyle = {
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
        background: 'rgba(0,0,0,0.75)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        overflowY: 'auto',
        padding: '20px'
    };

    const modalContentStyle = {
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '2.5rem',
        borderRadius: '16px',
        width: '100%',
        maxWidth: '650px',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        maxHeight: '90vh',
        overflowY: 'auto'
    };

    const formContainerStyle = {
        background: 'white',
        borderRadius: '12px',
        padding: '2rem',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
    };

    const headerStyle = {
        fontSize: '1.75rem',
        fontWeight: '700',
        color: 'white',
        marginBottom: '1.5rem',
        textAlign: 'center'
    };

    const sectionHeaderStyle = {
        fontSize: '1.1rem',
        fontWeight: '600',
        color: '#374151',
        marginBottom: '1rem',
        paddingBottom: '0.5rem',
        borderBottom: '2px solid #e5e7eb'
    };

    const labelStyle = {
        fontSize: '0.875rem',
        fontWeight: '500',
        color: '#374151',
        marginBottom: '0.5rem',
        display: 'block'
    };

    const inputStyle = {
        width: '100%',
        padding: '0.75rem',
        fontSize: '0.95rem',
        border: '2px solid #e5e7eb',
        borderRadius: '8px',
        outline: 'none',
        transition: 'all 0.2s',
        background: '#f9fafb',
        color: '#1f2937'
    };

    const selectStyle = {
        ...inputStyle,
        appearance: 'none',
        backgroundImage: 'url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' fill=\'none\' viewBox=\'0 0 20 20\'%3E%3Cpath stroke=\'%236b7280\' stroke-linecap=\'round\' stroke-linejoin=\'round\' stroke-width=\'1.5\' d=\'M6 8l4 4 4-4\'/%3E%3C/svg%3E")',
        backgroundPosition: 'right 0.5rem center',
        backgroundRepeat: 'no-repeat',
        backgroundSize: '1.5em 1.5em',
        paddingRight: '2.5rem',
        cursor: 'pointer',
        color: '#1f2937'
    };

    const buttonPrimaryStyle = {
        flex: 1,
        padding: '0.875rem 1.5rem',
        fontSize: '1rem',
        fontWeight: '600',
        color: 'white',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        border: 'none',
        borderRadius: '8px',
        cursor: 'pointer',
        transition: 'all 0.2s',
        boxShadow: '0 4px 6px rgba(102, 126, 234, 0.3)'
    };

    const buttonSecondaryStyle = {
        flex: 1,
        padding: '0.875rem 1.5rem',
        fontSize: '1rem',
        fontWeight: '600',
        color: '#4b5563',
        background: 'white',
        border: '2px solid #e5e7eb',
        borderRadius: '8px',
        cursor: 'pointer',
        transition: 'all 0.2s'
    };

    const collapsibleHeaderStyle = {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        cursor: 'pointer',
        padding: '1rem',
        background: '#f3f4f6',
        borderRadius: '8px',
        marginBottom: showOidcConfig ? '1rem' : 0,
        transition: 'all 0.2s'
    };

    return (
        <div
            className="modal-overlay"
            style={modalOverlayStyle}
            onClick={(e) => e.target.className === 'modal-overlay' && handleClose()}
        >
            <div
                className="modal-content"
                style={modalContentStyle}
                onClick={(e) => e.stopPropagation()}
            >
                <h2 style={headerStyle}>
                    {success ? '✅ Tenant Onboarded Successfully' : '🚀 Onboard New Tenant'}
                </h2>

                {error && (
                    <div style={{
                        marginBottom: '1rem',
                        padding: '1rem',
                        background: '#fef2f2',
                        border: '2px solid #fca5a5',
                        borderRadius: '8px',
                        color: '#dc2626',
                        fontWeight: '500'
                    }}>
                        ⚠️ {error}
                    </div>
                )}

                {success ? (
                    <div style={formContainerStyle}>
                        <div style={{
                            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                            padding: '1.5rem',
                            borderRadius: '12px',
                            color: 'white',
                            marginBottom: '1rem'
                        }}>
                            <p style={{ marginBottom: '0.75rem', fontSize: '1.1rem' }}>
                                🎉 Tenant <strong>{success.tenant_name}</strong> created!
                            </p>
                            <p style={{ marginBottom: '0', fontSize: '0.95rem', opacity: 0.9 }}>
                                Activation email sent to: <strong>{success.owner_email}</strong>
                            </p>
                        </div>

                        <div style={{
                            background: '#f3f4f6',
                            padding: '1rem',
                            borderRadius: '8px',
                            border: '2px solid #e5e7eb'
                        }}>
                            <label style={{
                                fontSize: '0.875rem',
                                color: '#6b7280',
                                display: 'block',
                                marginBottom: '0.5rem',
                                fontWeight: '600'
                            }}>
                                📎 Activation URL (valid for 48 hours):
                            </label>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <input
                                    type="text"
                                    readOnly
                                    value={success.activation_url}
                                    style={{
                                        flex: 1,
                                        padding: '0.75rem',
                                        background: 'white',
                                        border: '2px solid #e5e7eb',
                                        borderRadius: '8px',
                                        color: '#1f2937',
                                        fontSize: '0.875rem',
                                        fontFamily: 'monospace'
                                    }}
                                />
                                <button
                                    onClick={() => copyToClipboard(success.activation_url)}
                                    style={{
                                        padding: '0.75rem 1.25rem',
                                        background: '#667eea',
                                        border: 'none',
                                        borderRadius: '8px',
                                        color: 'white',
                                        cursor: 'pointer',
                                        fontSize: '0.875rem',
                                        fontWeight: '600'
                                    }}
                                >
                                    📋 Copy
                                </button>
                            </div>
                        </div>

                        <button
                            onClick={handleClose}
                            style={{
                                ...buttonPrimaryStyle,
                                marginTop: '1.5rem',
                                width: '100%'
                            }}
                        >
                            Done
                        </button>
                    </div>
                ) : (
                    <div style={formContainerStyle}>
                        <form onSubmit={handleSubmit}>
                            {/* Basic Information */}
                            <div style={{ marginBottom: '2rem' }}>
                                <h3 style={sectionHeaderStyle}>📋 Basic Information</h3>

                                <div style={{ marginBottom: '1.25rem' }}>
                                    <label style={labelStyle}>
                                        Company Name <span style={{ color: '#ef4444' }}>*</span>
                                    </label>
                                    <input
                                        type="text"
                                        name="company_name"
                                        value={formData.company_name}
                                        onChange={handleChange}
                                        placeholder="e.g., Acme Corporation"
                                        required
                                        style={inputStyle}
                                        onFocus={(e) => e.target.style.borderColor = '#667eea'}
                                        onBlur={(e) => e.target.style.borderColor = '#e5e7eb'}
                                    />
                                </div>

                                <div style={{ marginBottom: '1.25rem' }}>
                                    <label style={labelStyle}>
                                        Domain <span style={{ color: '#ef4444' }}>*</span>
                                    </label>
                                    <input
                                        type="text"
                                        name="domain"
                                        value={formData.domain}
                                        onChange={handleChange}
                                        placeholder="e.g., acme.com"
                                        required
                                        style={inputStyle}
                                        onFocus={(e) => e.target.style.borderColor = '#667eea'}
                                        onBlur={(e) => e.target.style.borderColor = '#e5e7eb'}
                                    />
                                </div>

                                <div>
                                    <label style={labelStyle}>
                                        Owner Email <span style={{ color: '#ef4444' }}>*</span>
                                    </label>
                                    <input
                                        type="email"
                                        name="owner_email"
                                        value={formData.owner_email}
                                        onChange={handleChange}
                                        placeholder="admin@acme.com"
                                        required
                                        style={inputStyle}
                                        onFocus={(e) => e.target.style.borderColor = '#667eea'}
                                        onBlur={(e) => e.target.style.borderColor = '#e5e7eb'}
                                    />
                                </div>
                            </div>

                            {/* SSO Configuration */}
                            <div style={{ marginBottom: '2rem' }}>
                                <div
                                    onClick={() => setShowOidcConfig(!showOidcConfig)}
                                    style={collapsibleHeaderStyle}
                                    onMouseEnter={(e) => e.currentTarget.style.background = '#e5e7eb'}
                                    onMouseLeave={(e) => e.currentTarget.style.background = '#f3f4f6'}
                                >
                                    <h3 style={{ fontSize: '1.1rem', fontWeight: '600', color: '#374151', margin: 0 }}>
                                        🔐 SSO Configuration
                                    </h3>
                                    <span style={{ fontSize: '1.2rem', color: '#6b7280' }}>
                                        {showOidcConfig ? '▼' : '▶'}
                                    </span>
                                </div>

                                {showOidcConfig && (
                                    <div style={{ paddingTop: '0.5rem' }}>
                                        <div style={{ marginBottom: '1.25rem' }}>
                                            <label style={labelStyle}>
                                                Provider Type <span style={{ color: '#ef4444' }}>*</span>
                                            </label>
                                            <select
                                                name="oidc_provider"
                                                value={formData.oidc_provider}
                                                onChange={handleChange}
                                                required
                                                style={selectStyle}
                                                onFocus={(e) => e.target.style.borderColor = '#667eea'}
                                                onBlur={(e) => e.target.style.borderColor = '#e5e7eb'}
                                            >
                                                <option value="oidc">OIDC (Generic)</option>
                                                <option value="saml">SAML</option>
                                                <option value="google">Google Workspace</option>
                                                <option value="microsoft">Microsoft Azure AD</option>
                                            </select>
                                        </div>

                                        <div style={{ marginBottom: '1.25rem' }}>
                                            <label style={labelStyle}>
                                                Client ID <span style={{ color: '#ef4444' }}>*</span>
                                            </label>
                                            <input
                                                type="text"
                                                name="oidc_client_id"
                                                value={formData.oidc_client_id}
                                                onChange={handleChange}
                                                placeholder="Your SSO client ID"
                                                required
                                                style={inputStyle}
                                                onFocus={(e) => e.target.style.borderColor = '#667eea'}
                                                onBlur={(e) => e.target.style.borderColor = '#e5e7eb'}
                                            />
                                        </div>

                                        <div style={{ marginBottom: '1.25rem' }}>
                                            <label style={labelStyle}>
                                                Client Secret <span style={{ color: '#ef4444' }}>*</span>
                                            </label>
                                            <input
                                                type="password"
                                                name="oidc_client_secret"
                                                value={formData.oidc_client_secret}
                                                onChange={handleChange}
                                                placeholder="Your SSO client secret"
                                                required
                                                style={inputStyle}
                                                onFocus={(e) => e.target.style.borderColor = '#667eea'}
                                                onBlur={(e) => e.target.style.borderColor = '#e5e7eb'}
                                            />
                                        </div>

                                        <div>
                                            <label style={labelStyle}>
                                                Issuer URL <span style={{ color: '#ef4444' }}>*</span>
                                            </label>
                                            <input
                                                type="url"
                                                name="oidc_issuer"
                                                value={formData.oidc_issuer}
                                                onChange={handleChange}
                                                placeholder="https://your-domain.com/"
                                                required
                                                style={inputStyle}
                                                onFocus={(e) => e.target.style.borderColor = '#667eea'}
                                                onBlur={(e) => e.target.style.borderColor = '#e5e7eb'}
                                            />
                                            <p style={{
                                                fontSize: '0.8rem',
                                                color: '#6b7280',
                                                marginTop: '0.5rem',
                                                fontStyle: 'italic'
                                            }}>
                                                The base URL of your identity provider
                                            </p>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div style={{ display: 'flex', gap: '1rem' }}>
                                <button
                                    type="button"
                                    onClick={handleClose}
                                    disabled={loading}
                                    style={buttonSecondaryStyle}
                                    onMouseEnter={(e) => !loading && (e.target.style.background = '#f3f4f6')}
                                    onMouseLeave={(e) => !loading && (e.target.style.background = 'white')}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={loading}
                                    style={{
                                        ...buttonPrimaryStyle,
                                        opacity: loading ? 0.7 : 1,
                                        cursor: loading ? 'not-allowed' : 'pointer'
                                    }}
                                    onMouseEnter={(e) => !loading && (e.target.style.transform = 'translateY(-2px)')}
                                    onMouseLeave={(e) => !loading && (e.target.style.transform = 'translateY(0)')}
                                >
                                    {loading ? '⏳ Creating...' : '✨ Onboard Tenant'}
                                </button>
                            </div>
                        </form>
                    </div>
                )}
            </div>
        </div>
    );
}

export default CreateTenantModal;

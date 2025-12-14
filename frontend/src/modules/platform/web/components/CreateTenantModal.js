import { useState } from 'react';
import platformApiService from '../../../../core/api/platformClient';

function CreateTenantModal({ onClose, onCreated }) {
    const [formData, setFormData] = useState({
        company_name: '',
        domain: '',
        owner_email: '',
        provider_type: 'oidc',
        // OIDC / Google / Microsoft
        oidc_client_id: '',
        oidc_client_secret: '',
        oidc_issuer: '',
        // SAML
        saml_entity_id: '',
        saml_sso_url: ''
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
            // Construct request payload
            const payload = {
                company_name: formData.company_name,
                domain: formData.domain,
                owner_email: formData.owner_email,
                provider_type: formData.provider_type,
                provider_config: {}
            };

            if (formData.provider_type === 'oidc') {
                payload.provider_config = {
                    client_id: formData.oidc_client_id,
                    client_secret: formData.oidc_client_secret,
                    issuer: formData.oidc_issuer,
                    provider_id: 'oidc.generic' // Default alias
                };
            } else if (formData.provider_type === 'saml') {
                payload.provider_config = {
                    idp_entity_id: formData.saml_entity_id,
                    sso_url: formData.saml_sso_url
                };
            } else if (['google', 'microsoft'].includes(formData.provider_type)) {
                payload.provider_config = {
                    client_id: formData.oidc_client_id,
                    client_secret: formData.oidc_client_secret,
                    issuer: formData.oidc_issuer // Optional for these, but good to have if user provides
                };
            }

            // Legacy backward compatibility (optional, but good for safety if API still expects them)
            // payload.oidc_provider = formData.provider_type === 'oidc' ? 'oidc' : formData.provider_type;

            const result = await platformApiService.onboardTenant(payload);
            setSuccess(result);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const overlayStyle = {
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
    };

    const modalStyle = {
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '2rem',
        width: '100%',
        maxWidth: '500px',
        maxHeight: '90vh',
        overflowY: 'auto',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
    };

    const labelStyle = {
        display: 'block',
        marginBottom: '0.5rem',
        fontSize: '0.875rem',
        fontWeight: '500',
        color: '#374151'
    };

    const inputStyle = {
        width: '100%',
        padding: '0.75rem',
        border: '1px solid #d1d5db',
        borderRadius: '6px',
        fontSize: '1rem',
        transition: 'border-color 0.15s ease-in-out',
        outline: 'none'
    };

    const selectStyle = {
        ...inputStyle,
        backgroundColor: 'white'
    };

    const buttonPrimaryStyle = {
        padding: '0.75rem 1.5rem',
        backgroundColor: '#4f46e5',
        color: 'white',
        border: 'none',
        borderRadius: '6px',
        fontWeight: '500',
        cursor: 'pointer',
        transition: 'all 0.2s',
        flex: 1
    };

    const buttonSecondaryStyle = {
        padding: '0.75rem 1.5rem',
        backgroundColor: 'white',
        color: '#374151',
        border: '1px solid #d1d5db',
        borderRadius: '6px',
        fontWeight: '500',
        cursor: 'pointer',
        transition: 'all 0.2s',
        flex: 1
    };

    const collapsibleHeaderStyle = {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0.75rem',
        backgroundColor: '#f9fafb',
        borderRadius: '6px',
        cursor: 'pointer',
        border: '1px solid #e5e7eb',
        transition: 'background-color 0.2s'
    };

    return (
        <div style={overlayStyle} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
            <div style={modalStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2rem' }}>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', margin: 0 }}>
                        Onboard New Tenant
                    </h2>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#6b7280' }}>
                        ×
                    </button>
                </div>

                {error && (
                    <div style={{ marginBottom: '1rem', padding: '1rem', backgroundColor: '#fef2f2', color: '#991b1b', borderRadius: '6px' }}>
                        {error}
                    </div>
                )}

                {success ? (
                    <div style={{ textAlign: 'center', padding: '2rem 0' }}>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🎉</div>
                        <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#111827', marginBottom: '0.5rem' }}>
                            Tenant Created Successfully!
                        </h3>
                        <p style={{ color: '#6b7280', marginBottom: '2rem' }}>
                            An activation email has been sent to <strong>{formData.owner_email}</strong>.
                        </p>
                        <button onClick={() => { if (onCreated) onCreated(); onClose(); }} style={buttonPrimaryStyle}>
                            Done
                        </button>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit}>
                        <div style={{ marginBottom: '1.25rem' }}>
                            <label style={labelStyle}>Company Name <span style={{ color: '#ef4444' }}>*</span></label>
                            <input
                                type="text"
                                name="company_name"
                                value={formData.company_name}
                                onChange={handleChange}
                                placeholder="Acme Corp"
                                required
                                style={inputStyle}
                            />
                        </div>

                        <div style={{ marginBottom: '1.25rem' }}>
                            <label style={labelStyle}>Domain <span style={{ color: '#ef4444' }}>*</span></label>
                            <input
                                type="text"
                                name="domain"
                                value={formData.domain}
                                onChange={handleChange}
                                placeholder="acme.com"
                                required
                                style={inputStyle}
                            />
                        </div>

                        <div style={{ marginBottom: '1.25rem' }}>
                            <label style={labelStyle}>Admin Email <span style={{ color: '#ef4444' }}>*</span></label>
                            <input
                                type="email"
                                name="owner_email"
                                value={formData.owner_email}
                                onChange={handleChange}
                                placeholder="admin@acme.com"
                                required
                                style={inputStyle}
                            />
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
                                            name="provider_type"
                                            value={formData.provider_type}
                                            onChange={handleChange}
                                            required
                                            style={selectStyle}
                                            onFocus={(e) => e.target.style.borderColor = '#667eea'}
                                            onBlur={(e) => e.target.style.borderColor = '#e5e7eb'}
                                        >
                                            <option value="oidc">OIDC (Generic)</option>
                                            <option value="saml">SAML (Skeletal)</option>
                                            <option value="google">Google Workspace</option>
                                            <option value="microsoft">Microsoft Azure AD</option>
                                        </select>
                                    </div>

                                    {formData.provider_type === 'saml' ? (
                                        <>
                                            <div style={{ marginBottom: '1.25rem' }}>
                                                <label style={labelStyle}>
                                                    Entity ID <span style={{ color: '#ef4444' }}>*</span>
                                                </label>
                                                <input
                                                    type="text"
                                                    name="saml_entity_id"
                                                    value={formData.saml_entity_id}
                                                    onChange={handleChange}
                                                    placeholder="SAML Entity ID"
                                                    required
                                                    style={inputStyle}
                                                />
                                            </div>
                                            <div style={{ marginBottom: '1.25rem' }}>
                                                <label style={labelStyle}>
                                                    SSO URL <span style={{ color: '#ef4444' }}>*</span>
                                                </label>
                                                <input
                                                    type="url"
                                                    name="saml_sso_url"
                                                    value={formData.saml_sso_url}
                                                    onChange={handleChange}
                                                    placeholder="SAML SSO URL"
                                                    required
                                                    style={inputStyle}
                                                />
                                            </div>
                                        </>
                                    ) : (
                                        <>
                                            <div style={{ marginBottom: '1.25rem' }}>
                                                <label style={labelStyle}>
                                                    Client ID <span style={{ color: '#ef4444' }}>*</span>
                                                </label>
                                                <input
                                                    type="text"
                                                    name="oidc_client_id"
                                                    value={formData.oidc_client_id}
                                                    onChange={handleChange}
                                                    placeholder="Client ID"
                                                    required
                                                    style={inputStyle}
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
                                                    placeholder="Client Secret"
                                                    required
                                                    style={inputStyle}
                                                />
                                            </div>

                                            <div style={{ marginBottom: '1.25rem' }}>
                                                <label style={labelStyle}>
                                                    Issuer URL {['google', 'microsoft'].includes(formData.provider_type) && '(Optional)'} <span style={{ color: formData.provider_type === 'oidc' ? '#ef4444' : '#9ca3af' }}>{formData.provider_type === 'oidc' ? '*' : ''}</span>
                                                </label>
                                                <input
                                                    type="url"
                                                    name="oidc_issuer"
                                                    value={formData.oidc_issuer}
                                                    onChange={handleChange}
                                                    placeholder="Issuer URL"
                                                    required={formData.provider_type === 'oidc'}
                                                    style={inputStyle}
                                                />
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}
                        </div>

                        <div style={{ display: 'flex', gap: '1rem' }}>
                            <button
                                type="button"
                                onClick={onClose}
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
                )}
            </div>
        </div>
    );
}

export default CreateTenantModal;

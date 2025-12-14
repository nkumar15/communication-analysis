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

    // ... (rest of styles/render) ...

    {/* SSO Configuration */ }
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
                        </form >
                    </div >
                )
}
            </div >
        </div >
    );
}

export default CreateTenantModal;

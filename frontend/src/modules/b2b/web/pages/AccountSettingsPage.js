import React, { useState, useEffect } from 'react';
import useAuth from '../../../../core/hooks/useAuth';
import { accountApi } from '../../../../core/api/accountClient';
import api from '../../../../core/api/b2bClient';
import AdminLayout from '../layouts/AdminLayout';
import { CardSkeleton } from '../../../../core/components/LoadingSkeleton';

const AccountSettingsPage = () => {
    const { user, hasRole } = useAuth();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    // Form state
    const [formData, setFormData] = useState({
        name: '',
        domain: '',
        logo_url: '',
        created_at: ''
    });

    // SSO state
    const [ssoConfig, setSsoConfig] = useState(null);
    const [ssoLoading, setSsoLoading] = useState(true);
    const [editingSSO, setEditingSSO] = useState(false);
    const [ssoFormData, setSsoFormData] = useState({
        client_id: '',
        client_secret: '',
        issuer: '',
        mobile_client_id: '',
        mobile_client_secret: ''
    });

    const canEdit = hasRole(['owner', 'admin']);

    useEffect(() => {
        loadSettings();
        if (canEdit) {
            loadSSOConfig();
        } else {
            setSsoLoading(false); // Don't show loading for non-editors
        }
    }, [canEdit]);

    const loadSettings = async () => {
        try {
            setLoading(true);
            const data = await accountApi.getSettings();
            setFormData({
                name: data.name,
                domain: data.domain,
                logo_url: data.logo_url || '',
                created_at: new Date(data.created_at).toLocaleDateString()
            });
        } catch (err) {
            setError(err.message || 'Failed to load account settings');
        } finally {
            setLoading(false);
        }
    };

    const loadSSOConfig = async () => {
        try {
            setSsoLoading(true);
            console.log('🔍 Fetching SSO config from /api/b2b/settings/sso');
            const response = await api.get('/api/b2b/settings/sso');
            console.log('✅ Full API response:', response);

            // The b2bClient already extracts .data, so response IS the data
            const data = response.data || response;
            console.log('✅ SSO config data:', data);

            setSsoConfig(data);
            setSsoFormData({
                client_id: data.client_id || '',
                client_secret: '',
                issuer: data.issuer || '',
                mobile_client_id: data.mobile_client_id || '',
                mobile_client_secret: ''
            });
            console.log('✅ SSO config state updated');
        } catch (err) {
            console.error('❌ Failed to load SSO config:', err);
            console.error('Error response:', err.response?.data);
            console.error('Error status:', err.response?.status);
            // Don't show error for 404 - it's expected for tenants without SSO configured
            // Just let the empty state UI show instead
        } finally {
            setSsoLoading(false);
            console.log('✅ SSO loading complete, ssoLoading = false');
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!canEdit) return;

        try {
            setSaving(true);
            setError('');
            setSuccess('');

            await accountApi.updateSettings({
                name: formData.name,
                logo_url: formData.logo_url
            });

            setSuccess('Account settings updated successfully');

            // Reload to ensure sync
            await loadSettings();
        } catch (err) {
            setError(err.message || 'Failed to update settings');
        } finally {
            setSaving(false);
        }
    };

    const handleSSOSubmit = async (e) => {
        e.preventDefault();
        console.log('🚀 SSO Submit triggered');
        console.log('📦 Form data:', ssoFormData);

        try {
            setSaving(true);
            setError('');
            setSuccess('');

            console.log('📡 Sending PUT request to /api/b2b/settings/sso');
            const response = await api.put('/api/b2b/settings/sso', ssoFormData);
            console.log('✅ API response:', response);

            setSuccess('SSO configuration updated successfully');
            setEditingSSO(false);

            // Reload SSO config
            await loadSSOConfig();
        } catch (err) {
            console.error('❌ SSO update failed:', err);
            console.error('Error response:', err.response);
            console.error('Error data:', err.response?.data);
            setError(err.response?.data?.detail || err.message || 'Failed to update SSO configuration');
        } finally {
            setSaving(false);
            console.log('✅ SSO submit complete');
        }
    };

    const handleCancel = () => {
        setError('');
        setSuccess('');
        loadSettings();
    };

    const handleSSOCancel = () => {
        setEditingSSO(false);
        setError('');
        setSuccess('');
        // Reset form
        if (ssoConfig) {
            setSsoFormData({
                client_id: ssoConfig.client_id,
                client_secret: '',
                issuer: ssoConfig.issuer,
                mobile_client_id: ssoConfig.mobile_client_id || '',
                mobile_client_secret: ''
            });
        }
    };

    if (loading) {
        return (
            <AdminLayout title="Account Settings" subtitle="Manage your organization's profile and preferences">
                <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
                    <CardSkeleton />
                    <CardSkeleton />
                </div>
            </AdminLayout>
        );
    }

    return (
        <AdminLayout title="Account Settings" subtitle="Manage your organization's profile and preferences">
            <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
                {error && (
                    <div style={{
                        padding: '12px 16px',
                        backgroundColor: '#fee2e2',
                        color: '#b91c1c',
                        borderRadius: '8px',
                        marginBottom: '24px'
                    }}>
                        {error}
                    </div>
                )}

                {success && (
                    <div style={{
                        padding: '12px 16px',
                        backgroundColor: '#d1fae5',
                        color: '#047857',
                        borderRadius: '8px',
                        marginBottom: '24px'
                    }}>
                        {success}
                    </div>
                )}

                {/* Organization Settings Card */}
                <div style={{
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                    padding: '32px',
                    marginBottom: '24px'
                }}>
                    <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '24px', color: '#111827' }}>
                        Organization Profile
                    </h2>
                    <form onSubmit={handleSubmit}>
                        {/* Tenant Name */}
                        <div style={{ marginBottom: '24px' }}>
                            <label style={{
                                display: 'block',
                                fontSize: '14px',
                                fontWeight: '600',
                                color: '#374151',
                                marginBottom: '8px'
                            }}>
                                Organization Name
                            </label>
                            <input
                                type="text"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                disabled={!canEdit}
                                required
                                style={{
                                    width: '100%',
                                    padding: '10px 12px',
                                    borderRadius: '6px',
                                    border: '1px solid #d1d5db',
                                    fontSize: '14px',
                                    backgroundColor: canEdit ? 'white' : '#f3f4f6'
                                }}
                            />
                        </div>

                        {/* Domain (Read-only) */}
                        <div style={{ marginBottom: '24px' }}>
                            <label style={{
                                display: 'block',
                                fontSize: '14px',
                                fontWeight: '600',
                                color: '#374151',
                                marginBottom: '8px'
                            }}>
                                Domain <span style={{ fontWeight: 'normal', color: '#6B7280', marginLeft: '8px' }}>(Read-only)</span>
                            </label>
                            <input
                                type="text"
                                value={formData.domain}
                                disabled
                                style={{
                                    width: '100%',
                                    padding: '10px 12px',
                                    borderRadius: '6px',
                                    border: '1px solid #d1d5db',
                                    fontSize: '14px',
                                    backgroundColor: '#f3f4f6',
                                    color: '#6B7280'
                                }}
                            />
                            <p style={{ marginTop: '6px', fontSize: '12px', color: '#6B7280' }}>
                                Your organization's domain is locked for security reasons. Contact support to change it.
                            </p>
                        </div>

                        {/* Logo URL */}
                        <div style={{ marginBottom: '24px' }}>
                            <label style={{
                                display: 'block',
                                fontSize: '14px',
                                fontWeight: '600',
                                color: '#374151',
                                marginBottom: '8px'
                            }}>
                                Logo URL
                            </label>
                            <input
                                type="url"
                                value={formData.logo_url}
                                onChange={(e) => setFormData({ ...formData, logo_url: e.target.value })}
                                disabled={!canEdit}
                                placeholder="https://example.com/logo.png"
                                style={{
                                    width: '100%',
                                    padding: '10px 12px',
                                    borderRadius: '6px',
                                    border: '1px solid #d1d5db',
                                    fontSize: '14px',
                                    backgroundColor: canEdit ? 'white' : '#f3f4f6'
                                }}
                            />
                            {formData.logo_url && (
                                <div style={{ marginTop: '12px' }}>
                                    <p style={{ fontSize: '12px', color: '#6B7280', marginBottom: '4px' }}>Preview:</p>
                                    <img
                                        src={formData.logo_url}
                                        alt="Logo Preview"
                                        style={{ maxHeight: '40px', maxWidth: '100%', objectFit: 'contain' }}
                                        onError={(e) => e.target.style.display = 'none'}
                                    />
                                </div>
                            )}
                        </div>

                        {/* Created At (Read-only) */}
                        <div style={{ marginBottom: '32px' }}>
                            <label style={{
                                display: 'block',
                                fontSize: '14px',
                                fontWeight: '600',
                                color: '#374151',
                                marginBottom: '8px'
                            }}>
                                Member Since
                            </label>
                            <div style={{ fontSize: '14px', color: '#374151' }}>
                                {formData.created_at}
                            </div>
                        </div>

                        {/* Action Buttons */}
                        {canEdit && (
                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                                <button
                                    type="button"
                                    onClick={handleCancel}
                                    disabled={saving}
                                    style={{
                                        padding: '10px 20px',
                                        borderRadius: '6px',
                                        border: '1px solid #d1d5db',
                                        backgroundColor: 'white',
                                        color: '#374151',
                                        fontSize: '14px',
                                        fontWeight: '500',
                                        cursor: 'pointer'
                                    }}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={saving}
                                    style={{
                                        padding: '10px 20px',
                                        borderRadius: '6px',
                                        border: 'none',
                                        backgroundColor: '#4f46e5',
                                        color: 'white',
                                        fontSize: '14px',
                                        fontWeight: '500',
                                        cursor: saving ? 'not-allowed' : 'pointer',
                                        opacity: saving ? 0.7 : 1
                                    }}
                                >
                                    {saving ? 'Saving...' : 'Save Changes'}
                                </button>
                            </div>
                        )}

                        {!canEdit && (
                            <div style={{
                                padding: '12px',
                                backgroundColor: '#f3f4f6',
                                borderRadius: '6px',
                                fontSize: '14px',
                                color: '#6B7280',
                                textAlign: 'center'
                            }}>
                                You do not have permission to edit account settings. Contact your administrator.
                            </div>
                        )}
                    </form>
                </div>

                {/* SSO Configuration Card */}
                {canEdit && (
                    <div style={{
                        backgroundColor: 'white',
                        borderRadius: '12px',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                        padding: '32px'
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                            <h2 style={{ fontSize: '18px', fontWeight: '600', color: '#111827', margin: 0 }}>
                                🔐 SSO Configuration
                            </h2>
                            {!editingSSO && ssoConfig && (
                                <button
                                    onClick={() => setEditingSSO(true)}
                                    style={{
                                        padding: '8px 16px',
                                        borderRadius: '6px',
                                        border: '1px solid #d1d5db',
                                        backgroundColor: 'white',
                                        color: '#374151',
                                        fontSize: '14px',
                                        fontWeight: '500',
                                        cursor: 'pointer'
                                    }}
                                >
                                    Edit Credentials
                                </button>
                            )}
                        </div>

                        {/* Debug: Log current state at render time */}
                        {console.log('🎨 Rendering SSO section - ssoLoading:', ssoLoading, 'ssoConfig:', ssoConfig, 'canEdit:', canEdit)}

                        {ssoLoading ? (
                            <CardSkeleton />
                        ) : ssoConfig ? (
                            editingSSO ? (
                                <form onSubmit={handleSSOSubmit}>
                                    <div style={{ marginBottom: '20px' }}>
                                        <label style={{
                                            display: 'block',
                                            fontSize: '14px',
                                            fontWeight: '600',
                                            color: '#374151',
                                            marginBottom: '8px'
                                        }}>
                                            Provider Type <span style={{ fontWeight: 'normal', color: '#6B7280', marginLeft: '8px' }}>(Read-only)</span>
                                        </label>
                                        <input
                                            type="text"
                                            value={ssoConfig.provider_type.toUpperCase()}
                                            disabled
                                            style={{
                                                width: '100%',
                                                padding: '10px 12px',
                                                borderRadius: '6px',
                                                border: '1px solid #d1d5db',
                                                fontSize: '14px',
                                                backgroundColor: '#f3f4f6',
                                                color: '#6B7280'
                                            }}
                                        />
                                    </div>

                                    <div style={{ marginBottom: '20px' }}>
                                        <label style={{
                                            display: 'block',
                                            fontSize: '14px',
                                            fontWeight: '600',
                                            color: '#374151',
                                            marginBottom: '8px'
                                        }}>
                                            Client ID <span style={{ color: '#ef4444' }}>*</span>
                                        </label>
                                        <input
                                            type="text"
                                            value={ssoFormData.client_id}
                                            onChange={(e) => setSsoFormData({ ...ssoFormData, client_id: e.target.value })}
                                            required
                                            style={{
                                                width: '100%',
                                                padding: '10px 12px',
                                                borderRadius: '6px',
                                                border: '1px solid #d1d5db',
                                                fontSize: '14px'
                                            }}
                                        />
                                    </div>

                                    <div style={{ marginBottom: '20px' }}>
                                        <label style={{
                                            display: 'block',
                                            fontSize: '14px',
                                            fontWeight: '600',
                                            color: '#374151',
                                            marginBottom: '8px'
                                        }}>
                                            Client Secret <span style={{ color: '#ef4444' }}>*</span>
                                        </label>
                                        <input
                                            type="password"
                                            value={ssoFormData.client_secret}
                                            onChange={(e) => setSsoFormData({ ...ssoFormData, client_secret: e.target.value })}
                                            required
                                            placeholder="Enter new client secret"
                                            style={{
                                                width: '100%',
                                                padding: '10px 12px',
                                                borderRadius: '6px',
                                                border: '1px solid #d1d5db',
                                                fontSize: '14px'
                                            }}
                                        />
                                    </div>

                                    <div style={{ marginBottom: '24px' }}>
                                        <label style={{
                                            display: 'block',
                                            fontSize: '14px',
                                            fontWeight: '600',
                                            color: '#374151',
                                            marginBottom: '8px'
                                        }}>
                                            Issuer URL <span style={{ color: '#ef4444' }}>*</span>
                                        </label>
                                        <input
                                            type="url"
                                            value={ssoFormData.issuer}
                                            onChange={(e) => setSsoFormData({ ...ssoFormData, issuer: e.target.value })}
                                            required
                                            style={{
                                                width: '100%',
                                                padding: '10px 12px',
                                                borderRadius: '6px',
                                                border: '1px solid #d1d5db',
                                                fontSize: '14px'
                                            }}
                                        />
                                    </div>

                                    {/* Mobile SSO Configuration (Optional) */}
                                    <div style={{
                                        marginTop: '24px',
                                        padding: '16px',
                                        backgroundColor: '#f9fafb',
                                        borderRadius: '8px',
                                        border: '1px solid #e5e7eb'
                                    }}>
                                        <h4 style={{
                                            fontSize: '14px',
                                            fontWeight: '600',
                                            color: '#374151',
                                            marginBottom: '8px'
                                        }}>
                                            📱 Mobile SSO (Optional)
                                        </h4>
                                        <p style={{ fontSize: '13px', color: '#6B7280', marginBottom: '16px' }}>
                                            Configure separate OAuth credentials for mobile apps. Leave blank to use web credentials.
                                        </p>

                                        <div style={{ marginBottom: '16px' }}>
                                            <label style={{
                                                display: 'block',
                                                fontSize: '14px',
                                                fontWeight: '500',
                                                color: '#374151',
                                                marginBottom: '8px'
                                            }}>
                                                Mobile Client ID
                                            </label>
                                            <input
                                                type="text"
                                                value={ssoFormData.mobile_client_id}
                                                onChange={(e) => setSsoFormData({ ...ssoFormData, mobile_client_id: e.target.value })}
                                                placeholder="Optional - mobile OAuth client ID"
                                                style={{
                                                    width: '100%',
                                                    padding: '10px 12px',
                                                    borderRadius: '6px',
                                                    border: '1px solid #d1d5db',
                                                    fontSize: '14px',
                                                    backgroundColor: 'white'
                                                }}
                                            />
                                        </div>

                                        <div style={{ marginBottom: '0' }}>
                                            <label style={{
                                                display: 'block',
                                                fontSize: '14px',
                                                fontWeight: '500',
                                                color: '#374151',
                                                marginBottom: '8px'
                                            }}>
                                                Mobile Client Secret
                                            </label>
                                            <input
                                                type="password"
                                                value={ssoFormData.mobile_client_secret}
                                                onChange={(e) => setSsoFormData({ ...ssoFormData, mobile_client_secret: e.target.value })}
                                                placeholder="Optional - mobile OAuth client secret"
                                                style={{
                                                    width: '100%',
                                                    padding: '10px 12px',
                                                    borderRadius: '6px',
                                                    border: '1px solid #d1d5db',
                                                    fontSize: '14px',
                                                    backgroundColor: 'white'
                                                }}
                                            />
                                        </div>
                                    </div>

                                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
                                        <button
                                            type="button"
                                            onClick={handleSSOCancel}
                                            disabled={saving}
                                            style={{
                                                padding: '10px 20px',
                                                borderRadius: '6px',
                                                border: '1px solid #d1d5db',
                                                backgroundColor: 'white',
                                                color: '#374151',
                                                fontSize: '14px',
                                                fontWeight: '500',
                                                cursor: 'pointer'
                                            }}
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            type="submit"
                                            disabled={saving}
                                            onClick={() => console.log('🖱️ Submit button clicked')}
                                            style={{
                                                padding: '10px 20px',
                                                borderRadius: '6px',
                                                border: 'none',
                                                backgroundColor: '#4f46e5',
                                                color: 'white',
                                                fontSize: '14px',
                                                fontWeight: '500',
                                                cursor: saving ? 'not-allowed' : 'pointer',
                                                opacity: saving ? 0.7 : 1
                                            }}
                                        >
                                            {saving ? 'Updating...' : 'Update SSO Configuration'}
                                        </button>
                                    </div>
                                </form>
                            ) : (
                                <div>
                                    <div style={{ marginBottom: '16px' }}>
                                        <div style={{ fontSize: '14px', fontWeight: '600', color: '#374151', marginBottom: '4px' }}>
                                            Provider Type
                                        </div>
                                        <div style={{ fontSize: '14px', color: '#6B7280' }}>
                                            {ssoConfig.provider_type.toUpperCase()}
                                        </div>
                                    </div>

                                    <div style={{ marginBottom: '16px' }}>
                                        <div style={{ fontSize: '14px', fontWeight: '600', color: '#374151', marginBottom: '4px' }}>
                                            Client ID
                                        </div>
                                        <div style={{ fontSize: '14px', color: '#6B7280', fontFamily: 'monospace' }}>
                                            {ssoConfig.client_id_masked}
                                        </div>
                                    </div>

                                    <div style={{ marginBottom: '16px' }}>
                                        <div style={{ fontSize: '14px', fontWeight: '600', color: '#374151', marginBottom: '4px' }}>
                                            Issuer URL
                                        </div>
                                        <div style={{ fontSize: '14px', color: '#6B7280' }}>
                                            {ssoConfig.issuer}
                                        </div>
                                    </div>

                                    {/* Mobile SSO Indicator */}
                                    {ssoConfig.has_mobile && (
                                        <div style={{
                                            marginTop: '20px',
                                            padding: '16px',
                                            backgroundColor: '#f0f9ff',
                                            borderRadius: '8px',
                                            border: '1px solid #bae6fd'
                                        }}>
                                            <div style={{ fontSize: '14px', fontWeight: '600', color: '#374151', marginBottom: '8px' }}>
                                                📱 Mobile SSO Configured
                                            </div>
                                            <div style={{ marginBottom: '8px' }}>
                                                <div style={{ fontSize: '13px', fontWeight: '500', color: '#6B7280', marginBottom: '4px' }}>
                                                    Mobile Client ID
                                                </div>
                                                <div style={{ fontSize: '14px', color: '#374151', fontFamily: 'monospace' }}>
                                                    {ssoConfig.mobile_client_id_masked}
                                                </div>
                                            </div>
                                            <p style={{ fontSize: '12px', color: '#0369a1', margin: 0 }}>
                                                Separate OAuth credentials configured for mobile applications
                                            </p>
                                        </div>
                                    )}

                                    <div style={{
                                        marginTop: '20px',
                                        padding: '12px',
                                        backgroundColor: '#eff6ff',
                                        borderRadius: '6px',
                                        fontSize: '13px',
                                        color: '#1e40af'
                                    }}>
                                        💡 Changes to SSO configuration will affect all users in your organization. Test carefully after updating.
                                    </div>
                                </div>
                            )
                        ) : (
                            <div style={{
                                padding: '24px',
                                textAlign: 'center',
                                color: '#6B7280'
                            }}>
                                No SSO configuration found. This should have been set during tenant activation.
                            </div>
                        )}
                    </div>
                )}
            </div>
        </AdminLayout>
    );
};

export default AccountSettingsPage;

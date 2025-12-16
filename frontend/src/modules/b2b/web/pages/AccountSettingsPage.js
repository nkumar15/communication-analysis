import React, { useState, useEffect } from 'react';
import useAuth from '../../../../core/hooks/useAuth';
import { accountApi } from '../../../../core/api/accountClient';
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

    const canEdit = hasRole(['owner', 'admin']);

    useEffect(() => {
        loadSettings();
    }, []);

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

    const handleCancel = () => {
        setError('');
        setSuccess('');
        loadSettings();
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

                <div style={{
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                    padding: '32px'
                }}>
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
            </div>
        </AdminLayout>
    );
};

export default AccountSettingsPage;

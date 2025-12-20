import React, { useState } from 'react';
import { auth } from '../../../../core/firebase/b2c-config';
import B2CLayout from '../layouts/B2CLayout';

const UserSettingsPage = () => {
    const currentUser = auth.currentUser;
    const [formData, setFormData] = useState({
        displayName: currentUser?.displayName || '',
        email: currentUser?.email || '',
        photoURL: currentUser?.photoURL || ''
    });
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState(null);

    const handleSave = async (e) => {
        e.preventDefault();
        setSaving(true);
        setMessage(null);

        try {
            // Mock save - will be replaced with real API
            await new Promise(resolve => setTimeout(resolve, 1000));

            setMessage({ type: 'success', text: 'Settings saved successfully!' });
        } catch (error) {
            setMessage({ type: 'error', text: 'Failed to save settings' });
        } finally {
            setSaving(false);
        }
    };

    return (
        <B2CLayout>
            <div style={{ maxWidth: '800px', margin: '0 auto' }}>
                <h1 style={{
                    fontSize: '32px',
                    fontWeight: '700',
                    color: '#111827',
                    marginBottom: '8px'
                }}>
                    Account Settings
                </h1>
                <p style={{
                    fontSize: '16px',
                    color: '#6B7280',
                    marginBottom: '32px'
                }}>
                    Manage your account preferences and profile information
                </p>

                {message && (
                    <div style={{
                        padding: '16px',
                        borderRadius: '8px',
                        marginBottom: '24px',
                        backgroundColor: message.type === 'success' ? '#D1FAE5' : '#FEE2E2',
                        color: message.type === 'success' ? '#065F46' : '#991B1B',
                        border: `1px solid ${message.type === 'success' ? '#A7F3D0' : '#FCA5A5'}`
                    }}>
                        {message.text}
                    </div>
                )}

                <form onSubmit={handleSave}>
                    {/* Profile Section */}
                    <div style={{
                        backgroundColor: 'white',
                        borderRadius: '12px',
                        padding: '28px',
                        border: '1px solid #E5E7EB',
                        marginBottom: '24px'
                    }}>
                        <h2 style={{
                            fontSize: '20px',
                            fontWeight: '600',
                            color: '#111827',
                            marginBottom: '20px'
                        }}>
                            Profile Information
                        </h2>

                        <div style={{ marginBottom: '20px' }}>
                            <label style={{
                                display: 'block',
                                marginBottom: '8px',
                                fontWeight: '600',
                                fontSize: '14px',
                                color: '#374151'
                            }}>
                                Display Name
                            </label>
                            <input
                                type="text"
                                value={formData.displayName}
                                onChange={(e) => setFormData({ ...formData, displayName: e.target.value })}
                                style={{
                                    width: '100%',
                                    padding: '12px 16px',
                                    border: '2px solid #E5E7EB',
                                    borderRadius: '8px',
                                    fontSize: '14px',
                                    backgroundColor: '#F9FAFB',
                                    outline: 'none'
                                }}
                            />
                        </div>

                        <div style={{ marginBottom: '20px' }}>
                            <label style={{
                                display: 'block',
                                marginBottom: '8px',
                                fontWeight: '600',
                                fontSize: '14px',
                                color: '#374151'
                            }}>
                                Email Address
                            </label>
                            <input
                                type="email"
                                value={formData.email}
                                disabled
                                style={{
                                    width: '100%',
                                    padding: '12px 16px',
                                    border: '2px solid #E5E7EB',
                                    borderRadius: '8px',
                                    fontSize: '14px',
                                    backgroundColor: '#F3F4F6',
                                    color: '#6B7280',
                                    cursor: 'not-allowed'
                                }}
                            />
                            <p style={{
                                fontSize: '12px',
                                color: '#6B7280',
                                marginTop: '6px'
                            }}>
                                Contact support to change your email address
                            </p>
                        </div>
                    </div>

                    {/* Preferences */}
                    <div style={{
                        backgroundColor: 'white',
                        borderRadius: '12px',
                        padding: '28px',
                        border: '1px solid #E5E7EB',
                        marginBottom: '24px'
                    }}>
                        <h2 style={{
                            fontSize: '20px',
                            fontWeight: '600',
                            color: '#111827',
                            marginBottom: '20px'
                        }}>
                            Preferences
                        </h2>

                        <div style={{
                            padding: '16px',
                            backgroundColor: '#F9FAFB',
                            borderRadius: '8px',
                            color: '#6B7280'
                        }}>
                            Email notifications and other preferences coming soon
                        </div>
                    </div>

                    {/* Actions */}
                    <div style={{
                        display: 'flex',
                        justifyContent: 'flex-end',
                        gap: '12px'
                    }}>
                        <button
                            type="submit"
                            disabled={saving}
                            style={{
                                padding: '14px 32px',
                                borderRadius: '8px',
                                border: 'none',
                                background: saving ? '#9CA3AF' : 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)',
                                color: 'white',
                                fontSize: '14px',
                                fontWeight: '600',
                                cursor: saving ? 'not-allowed' : 'pointer',
                                boxShadow: saving ? 'none' : '0 4px 12px rgba(99, 102, 241, 0.4)'
                            }}
                        >
                            {saving ? 'Saving...' : 'Save Changes'}
                        </button>
                    </div>
                </form>
            </div>
        </B2CLayout>
    );
};

export default UserSettingsPage;

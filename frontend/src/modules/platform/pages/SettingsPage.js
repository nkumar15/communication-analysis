import React from 'react';

function SettingsPage() {
    return (
        <div>
            <div className="platform-page-header">
                <h1 className="platform-page-title">Platform Settings</h1>
            </div>

            <div className="platform-card">
                <h2 style={{ fontSize: '1.1rem', fontWeight: '600', marginBottom: '1.5rem', color: '#1f2937', borderBottom: '1px solid #e5e7eb', paddingBottom: '0.75rem' }}>General Configuration</h2>

                <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>Platform Name</label>
                    <input
                        type="text"
                        defaultValue="SaaS Admin"
                        disabled
                        style={{
                            width: '100%',
                            maxWidth: '400px',
                            padding: '0.5rem 0.75rem',
                            border: '1px solid #d1d5db',
                            borderRadius: '0.375rem',
                            backgroundColor: '#f3f4f6',
                            color: '#6b7280'
                        }}
                    />
                    <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>System-wide platform name.</p>
                </div>

                <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>Support Email</label>
                    <input
                        type="email"
                        defaultValue="support@platform.net"
                        disabled
                        style={{
                            width: '100%',
                            maxWidth: '400px',
                            padding: '0.5rem 0.75rem',
                            border: '1px solid #d1d5db',
                            borderRadius: '0.375rem',
                            backgroundColor: '#f3f4f6',
                            color: '#6b7280'
                        }}
                    />
                </div>
            </div>
        </div>
    );
}

export default SettingsPage;

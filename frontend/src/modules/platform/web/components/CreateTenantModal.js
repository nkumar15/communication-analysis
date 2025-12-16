import { useState } from 'react';
import platformApiService from '../../../../core/api/platformClient';

function CreateTenantModal({ onClose, onCreated }) {
    const [formData, setFormData] = useState({
        company_name: '',
        domain: '',
        owner_email: ''
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);


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
                owner_email: formData.owner_email
            };

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

                        {/* SSO Configuration - Moved to activation flow */}
                        <div style={{ padding: '12px', marginBottom: '20px', backgroundColor: '#F3F4F6', borderRadius: '6px', fontSize: '14px', color: '#4B5563' }}>
                            <span style={{ marginRight: '6px' }}>ℹ️</span>
                            SSO configuration will be done by the tenant admin during activation.
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

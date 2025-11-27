import { useState } from 'react';
import apiService from '../services/api';

function CreateTenantModal({ onClose, onCreated }) {
    const [formData, setFormData] = useState({
        name: '',
        domain: '',
        admin_email: '',
        plan: 'free'
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

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
            await apiService.post('/api/platform/tenants', formData);
            onCreated();
            onClose();
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="modal-overlay" style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000
        }}>
            <div className="modal-content" style={{
                background: '#2d2d44', padding: '2rem', borderRadius: '12px',
                width: '100%', maxWidth: '500px', border: '1px solid rgba(255,255,255,0.1)'
            }}>
                <h2 style={{ marginBottom: '1.5rem' }}>Create New Tenant</h2>

                {error && (
                    <div className="error-message" style={{ marginBottom: '1rem' }}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>Tenant Name</label>
                        <input
                            type="text"
                            name="name"
                            className="email-input"
                            value={formData.name}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label>Domain</label>
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
                        <label>Admin Email</label>
                        <input
                            type="email"
                            name="admin_email"
                            className="email-input"
                            value={formData.admin_email}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label>Plan</label>
                        <select
                            name="plan"
                            className="email-input"
                            value={formData.plan}
                            onChange={handleChange}
                        >
                            <option value="free">Free Tier</option>
                            <option value="pro">Pro Plan</option>
                            <option value="enterprise">Enterprise</option>
                        </select>
                    </div>

                    <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
                        <button
                            type="button"
                            onClick={onClose}
                            className="saas-btn saas-btn-outline"
                            style={{ flex: 1 }}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="submit-button"
                            style={{ flex: 1, margin: 0 }}
                            disabled={loading}
                        >
                            {loading ? 'Creating...' : 'Create Tenant'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

export default CreateTenantModal;

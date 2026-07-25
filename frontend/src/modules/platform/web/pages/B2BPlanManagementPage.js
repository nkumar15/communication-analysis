import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import platformClient from '../../../../core/api/platformClient';

const B2BPlanManagementPage = () => {
    const navigate = useNavigate();
    const [plans, setPlans] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [formData, setFormData] = useState({
        tier_key: '',
        name: '',
        description: '',
        base_price_monthly: 0,
        base_price_yearly: 0,
        per_seat_price_monthly: 0,
        per_seat_price_yearly: 0,
        limits: { projects: 10, storage_gb: 10 },
        features: { sso: false, audit_logs: false },
        provider_config: { stripe: { monthly_price_id: '', yearly_price_id: '' } },
        contact_required: false
    });

    useEffect(() => {
        loadPlans();
    }, []);

    const loadPlans = async () => {
        try {
            const data = await platformClient.getB2BPlans();
            setPlans(data);
        } catch (error) {
            console.error('Failed to load plans:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        try {
            await platformClient.createB2BPlan(formData);
            setShowCreateModal(false);
            loadPlans();
        } catch (error) {
            alert('Failed to create plan: ' + error.message);
        }
    };

    const handleArchive = async (planId) => {
        if (!window.confirm('Are you sure you want to archive this plan?')) return;
        try {
            await platformClient.archiveB2BPlan(planId);
            loadPlans();
        } catch (error) {
            alert('Failed to archive plan');
        }
    };

    if (loading) return <div>Loading...</div>;

    return (
        <div style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>B2B Plans</h1>
                <button
                    onClick={() => setShowCreateModal(true)}
                    style={{
                        padding: '10px 20px',
                        backgroundColor: '#4F46E5',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer'
                    }}
                >
                    Create New Version
                </button>
            </div>

            <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', borderRadius: '8px', overflow: 'hidden', border: '1px solid #E5E7EB' }}>
                    <thead style={{ backgroundColor: '#F9FAFB' }}>
                        <tr>
                            <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Tier</th>
                            <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Name</th>
                            <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Price Configuration</th>
                            <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Effective From</th>
                            <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Status</th>
                            <th style={{ padding: '12px 16px', textAlign: 'right', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Actions</th>
                        </tr>
                    </thead>
                    <tbody style={{ backgroundColor: 'white' }}>
                        {plans.map((plan) => {
                            const isEnterprise = plan.tier_key === 'enterprise' || plan.contact_required;

                            return (
                                <tr key={plan.id} style={{ borderTop: '1px solid #E5E7EB' }}>
                                    <td style={{ padding: '12px 16px' }}>
                                        <span style={{
                                            padding: '2px 8px', borderRadius: '9999px', fontSize: '12px', fontWeight: '500',
                                            backgroundColor: plan.tier_key === 'starter' ? '#E5E7EB' : (plan.tier_key === 'professional' ? '#E0E7FF' : '#FEE2E2'),
                                            color: plan.tier_key === 'starter' ? '#374151' : (plan.tier_key === 'professional' ? '#4338CA' : '#991B1B')
                                        }}>
                                            {plan.tier_key}
                                        </span>
                                    </td>
                                    <td style={{ padding: '12px 16px', fontWeight: '500', color: '#111827' }}>
                                        {plan.name}
                                        <div style={{ fontSize: '12px', color: '#6B7280', fontWeight: 'normal' }}>{plan.description}</div>
                                    </td>
                                    <td style={{ padding: '12px 16px', color: '#6B7280', fontSize: '14px' }}>
                                        {isEnterprise ? (
                                            <span style={{ fontWeight: '600', color: '#111827' }}>Contact Us (Custom)</span>
                                        ) : (
                                            <div style={{ display: 'grid', gap: '4px' }}>
                                                <div>Base: ${(plan.base_price_monthly / 100).toFixed(2)}/mo</div>
                                                <div>Seat: ${(plan.per_seat_price_monthly / 100).toFixed(2)}/mo</div>
                                            </div>
                                        )}
                                    </td>
                                    <td style={{ padding: '12px 16px', color: '#6B7280' }}>
                                        {plan.effective_from ? new Date(plan.effective_from).toLocaleDateString() : 'Immediate'}
                                    </td>
                                    <td style={{ padding: '12px 16px' }}>
                                        <span style={{
                                            display: 'inline-flex', alignItems: 'center',
                                            color: plan.archived_at ? '#EF4444' : '#10B981',
                                            fontSize: '14px'
                                        }}>
                                            {plan.archived_at ? 'Archived' : 'Active'}
                                        </span>
                                    </td>
                                    <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                                        {!plan.archived_at && (
                                            <button
                                                onClick={() => handleArchive(plan.id)}
                                                style={{ color: '#EF4444', background: 'none', border: 'none', cursor: 'pointer', fontWeight: '500' }}
                                            >
                                                Archive
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {showCreateModal && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    zIndex: 50
                }}>
                    <div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '24px', width: '500px', maxHeight: '90vh', overflowY: 'auto' }}>
                        <h2 style={{ fontSize: '20px', fontWeight: 'bold', marginBottom: '16px' }}>Create New Plan Version</h2>
                        <form onSubmit={handleCreate}>
                            <div style={{ marginBottom: '16px' }}>
                                <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500' }}>Tier Key</label>
                                <select
                                    value={formData.tier_key}
                                    onChange={e => setFormData({ ...formData, tier_key: e.target.value })}
                                    style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #D1D5DB' }}
                                    required
                                >
                                    <option value="">Select Tier</option>
                                    <option value="starter">Starter</option>
                                    <option value="professional">Professional</option>
                                    <option value="enterprise">Enterprise</option>
                                </select>
                            </div>
                            <div style={{ marginBottom: '16px' }}>
                                <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500' }}>Name</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                                    style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #D1D5DB' }}
                                    required
                                />
                            </div>

                            <div style={{ marginBottom: '16px' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontWeight: '500', color: '#374151' }}>
                                    <input
                                        type="checkbox"
                                        checked={formData.contact_required}
                                        onChange={e => setFormData({ ...formData, contact_required: e.target.checked })}
                                    />
                                    Is Contact Required? (No Pricing)
                                </label>
                            </div>

                            {!formData.contact_required && (
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', fontWeight: '500' }}>Base Price (Cents/Mo)</label>
                                        <input
                                            type="number"
                                            value={formData.base_price_monthly}
                                            onChange={e => setFormData({ ...formData, base_price_monthly: parseInt(e.target.value) })}
                                            style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #D1D5DB' }}
                                        />
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', fontWeight: '500' }}>Per Seat (Cents/Mo)</label>
                                        <input
                                            type="number"
                                            value={formData.per_seat_price_monthly}
                                            onChange={e => setFormData({ ...formData, per_seat_price_monthly: parseInt(e.target.value) })}
                                            style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #D1D5DB' }}
                                        />
                                    </div>
                                </div>
                            )}

                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
                                <button
                                    type="button"
                                    onClick={() => setShowCreateModal(false)}
                                    style={{ padding: '8px 16px', border: '1px solid #D1D5DB', borderRadius: '6px', background: 'white', cursor: 'pointer' }}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    style={{ padding: '8px 16px', backgroundColor: '#4F46E5', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
                                >
                                    Create Plan
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default B2BPlanManagementPage;

import React, { useState, useEffect } from 'react';
import PlatformLayout from '../layouts/PlatformLayout';
import platformClient from '../../../../core/api/platformClient';

const PlanManagementPage = () => {
    const [plans, setPlans] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);

    // New plan form state
    const [newPlan, setNewPlan] = useState({
        tier_key: 'premium',
        name: '',
        description: '',
        price_monthly: 0,
        price_yearly: 0,
        provider_config: { stripe: { monthly_price_id: '', yearly_price_id: '' } },
        limits: { projects: 10, team_members: 5, storage_gb: 10 },
        features: { priority_support: true, custom_branding: false }
    });

    useEffect(() => {
        loadPlans();
    }, []);

    const loadPlans = async () => {
        setLoading(true);
        try {
            const data = await platformClient.getPlans();
            setPlans(data);
        } catch (error) {
            console.error('Failed to load plans:', error);
            alert('Failed to load plans');
        } finally {
            setLoading(false);
        }
    };

    const handleCreatePlan = async (e) => {
        e.preventDefault();
        try {
            // Ensure numbers
            const payload = {
                ...newPlan,
                price_monthly: parseInt(newPlan.price_monthly),
                price_yearly: parseInt(newPlan.price_yearly)
            };

            await platformClient.createPlan(payload);
            setShowCreateModal(false);
            loadPlans();
            alert('Plan version created successfully!');
        } catch (error) {
            console.error('Create plan error:', error);
            alert('Failed to create plan');
        }
    };

    const handleArchivePlan = async (planId) => {
        if (!window.confirm('Are you sure you want to archive this plan version? It will no longer be available for new subscriptions.')) return;

        try {
            await platformClient.archivePlan(planId);
            loadPlans();
        } catch (error) {
            console.error('Archive error:', error);
            alert('Failed to archive plan');
        }
    };

    // Helper to group plans by tier for display if needed, or just list flat
    // Flat list sorted by tier/date is simple enough given backend sort.

    return (
        <PlatformLayout>
            <div style={{ padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                    <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>Subscription Plans</h1>
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

                {loading ? (
                    <div>Loading...</div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', borderRadius: '8px', overflow: 'hidden', border: '1px solid #E5E7EB' }}>
                            <thead style={{ backgroundColor: '#F9FAFB' }}>
                                <tr>
                                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Tier</th>
                                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Name</th>
                                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Price (M/Y)</th>
                                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Effective From</th>
                                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Status</th>
                                    <th style={{ padding: '12px 16px', textAlign: 'right', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody style={{ backgroundColor: 'white' }}>
                                {plans.map((plan) => (
                                    <tr key={plan.id} style={{ borderTop: '1px solid #E5E7EB' }}>
                                        <td style={{ padding: '12px 16px' }}>
                                            <span style={{
                                                padding: '2px 8px', borderRadius: '9999px', fontSize: '12px', fontWeight: '500',
                                                backgroundColor: plan.tier_key === 'free' ? '#E5E7EB' : (plan.tier_key === 'premium' ? '#E0E7FF' : '#D1FAE5'),
                                                color: plan.tier_key === 'free' ? '#374151' : (plan.tier_key === 'premium' ? '#4338CA' : '#065F46')
                                            }}>
                                                {plan.tier_key}
                                            </span>
                                        </td>
                                        <td style={{ padding: '12px 16px', fontWeight: '500', color: '#111827' }}>{plan.name}</td>
                                        <td style={{ padding: '12px 16px', color: '#6B7280' }}>
                                            ${(plan.price_monthly / 100).toFixed(2)} / ${(plan.price_yearly / 100).toFixed(2)}
                                        </td>
                                        <td style={{ padding: '12px 16px', color: '#6B7280' }}>
                                            {new Date(plan.effective_from).toLocaleDateString()}
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
                                                    onClick={() => handleArchivePlan(plan.id)}
                                                    style={{ color: '#EF4444', background: 'none', border: 'none', cursor: 'pointer', fontWeight: '500' }}
                                                >
                                                    Archive
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Create Modal (Simplified) */}
                {showCreateModal && (
                    <div style={{
                        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                        backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        zIndex: 50
                    }}>
                        <div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '24px', width: '500px', maxHeight: '90vh', overflowY: 'auto' }}>
                            <h2 style={{ fontSize: '20px', fontWeight: 'bold', marginBottom: '16px' }}>Create New Plan Version</h2>
                            <form onSubmit={handleCreatePlan}>
                                <div style={{ marginBottom: '16px' }}>
                                    <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500' }}>Tier Key</label>
                                    <select
                                        style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #D1D5DB' }}
                                        value={newPlan.tier_key}
                                        onChange={e => setNewPlan({ ...newPlan, tier_key: e.target.value })}
                                    >
                                        <option value="premium">Premium</option>
                                        <option value="ultimate">Ultimate</option>
                                        <option value="free">Free</option>
                                    </select>
                                </div>
                                <div style={{ marginBottom: '16px' }}>
                                    <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500' }}>Name</label>
                                    <input
                                        type="text" required
                                        style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #D1D5DB' }}
                                        value={newPlan.name}
                                        onChange={e => setNewPlan({ ...newPlan, name: e.target.value })}
                                    />
                                </div>
                                <div style={{ marginBottom: '16px' }}>
                                    <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500' }}>Description</label>
                                    <textarea
                                        style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #D1D5DB' }}
                                        value={newPlan.description}
                                        onChange={e => setNewPlan({ ...newPlan, description: e.target.value })}
                                    />
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500' }}>Monthly Price (cents)</label>
                                        <input
                                            type="number" required
                                            style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #D1D5DB' }}
                                            value={newPlan.price_monthly}
                                            onChange={e => setNewPlan({ ...newPlan, price_monthly: e.target.value })}
                                        />
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500' }}>Yearly Price (cents)</label>
                                        <input
                                            type="number" required
                                            style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #D1D5DB' }}
                                            value={newPlan.price_yearly}
                                            onChange={e => setNewPlan({ ...newPlan, price_yearly: e.target.value })}
                                        />
                                    </div>
                                </div>

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
        </PlatformLayout>
    );
};

export default PlanManagementPage;

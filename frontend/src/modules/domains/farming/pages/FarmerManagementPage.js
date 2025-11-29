// FarmerManagementPage.js – UI for managing farmers
import React, { useEffect, useState } from 'react';
import apiService from '../../../../core/api/b2bClient';
import AdminLayout from '../../../b2b/layouts/AdminLayout';

const FarmerManagementPage = () => {
    const [farmers, setFarmers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchFarmers = async () => {
            try {
                const data = await apiService.getFarmers();
                setFarmers(data);
            } catch (e) {
                console.error('Failed to fetch farmers', e);
                setError('Unable to load farmers');
            } finally {
                setLoading(false);
            }
        };
        fetchFarmers();
    }, []);

    if (loading) return <div className="loading">Loading farmers...</div>;
    if (error) return <div className="error">{error}</div>;

    return (
        <AdminLayout title="Farmer Management" subtitle="Manage farmers and their data">
            <div style={{ padding: '32px', maxWidth: '1400px', margin: '0 auto' }}>
                <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderTop: '1px solid #E5E7EB', borderBottom: '1px solid #E5E7EB', backgroundColor: '#F9FAFB' }}>
                                    <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Name</th>
                                    <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Email</th>
                                    <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Phone</th>
                                    <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Address</th>
                                </tr>
                            </thead>
                            <tbody>
                                {farmers.map((f) => (
                                    <tr key={f.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                        <td style={{ padding: '16px 24px', fontWeight: '500', color: '#111827' }}>{f.name}</td>
                                        <td style={{ padding: '16px 24px', color: '#6B7280' }}>{f.email}</td>
                                        <td style={{ padding: '16px 24px', color: '#6B7280' }}>{f.phone}</td>
                                        <td style={{ padding: '16px 24px', color: '#6B7280' }}>{f.address}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {farmers.length === 0 && (
                            <div style={{ padding: '60px 24px', textAlign: 'center', color: '#9CA3AF' }}>
                                No farmers found
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </AdminLayout>
    );
};

export default FarmerManagementPage;

// RoleManagementPage.js – UI for managing roles and permissions
import React, { useEffect, useState } from 'react';
import apiService from '../services/api';
import AdminLayout from './layout/AdminLayout';
import './Card.css';
import './RoleManagementPage.css';

const RoleManagementPage = () => {
    const [roles, setRoles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchRoles = async () => {
            try {
                const data = await apiService.getRoles();
                setRoles(data);
            } catch (e) {
                console.error('Failed to fetch roles', e);
                setError('Unable to load roles');
            } finally {
                setLoading(false);
            }
        };
        fetchRoles();
    }, []);

    if (loading) return <div className="loading">Loading roles...</div>;
    if (error) return <div className="error">{error}</div>;

    return (
        <AdminLayout title="Role Management" subtitle="Manage user roles and permissions">
            <div style={{ padding: '32px', maxWidth: '1400px', margin: '0 auto' }}>
                <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderTop: '1px solid #E5E7EB', borderBottom: '1px solid #E5E7EB', backgroundColor: '#F9FAFB' }}>
                                    <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Name</th>
                                    <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Display Name</th>
                                    <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Permissions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {roles.map((role) => (
                                    <tr key={role.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                        <td style={{ padding: '16px 24px', fontWeight: '500', color: '#111827' }}>{role.name}</td>
                                        <td style={{ padding: '16px 24px', color: '#6B7280' }}>{role.display_name}</td>
                                        <td style={{ padding: '16px 24px', color: '#6B7280' }}>
                                            {role.permissions && role.permissions.length > 0 ? (
                                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                                                    {role.permissions.map((perm) => (
                                                        <span key={perm.id} style={{
                                                            display: 'inline-flex',
                                                            alignItems: 'center',
                                                            padding: '2px 8px',
                                                            borderRadius: '4px',
                                                            backgroundColor: '#EEF2FF',
                                                            color: '#4F46E5',
                                                            fontSize: '12px',
                                                            fontWeight: '500'
                                                        }}>
                                                            {perm.resource}:{perm.action}
                                                        </span>
                                                    ))}
                                                </div>
                                            ) : (
                                                <span style={{ color: '#9CA3AF', fontStyle: 'italic' }}>No permissions</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </AdminLayout>
    );
};

export default RoleManagementPage;

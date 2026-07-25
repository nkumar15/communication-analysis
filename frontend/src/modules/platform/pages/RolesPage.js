import React, { useState, useEffect } from 'react';
import api from '../../../core/api/platformClient';

const RolesPage = () => {
    const [roles, setRoles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchRoles();
    }, []);

    const fetchRoles = async () => {
        try {
            setLoading(true);
            const response = await api.get('/api/platform/roles/');
            setRoles(response);
            setLoading(false);
        } catch (err) {
            setError('Failed to load roles');
            setLoading(false);
            console.error(err);
        }
    };

    if (loading) {
        return (
            <div className="p-10">
                <div className="animate-pulse">
                    <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
                    <div className="bg-white rounded-lg shadow">
                        <div className="h-64 bg-gray-100"></div>
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-10">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
                    {error}
                </div>
            </div>
        );
    }

    return (
        <div style={{ padding: '2.5rem' }}>
            {/* Header */}
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 style={{
                        fontSize: '24px',
                        fontWeight: 600,
                        color: '#111827',
                        marginBottom: '4px'
                    }}>
                        Platform Roles
                    </h1>
                    <p style={{ fontSize: '14px', color: '#6B7280' }}>
                        Manage platform-level roles and permissions
                    </p>
                </div>
                <button
                    disabled
                    style={{
                        backgroundColor: '#E5E7EB',
                        color: '#9CA3AF',
                        padding: '12px 20px',
                        borderRadius: '8px',
                        fontSize: '14px',
                        fontWeight: 500,
                        cursor: 'not-allowed',
                        border: 'none'
                    }}
                    title="Custom role creation coming soon"
                >
                    + Create Role
                </button>
            </div>

            {/* Roles Table */}
            <div style={{ backgroundColor: '#FFFFFF', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead style={{ backgroundColor: '#F9FAFB', borderBottom: '1px solid #E5E7EB' }}>
                        <tr>
                            <th style={{
                                padding: '16px 24px',
                                textAlign: 'left',
                                fontSize: '12px',
                                fontWeight: 500,
                                color: '#6B7280',
                                textTransform: 'uppercase',
                                letterSpacing: '0.05em'
                            }}>
                                Role Name
                            </th>
                            <th style={{
                                padding: '16px 24px',
                                textAlign: 'left',
                                fontSize: '12px',
                                fontWeight: 500,
                                color: '#6B7280',
                                textTransform: 'uppercase',
                                letterSpacing: '0.05em'
                            }}>
                                Type
                            </th>
                            <th style={{
                                padding: '16px 24px',
                                textAlign: 'left',
                                fontSize: '12px',
                                fontWeight: 500,
                                color: '#6B7280',
                                textTransform: 'uppercase',
                                letterSpacing: '0.05em'
                            }}>
                                Permissions
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {roles.map((role, index) => (
                            <tr
                                key={role.id}
                                style={{
                                    borderBottom: index < roles.length - 1 ? '1px solid #F3F4F6' : 'none',
                                    transition: 'background-color 0.15s ease'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#F9FAFB'}
                                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                            >
                                <td style={{ padding: '20px 24px' }}>
                                    <div style={{ fontSize: '14px', fontWeight: 500, color: '#111827', marginBottom: '2px' }}>
                                        {role.display_name}
                                    </div>
                                    <div style={{ fontSize: '12px', color: '#6B7280' }}>
                                        {role.name}
                                    </div>
                                </td>
                                <td style={{ padding: '20px 24px' }}>
                                    {role.is_system_role ? (
                                        <span style={{
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            padding: '4px 12px',
                                            borderRadius: '16px',
                                            fontSize: '12px',
                                            fontWeight: 500,
                                            backgroundColor: '#EDE9FE',
                                            color: '#8B5CF6'
                                        }}>
                                            System
                                        </span>
                                    ) : (
                                        <span style={{
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            padding: '4px 12px',
                                            borderRadius: '16px',
                                            fontSize: '12px',
                                            fontWeight: 500,
                                            backgroundColor: '#D1FAE5',
                                            color: '#059669'
                                        }}>
                                            Custom
                                        </span>
                                    )}
                                </td>
                                <td style={{ padding: '20px 24px' }}>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                        {role.permissions && role.permissions.length > 0 ? (
                                            role.permissions.map((perm, idx) => (
                                                <span
                                                    key={idx}
                                                    style={{
                                                        display: 'inline-flex',
                                                        alignItems: 'center',
                                                        padding: '4px 10px',
                                                        borderRadius: '6px',
                                                        fontSize: '12px',
                                                        fontWeight: 400,
                                                        backgroundColor: '#F3F4F6',
                                                        color: '#374151',
                                                        border: '1px solid #E5E7EB'
                                                    }}
                                                >
                                                    <span style={{ fontWeight: 500, color: '#8B5CF6' }}>
                                                        {perm.resource}
                                                    </span>
                                                    <span style={{ margin: '0 4px', color: '#9CA3AF' }}>:</span>
                                                    <span>{perm.action}</span>
                                                </span>
                                            ))
                                        ) : (
                                            <span style={{ fontSize: '12px', color: '#9CA3AF' }}>
                                                No specific permissions
                                            </span>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Stats Footer */}
            <div style={{ marginTop: '16px', fontSize: '12px', color: '#6B7280' }}>
                Showing {roles.length} role{roles.length !== 1 ? 's' : ''}
            </div>
        </div>
    );
};

export default RolesPage;

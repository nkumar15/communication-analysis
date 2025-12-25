// RoleManagementPage.js – UI for managing roles and permissions
import React, { useEffect, useState } from 'react';
import apiService from '../../../../core/api/b2bClient';
import AdminLayout from '../layouts/AdminLayout';
import { TableSkeleton } from '../../../../core/components/LoadingSkeleton';

const RoleManagementPage = () => {
    const [roles, setRoles] = useState([]);
    const [templates, setTemplates] = useState([]);
    const [resources, setResources] = useState([]);
    const [actions, setActions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [showCreateModal, setShowCreateModal] = useState(false);

    const [creating, setCreating] = useState(false);
    const [newRole, setNewRole] = useState({
        name: '',
        display_name: '',
        description: '',
        template_id: ''
    });
    const [selectedPermissions, setSelectedPermissions] = useState({});

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [rolesData, templatesData, resourcesData, actionsData] = await Promise.all([
                apiService.getRoles(),
                apiService.getRoleTemplates(),
                apiService.getResources(),
                apiService.getActions()
            ]);
            setRoles(rolesData);
            setTemplates(templatesData);
            setResources(resourcesData);
            setActions(actionsData.actions || []);
        } catch (e) {
            console.error('Failed to fetch data', e);
            setError('Failed to load role data');
        } finally {
            setLoading(false);
        }
    };

    const handleTemplateChange = (templateId) => {
        const template = templates.find(t => t.id === templateId);
        setNewRole({ ...newRole, template_id: templateId });

        // Pre-fill permissions based on template
        if (template && template.permissions) {
            const newPerms = {};
            template.permissions.forEach(p => {
                const resource = resources.find(r => r.name === p.resource);
                const actionList = p.actions || [];

                if (resource) {
                    actionList.forEach(actionName => {
                        const action = actions.find(a => a.name === actionName);
                        if (action) {
                            newPerms[`${resource.id}___${action.id}`] = true;
                        }
                    });
                }
            });
            setSelectedPermissions(newPerms);
        } else {
            setSelectedPermissions({});
        }
    };

    const handlePermissionChange = (resourceId, actionId) => {
        const key = `${resourceId}___${actionId}`;
        setSelectedPermissions(prev => ({
            ...prev,
            [key]: !prev[key]
        }));
    };

    const handleCreateRole = async (e) => {
        e.preventDefault();
        setCreating(true);
        setError(null);
        setSuccess(null);
        try {
            // ... logic
            // Convert selectedPermissions map to list of objects
            const permissionsList = Object.keys(selectedPermissions)
                .filter(key => selectedPermissions[key])
                .map(key => {
                    const parts = key.split('___');
                    if (parts.length !== 2) return null;
                    const [resourceId, actionId] = parts;
                    if (!resourceId || resourceId === 'undefined' || !actionId || actionId === 'undefined') {
                        return null;
                    }
                    return { resource_id: resourceId, action_id: actionId };
                })
                .filter(Boolean);

            const roleData = {
                ...newRole,
                template_id: newRole.template_id || null, // Convert empty string to null
                permissions: permissionsList
            };

            await apiService.createRole(roleData);
            setShowCreateModal(false);
            setNewRole({ name: '', display_name: '', description: '', template_id: '' });
            setSelectedPermissions({});
            setSuccess(`Role "${newRole.display_name}" created successfully`);
            fetchData(); // Refresh list
            setTimeout(() => setSuccess(null), 3000);
        } catch (e) {
            console.error('Failed to create role', e);
            setError('Failed to create role: ' + e.message);
        } finally {
            setCreating(false);
        }
    };

    const handleDeleteRole = async (roleId) => {
        if (!window.confirm('Are you sure you want to delete this role?')) return;
        setError(null);
        setSuccess(null);
        try {
            await apiService.deleteRole(roleId);
            setSuccess('Role deleted successfully');
            fetchData(); // Refresh list
            setTimeout(() => setSuccess(null), 3000);
        } catch (e) {
            console.error('Failed to delete role', e);
            setError('Failed to delete role: ' + e.message);
        }
    };

    if (loading) return (
        <AdminLayout title="Role Management" subtitle="Manage user roles and permissions">
            <div style={{ padding: '32px', maxWidth: '1400px', margin: '0 auto' }}>
                <TableSkeleton rows={6} />
            </div>
        </AdminLayout>
    );

    return (
        <AdminLayout title="Role Management" subtitle="Manage user roles and permissions">
            <div style={{ padding: '32px', maxWidth: '1400px', margin: '0 auto' }}>

                {error && <div className="error" style={{ marginBottom: '16px', color: '#DC2626', backgroundColor: '#FEE2E2', padding: '12px', borderRadius: '8px' }}>{error}</div>}

                {success && (
                    <div className="success" style={{ marginBottom: '16px', color: '#16A34A', backgroundColor: '#DCFCE7', padding: '12px', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        {success}
                        <button onClick={() => setSuccess(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: '16px' }}>×</button>
                    </div>
                )}

                <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'flex-end' }}>
                    <button
                        onClick={() => {
                            setShowCreateModal(true);
                            if (templates.length > 0) {
                                handleTemplateChange(templates[0].id);
                            }
                        }}
                        style={{
                            backgroundColor: '#4F46E5',
                            color: 'white',
                            padding: '10px 20px',
                            borderRadius: '6px',
                            border: 'none',
                            fontWeight: '500',
                            cursor: 'pointer'
                        }}
                    >
                        Create Role
                    </button>
                </div>

                <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderTop: '1px solid #E5E7EB', borderBottom: '1px solid #E5E7EB', backgroundColor: '#F9FAFB' }}>
                                    <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Display Name</th>
                                    <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Name</th>
                                    <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Permissions</th>
                                    <th style={{ padding: '12px 24px', textAlign: 'right', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {roles.map((role) => (
                                    <tr key={role.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                        <td style={{ padding: '16px 24px', fontWeight: '500', color: '#111827' }}>{role.display_name}</td>
                                        <td style={{ padding: '16px 24px', color: '#6B7280', fontSize: '13px' }}>
                                            <code style={{
                                                backgroundColor: '#F3F4F6',
                                                padding: '2px 6px',
                                                borderRadius: '3px',
                                                fontSize: '12px'
                                            }}>
                                                {role.name}
                                            </code>
                                        </td>
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
                                                            {perm.resource.display_name}:{perm.action.display_name}
                                                        </span>
                                                    ))}
                                                </div>
                                            ) : (
                                                <span style={{ color: '#9CA3AF', fontStyle: 'italic' }}>No permissions</span>
                                            )}
                                        </td>
                                        <td style={{ padding: '16px 24px', textAlign: 'right' }}>
                                            {!role.is_system_role && (
                                                <button
                                                    onClick={() => handleDeleteRole(role.id)}
                                                    style={{ color: '#EF4444', background: 'none', border: 'none', cursor: 'pointer', fontWeight: '500' }}
                                                >
                                                    Delete
                                                </button>
                                            )}
                                            {role.is_system_role && (
                                                <span style={{ color: '#9CA3AF', fontSize: '12px' }}>System Role</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Create Role Modal */}
                {showCreateModal && (
                    <div style={{
                        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                        backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
                    }}>
                        <div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '24px', width: '100%', maxWidth: '800px', maxHeight: '90vh', overflowY: 'auto' }}>
                            <h2 style={{ marginTop: 0, marginBottom: '16px', fontSize: '20px', fontWeight: '600' }}>Create New Role</h2>
                            <form onSubmit={handleCreateRole}>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                                    <div style={{ marginBottom: '16px' }}>
                                        <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>Name (Identifier)</label>
                                        <input
                                            type="text"
                                            value={newRole.name}
                                            onChange={(e) => setNewRole({ ...newRole, name: e.target.value })}
                                            placeholder="e.g. field_manager"
                                            required
                                            style={{ width: '100%', padding: '8px 12px', borderRadius: '4px', border: '1px solid #D1D5DB' }}
                                        />
                                    </div>
                                    <div style={{ marginBottom: '16px' }}>
                                        <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>Display Name</label>
                                        <input
                                            type="text"
                                            value={newRole.display_name}
                                            onChange={(e) => setNewRole({ ...newRole, display_name: e.target.value })}
                                            placeholder="e.g. Field Manager"
                                            required
                                            style={{ width: '100%', padding: '8px 12px', borderRadius: '4px', border: '1px solid #D1D5DB' }}
                                        />
                                    </div>
                                </div>
                                <div style={{ marginBottom: '16px' }}>
                                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>Description</label>
                                    <textarea
                                        value={newRole.description}
                                        onChange={(e) => setNewRole({ ...newRole, description: e.target.value })}
                                        style={{ width: '100%', padding: '8px 12px', borderRadius: '4px', border: '1px solid #D1D5DB' }}
                                    />
                                </div>
                                <div style={{ marginBottom: '24px' }}>
                                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>
                                        Template <span style={{ color: '#DC2626' }}>*</span>
                                    </label>
                                    <select
                                        value={newRole.template_id}
                                        onChange={(e) => handleTemplateChange(e.target.value)}
                                        required
                                        style={{ width: '100%', padding: '8px 12px', borderRadius: '4px', border: '1px solid #D1D5DB' }}
                                    >
                                        {templates.map(t => (
                                            <option key={t.id} value={t.id}>{t.display_name}</option>
                                        ))}
                                    </select>
                                    <p style={{ fontSize: '12px', color: '#6B7280', marginTop: '4px' }}>
                                        Selecting a template will pre-fill permissions below. You can customize them.
                                    </p>
                                </div>

                                <div style={{ marginBottom: '24px' }}>
                                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>Permissions</label>
                                    <div style={{ border: '1px solid #E5E7EB', borderRadius: '4px', overflow: 'hidden' }}>
                                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                            <thead>
                                                <tr style={{ backgroundColor: '#F9FAFB', borderBottom: '1px solid #E5E7EB' }}>
                                                    <th style={{ padding: '8px 12px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280' }}>Resource</th>
                                                    {actions.map(action => (
                                                        <th key={action.id} style={{ padding: '8px 12px', textAlign: 'center', fontSize: '12px', fontWeight: '600', color: '#6B7280' }}>
                                                            {action.display_name}
                                                        </th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {resources.map(resource => (
                                                    <tr key={resource.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                                        <td style={{ padding: '8px 12px', fontSize: '14px', color: '#111827' }}>
                                                            {resource.display_name}
                                                        </td>
                                                        {actions.map(action => (
                                                            <td key={action.id} style={{ padding: '8px 12px', textAlign: 'center' }}>
                                                                <input
                                                                    type="checkbox"
                                                                    checked={!!selectedPermissions[`${resource.id}___${action.id}`]}
                                                                    onChange={() => handlePermissionChange(resource.id, action.id)}
                                                                    style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                                                                />
                                                            </td>
                                                        ))}
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>

                                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                                    <button
                                        type="button"
                                        onClick={() => setShowCreateModal(false)}
                                        style={{ padding: '8px 16px', borderRadius: '4px', border: '1px solid #D1D5DB', backgroundColor: 'white', cursor: 'pointer' }}
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={creating}
                                        style={{ padding: '8px 16px', borderRadius: '4px', border: 'none', backgroundColor: '#4F46E5', color: 'white', cursor: 'pointer', opacity: creating ? 0.7 : 1 }}
                                    >
                                        {creating ? 'Creating...' : 'Create Role'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}
            </div>
        </AdminLayout>
    );
};

export default RoleManagementPage;

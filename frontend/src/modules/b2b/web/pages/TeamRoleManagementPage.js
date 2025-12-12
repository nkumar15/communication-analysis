// TeamRoleManagementPage.js – UI for managing team-level roles and capabilities
import React, { useEffect, useState } from 'react';
import apiService from '../../../../core/api/b2bClient';
import AdminLayout from '../layouts/AdminLayout';

const TeamRoleManagementPage = () => {
    const [teamRoles, setTeamRoles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [selectedRole, setSelectedRole] = useState(null);
    const [formData, setFormData] = useState({
        name: '',
        display_name: '',
        description: '',
        can_manage_members: false,
        can_manage_settings: false,
        can_write_resources: true,
        can_delete_resources: false,
        is_default: false
    });
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        fetchTeamRoles();
    }, []);

    const fetchTeamRoles = async () => {
        try {
            setLoading(true);
            const data = await apiService.get('/api/b2b/team-roles');
            setTeamRoles(data);
        } catch (e) {
            console.error('Failed to fetch team roles', e);
            setError('Unable to load team roles');
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setFormData({
            name: '',
            display_name: '',
            description: '',
            can_manage_members: false,
            can_manage_settings: false,
            can_write_resources: true,
            can_delete_resources: false,
            is_default: false
        });
    };

    const handleOpenCreate = () => {
        resetForm();
        setShowCreateModal(true);
    };

    const handleOpenEdit = (role) => {
        setSelectedRole(role);
        setFormData({
            name: role.name,
            display_name: role.display_name,
            description: role.description || '',
            can_manage_members: role.can_manage_members,
            can_manage_settings: role.can_manage_settings,
            can_write_resources: role.can_write_resources,
            can_delete_resources: role.can_delete_resources,
            is_default: role.is_default
        });
        setShowEditModal(true);
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            await apiService.post('/api/b2b/team-roles', formData);
            setShowCreateModal(false);
            resetForm();
            fetchTeamRoles();
        } catch (e) {
            console.error('Failed to create team role', e);
            setError(e.response?.data?.detail || 'Failed to create team role');
        } finally {
            setSaving(false);
        }
    };

    const handleUpdate = async (e) => {
        e.preventDefault();
        if (!selectedRole) return;
        setSaving(true);
        try {
            const updateData = {
                display_name: formData.display_name,
                description: formData.description,
                can_manage_members: formData.can_manage_members,
                can_manage_settings: formData.can_manage_settings,
                can_write_resources: formData.can_write_resources,
                can_delete_resources: formData.can_delete_resources,
                is_default: formData.is_default
            };
            await apiService.put(`/api/b2b/team-roles/${selectedRole.id}`, updateData);
            setShowEditModal(false);
            setSelectedRole(null);
            resetForm();
            fetchTeamRoles();
        } catch (e) {
            console.error('Failed to update team role', e);
            setError(e.response?.data?.detail || 'Failed to update team role');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (role) => {
        if (role.is_system) {
            setError('Cannot delete system roles');
            return;
        }
        if (!window.confirm(`Delete role "${role.display_name}"? This cannot be undone.`)) {
            return;
        }
        try {
            await apiService.delete(`/api/b2b/team-roles/${role.id}`);
            fetchTeamRoles();
        } catch (e) {
            console.error('Failed to delete team role', e);
            setError(e.response?.data?.detail || 'Failed to delete team role');
        }
    };

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const getCapabilityBadges = (role) => {
        const badges = [];
        if (role.can_manage_members) badges.push({ label: 'Manage Members', color: 'green' });
        if (role.can_manage_settings) badges.push({ label: 'Manage Settings', color: 'blue' });
        if (role.can_write_resources) badges.push({ label: 'Write', color: 'yellow' });
        if (role.can_delete_resources) badges.push({ label: 'Delete', color: 'red' });
        return badges;
    };

    if (loading) {
        return (
            <AdminLayout>
                <div className="loading-container">
                    <div className="loading-spinner"></div>
                    <p>Loading team roles...</p>
                </div>
            </AdminLayout>
        );
    }

    return (
        <AdminLayout>
            <div className="team-role-management">
                <div className="page-header">
                    <div>
                        <h1>Team Roles</h1>
                        <p className="description">
                            Configure team-level roles that control what actions members can perform within teams.
                        </p>
                    </div>
                    <button className="btn btn-primary" onClick={handleOpenCreate}>
                        + Create Custom Role
                    </button>
                </div>

                {error && (
                    <div className="alert alert-error">
                        {error}
                        <button onClick={() => setError(null)}>×</button>
                    </div>
                )}

                <div className="roles-grid">
                    {teamRoles.map(role => (
                        <div key={role.id} className={`role-card ${role.is_system ? 'system-role' : ''}`}>
                            <div className="role-header">
                                <div className="role-title">
                                    <h3>{role.display_name}</h3>
                                    {role.is_system && <span className="badge badge-gray">System</span>}
                                    {role.is_default && <span className="badge badge-blue">Default</span>}
                                </div>
                                {!role.is_system && (
                                    <div className="role-actions">
                                        <button
                                            className="btn btn-sm btn-secondary"
                                            onClick={() => handleOpenEdit(role)}
                                        >
                                            Edit
                                        </button>
                                        <button
                                            className="btn btn-sm btn-danger"
                                            onClick={() => handleDelete(role)}
                                        >
                                            Delete
                                        </button>
                                    </div>
                                )}
                            </div>
                            <p className="role-description">{role.description || 'No description'}</p>
                            <div className="role-capabilities">
                                <h4>Capabilities</h4>
                                <div className="capability-badges">
                                    {getCapabilityBadges(role).map((badge, idx) => (
                                        <span key={idx} className={`badge badge-${badge.color}`}>
                                            {badge.label}
                                        </span>
                                    ))}
                                    {getCapabilityBadges(role).length === 0 && (
                                        <span className="badge badge-gray">Read Only</span>
                                    )}
                                </div>
                            </div>
                            <div className="role-name">
                                <code>{role.name}</code>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Create Modal */}
                {showCreateModal && (
                    <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
                        <div className="modal" onClick={e => e.stopPropagation()}>
                            <div className="modal-header">
                                <h2>Create Custom Team Role</h2>
                                <button className="modal-close" onClick={() => setShowCreateModal(false)}>×</button>
                            </div>
                            <form onSubmit={handleCreate}>
                                <div className="modal-body">
                                    <div className="form-group">
                                        <label>Role Name (slug)</label>
                                        <input
                                            type="text"
                                            name="name"
                                            value={formData.name}
                                            onChange={handleChange}
                                            placeholder="e.g. senior_contributor"
                                            pattern="^[a-z_]+$"
                                            required
                                        />
                                        <small>Lowercase letters and underscores only</small>
                                    </div>
                                    <div className="form-group">
                                        <label>Display Name</label>
                                        <input
                                            type="text"
                                            name="display_name"
                                            value={formData.display_name}
                                            onChange={handleChange}
                                            placeholder="e.g. Senior Contributor"
                                            required
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label>Description</label>
                                        <textarea
                                            name="description"
                                            value={formData.description}
                                            onChange={handleChange}
                                            placeholder="Describe what this role can do..."
                                            rows={3}
                                        />
                                    </div>
                                    <div className="form-section">
                                        <h4>Capabilities</h4>
                                        <div className="capability-checkboxes">
                                            <label className="checkbox-label">
                                                <input
                                                    type="checkbox"
                                                    name="can_manage_members"
                                                    checked={formData.can_manage_members}
                                                    onChange={handleChange}
                                                />
                                                <span>Can Manage Members</span>
                                                <small>Add/remove team members</small>
                                            </label>
                                            <label className="checkbox-label">
                                                <input
                                                    type="checkbox"
                                                    name="can_manage_settings"
                                                    checked={formData.can_manage_settings}
                                                    onChange={handleChange}
                                                />
                                                <span>Can Manage Settings</span>
                                                <small>Edit team name, description</small>
                                            </label>
                                            <label className="checkbox-label">
                                                <input
                                                    type="checkbox"
                                                    name="can_write_resources"
                                                    checked={formData.can_write_resources}
                                                    onChange={handleChange}
                                                />
                                                <span>Can Write Resources</span>
                                                <small>Create/edit projects, tasks, etc.</small>
                                            </label>
                                            <label className="checkbox-label">
                                                <input
                                                    type="checkbox"
                                                    name="can_delete_resources"
                                                    checked={formData.can_delete_resources}
                                                    onChange={handleChange}
                                                />
                                                <span>Can Delete Resources</span>
                                                <small>Delete projects, tasks, etc.</small>
                                            </label>
                                        </div>
                                    </div>
                                    <div className="form-group">
                                        <label className="checkbox-label">
                                            <input
                                                type="checkbox"
                                                name="is_default"
                                                checked={formData.is_default}
                                                onChange={handleChange}
                                            />
                                            <span>Set as default role for new team members</span>
                                        </label>
                                    </div>
                                </div>
                                <div className="modal-footer">
                                    <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                                        Cancel
                                    </button>
                                    <button type="submit" className="btn btn-primary" disabled={saving}>
                                        {saving ? 'Creating...' : 'Create Role'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}

                {/* Edit Modal */}
                {showEditModal && selectedRole && (
                    <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
                        <div className="modal" onClick={e => e.stopPropagation()}>
                            <div className="modal-header">
                                <h2>Edit Team Role</h2>
                                <button className="modal-close" onClick={() => setShowEditModal(false)}>×</button>
                            </div>
                            <form onSubmit={handleUpdate}>
                                <div className="modal-body">
                                    <div className="form-group">
                                        <label>Role Name (slug)</label>
                                        <input
                                            type="text"
                                            value={formData.name}
                                            disabled
                                        />
                                        <small>Role name cannot be changed</small>
                                    </div>
                                    <div className="form-group">
                                        <label>Display Name</label>
                                        <input
                                            type="text"
                                            name="display_name"
                                            value={formData.display_name}
                                            onChange={handleChange}
                                            required
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label>Description</label>
                                        <textarea
                                            name="description"
                                            value={formData.description}
                                            onChange={handleChange}
                                            rows={3}
                                        />
                                    </div>
                                    <div className="form-section">
                                        <h4>Capabilities</h4>
                                        <div className="capability-checkboxes">
                                            <label className="checkbox-label">
                                                <input
                                                    type="checkbox"
                                                    name="can_manage_members"
                                                    checked={formData.can_manage_members}
                                                    onChange={handleChange}
                                                />
                                                <span>Can Manage Members</span>
                                            </label>
                                            <label className="checkbox-label">
                                                <input
                                                    type="checkbox"
                                                    name="can_manage_settings"
                                                    checked={formData.can_manage_settings}
                                                    onChange={handleChange}
                                                />
                                                <span>Can Manage Settings</span>
                                            </label>
                                            <label className="checkbox-label">
                                                <input
                                                    type="checkbox"
                                                    name="can_write_resources"
                                                    checked={formData.can_write_resources}
                                                    onChange={handleChange}
                                                />
                                                <span>Can Write Resources</span>
                                            </label>
                                            <label className="checkbox-label">
                                                <input
                                                    type="checkbox"
                                                    name="can_delete_resources"
                                                    checked={formData.can_delete_resources}
                                                    onChange={handleChange}
                                                />
                                                <span>Can Delete Resources</span>
                                            </label>
                                        </div>
                                    </div>
                                    <div className="form-group">
                                        <label className="checkbox-label">
                                            <input
                                                type="checkbox"
                                                name="is_default"
                                                checked={formData.is_default}
                                                onChange={handleChange}
                                            />
                                            <span>Set as default role</span>
                                        </label>
                                    </div>
                                </div>
                                <div className="modal-footer">
                                    <button type="button" className="btn btn-secondary" onClick={() => setShowEditModal(false)}>
                                        Cancel
                                    </button>
                                    <button type="submit" className="btn btn-primary" disabled={saving}>
                                        {saving ? 'Saving...' : 'Save Changes'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}
            </div>

            <style jsx>{`
                .team-role-management {
                    padding: 2rem;
                }
                .page-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 2rem;
                }
                .page-header h1 {
                    margin: 0 0 0.5rem 0;
                }
                .description {
                    color: #6b7280;
                    margin: 0;
                }
                .roles-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
                    gap: 1.5rem;
                }
                .role-card {
                    background: white;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    padding: 1.5rem;
                    transition: box-shadow 0.2s;
                }
                .role-card:hover {
                    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                }
                .role-card.system-role {
                    border-left: 4px solid #6b7280;
                }
                .role-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 0.75rem;
                }
                .role-title {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                }
                .role-title h3 {
                    margin: 0;
                    font-size: 1.1rem;
                }
                .role-description {
                    color: #6b7280;
                    font-size: 0.9rem;
                    margin: 0 0 1rem 0;
                }
                .role-capabilities h4 {
                    font-size: 0.8rem;
                    color: #6b7280;
                    margin: 0 0 0.5rem 0;
                    text-transform: uppercase;
                }
                .capability-badges {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 0.5rem;
                }
                .role-name {
                    margin-top: 1rem;
                    padding-top: 1rem;
                    border-top: 1px solid #e5e7eb;
                }
                .role-name code {
                    font-size: 0.8rem;
                    color: #6b7280;
                    background: #f3f4f6;
                    padding: 0.25rem 0.5rem;
                    border-radius: 4px;
                }
                .badge {
                    display: inline-block;
                    padding: 0.25rem 0.5rem;
                    border-radius: 4px;
                    font-size: 0.75rem;
                    font-weight: 500;
                }
                .badge-gray { background: #f3f4f6; color: #6b7280; }
                .badge-blue { background: #dbeafe; color: #1d4ed8; }
                .badge-green { background: #dcfce7; color: #16a34a; }
                .badge-yellow { background: #fef3c7; color: #d97706; }
                .badge-red { background: #fee2e2; color: #dc2626; }
                .role-actions {
                    display: flex;
                    gap: 0.5rem;
                }
                .btn {
                    padding: 0.5rem 1rem;
                    border-radius: 6px;
                    font-weight: 500;
                    cursor: pointer;
                    border: none;
                    transition: all 0.2s;
                }
                .btn-primary {
                    background: #4f46e5;
                    color: white;
                }
                .btn-primary:hover {
                    background: #4338ca;
                }
                .btn-secondary {
                    background: #f3f4f6;
                    color: #374151;
                }
                .btn-danger {
                    background: #fee2e2;
                    color: #dc2626;
                }
                .btn-sm {
                    padding: 0.25rem 0.5rem;
                    font-size: 0.8rem;
                }
                .modal-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0,0,0,0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 1000;
                }
                .modal {
                    background: white;
                    border-radius: 12px;
                    width: 100%;
                    max-width: 500px;
                    max-height: 90vh;
                    overflow-y: auto;
                }
                .modal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 1.5rem;
                    border-bottom: 1px solid #e5e7eb;
                }
                .modal-header h2 {
                    margin: 0;
                }
                .modal-close {
                    background: none;
                    border: none;
                    font-size: 1.5rem;
                    cursor: pointer;
                    color: #6b7280;
                }
                .modal-body {
                    padding: 1.5rem;
                }
                .modal-footer {
                    padding: 1rem 1.5rem;
                    border-top: 1px solid #e5e7eb;
                    display: flex;
                    justify-content: flex-end;
                    gap: 0.75rem;
                }
                .form-group {
                    margin-bottom: 1rem;
                }
                .form-group label {
                    display: block;
                    font-weight: 500;
                    margin-bottom: 0.5rem;
                }
                .form-group input,
                .form-group textarea {
                    width: 100%;
                    padding: 0.75rem;
                    border: 1px solid #d1d5db;
                    border-radius: 6px;
                    font-size: 1rem;
                }
                .form-group small {
                    display: block;
                    margin-top: 0.25rem;
                    color: #6b7280;
                    font-size: 0.8rem;
                }
                .form-section {
                    margin: 1.5rem 0;
                    padding: 1rem;
                    background: #f9fafb;
                    border-radius: 8px;
                }
                .form-section h4 {
                    margin: 0 0 1rem 0;
                }
                .capability-checkboxes {
                    display: flex;
                    flex-direction: column;
                    gap: 0.75rem;
                }
                .checkbox-label {
                    display: flex;
                    align-items: flex-start;
                    gap: 0.5rem;
                    cursor: pointer;
                }
                .checkbox-label input {
                    margin-top: 0.25rem;
                }
                .checkbox-label span {
                    font-weight: 500;
                }
                .checkbox-label small {
                    display: block;
                    color: #6b7280;
                    font-size: 0.8rem;
                }
                .alert {
                    padding: 1rem;
                    border-radius: 8px;
                    margin-bottom: 1rem;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .alert-error {
                    background: #fee2e2;
                    color: #dc2626;
                }
                .alert button {
                    background: none;
                    border: none;
                    font-size: 1.25rem;
                    cursor: pointer;
                    color: inherit;
                }
                .loading-container {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    padding: 4rem;
                }
                .loading-spinner {
                    width: 40px;
                    height: 40px;
                    border: 3px solid #e5e7eb;
                    border-top-color: #4f46e5;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </AdminLayout>
    );
};

export default TeamRoleManagementPage;

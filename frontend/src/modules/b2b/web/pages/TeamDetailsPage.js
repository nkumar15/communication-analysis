import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import teamApi from '../../../../core/api/teamClient';
import AdminLayout from '../layouts/AdminLayout';
import TeamRoleBadge from '../components/TeamRoleBadge';
import { formatDateTime } from '../../../../utils/dateUtils';

const TeamDetailsPage = () => {
    const { teamId } = useParams();
    const navigate = useNavigate();

    const [team, setTeam] = useState(null);
    const [members, setMembers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    // Add Member Modal State
    const [showAddMemberModal, setShowAddMemberModal] = useState(false);
    const [newMemberId, setNewMemberId] = useState('');
    const [newMemberRole, setNewMemberRole] = useState('team_member');
    const [addingMember, setAddingMember] = useState(false);

    // Edit Team Modal State
    const [showEditModal, setShowEditModal] = useState(false);
    const [editName, setEditName] = useState('');
    const [editDesc, setEditDesc] = useState('');
    const [saving, setSaving] = useState(false);

    // Available users for adding (should be fetched from API)
    // For now, we'll just use an input for User ID, but ideally this should be a user selector
    // Since we don't have a "UserSelector" component yet, I'll assume we might need one or just use ID for now.
    // Actually, let's fetch users to populate a dropdown.
    const [availableUsers, setAvailableUsers] = useState([]);
    const [teamRoles, setTeamRoles] = useState([
        { value: 'team_manager', label: 'Team Manager' },
        { value: 'team_member', label: 'Team Member' },
        { value: 'team_viewer', label: 'Team Viewer' }
    ]);

    useEffect(() => {
        loadData();
    }, [teamId]);

    const loadData = async () => {
        try {
            setLoading(true);
            const [teamData, membersData] = await Promise.all([
                teamApi.getTeam(teamId),
                teamApi.listMembers(teamId)
            ]);
            setTeam(teamData);
            setMembers(membersData);

            // Initialize edit form
            setEditName(teamData.name);
            setEditDesc(teamData.description || '');

            // Fetch team roles from API
            try {
                const rolesData = await teamApi.getTeamRoles();
                console.log('Team roles fetched:', rolesData);
                if (Array.isArray(rolesData) && rolesData.length > 0) {
                    setTeamRoles(rolesData);
                }
            } catch (roleErr) {
                console.error('Failed to load team roles, using defaults:', roleErr);
                // Keep default roles already set in state
            }

        } catch (err) {
            console.error('Failed to load team details:', err);
            setError('Failed to load team details');
        } finally {
            setLoading(false);
        }
    };

    const loadAvailableUsers = async () => {
        try {
            // We need to import invitationApi to get users
            const invitationApi = require('../../../../core/api/invitationClient').default;
            const users = await invitationApi.getUsers();

            // Filter out users already in the team
            const memberIds = new Set(members.map(m => m.user_id));
            const available = users.filter(u => !memberIds.has(u.id));
            setAvailableUsers(available);
        } catch (err) {
            console.error('Failed to load users:', err);
        }
    };

    const handleAddMember = async (e) => {
        e.preventDefault();
        setAddingMember(true);
        try {
            await teamApi.addMember(teamId, newMemberId, newMemberRole);
            setShowAddMemberModal(false);
            setNewMemberId('');
            loadData(); // Reload to see new member
        } catch (err) {
            setError(err.message || 'Failed to add member');
        } finally {
            setAddingMember(false);
        }
    };

    const handleRemoveMember = async (userId) => {
        if (!window.confirm('Are you sure you want to remove this user from the team?')) {
            return;
        }
        try {
            await teamApi.removeMember(teamId, userId);
            loadData();
        } catch (err) {
            setError(err.message || 'Failed to remove member');
        }
    };

    const handleUpdateRole = async (userId, newRole) => {
        try {
            await teamApi.updateMemberRole(teamId, userId, newRole);
            loadData();
        } catch (err) {
            setError(err.message || 'Failed to update role');
        }
    };

    const handleUpdateTeam = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            await teamApi.updateTeam(teamId, {
                name: editName,
                description: editDesc
            });
            setShowEditModal(false);
            loadData();
        } catch (err) {
            setError(err.message || 'Failed to update team');
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <AdminLayout title="Team Details" subtitle="View and manage team members">
                <div style={{ padding: '40px', textAlign: 'center' }}>
                    <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</div>
                    <p>Loading team details...</p>
                </div>
            </AdminLayout>
        );
    }

    if (!team) {
        return (
            <AdminLayout title="Team Details" subtitle="View and manage team members">
                <div style={{ padding: '40px', textAlign: 'center' }}>
                    <div style={{ fontSize: '48px', marginBottom: '16px' }}>❌</div>
                    <p>Team not found</p>
                </div>
            </AdminLayout>
        );
    }

    return (
        <AdminLayout title={team.name} subtitle={team.description || 'Team details and members'}>
            <div style={{ padding: '32px', maxWidth: '1400px', margin: '0 auto' }}>
                {/* Back Button */}
                <button
                    onClick={() => navigate('/b2b/teams')}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        fontSize: '14px',
                        color: '#6B7280',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        marginBottom: '24px',
                        padding: '8px 0',
                        transition: 'color 0.2s'
                    }}
                    onMouseEnter={(e) => e.target.style.color = '#374151'}
                    onMouseLeave={(e) => e.target.style.color = '#6B7280'}
                >
                    <svg style={{ width: '16px', height: '16px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                    Back to Teams
                </button>

                {/* Header with Team Name and Actions */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    marginBottom: '24px',
                    flexWrap: 'wrap',
                    gap: '16px'
                }}>
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                            <h1 style={{
                                fontSize: '28px',
                                fontWeight: '700',
                                color: '#111827',
                                margin: 0
                            }}>
                                🏢 {team.name}
                            </h1>
                            {team.is_default && (
                                <span style={{
                                    padding: '4px 12px',
                                    borderRadius: '9999px',
                                    fontSize: '12px',
                                    fontWeight: '600',
                                    backgroundColor: '#d1fae5',
                                    color: '#065f46',
                                    border: '1px solid #10b981'
                                }}>
                                    ✓ Default Team
                                </span>
                            )}
                        </div>
                        <p style={{ fontSize: '14px', color: '#6B7280', margin: 0 }}>
                            {team.description || 'No description'}
                        </p>
                    </div>
                    <div style={{ display: 'flex', gap: '12px' }}>
                        <button
                            onClick={() => setShowEditModal(true)}
                            style={{
                                padding: '10px 16px',
                                borderRadius: '8px',
                                border: '2px solid #e5e7eb',
                                background: 'white',
                                color: '#374151',
                                fontSize: '14px',
                                fontWeight: '600',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px'
                            }}
                            onMouseEnter={(e) => e.target.style.background = '#f3f4f6'}
                            onMouseLeave={(e) => e.target.style.background = 'white'}
                        >
                            <svg style={{ width: '16px', height: '16px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                            </svg>
                            ✏️ Edit Team
                        </button>
                        <button
                            onClick={() => {
                                loadAvailableUsers();
                                setShowAddMemberModal(true);
                            }}
                            style={{
                                padding: '10px 18px',
                                borderRadius: '8px',
                                border: 'none',
                                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                color: 'white',
                                fontSize: '14px',
                                fontWeight: '600',
                                cursor: 'pointer',
                                boxShadow: '0 4px 12px rgba(102, 126, 234, 0.4)',
                                transition: 'all 0.2s',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px'
                            }}
                            onMouseEnter={(e) => e.target.style.transform = 'translateY(-2px)'}
                            onMouseLeave={(e) => e.target.style.transform = 'translateY(0)'}
                        >
                            <svg style={{ width: '20px', height: '20px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                            </svg>
                            👤 Add Member
                        </button>
                    </div>
                </div>

                {error && (
                    <div className="mb-4 bg-red-50 border-l-4 border-red-400 p-4">
                        <div className="flex">
                            <div className="flex-shrink-0">
                                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                </svg>
                            </div>
                            <div className="ml-3">
                                <p className="text-sm text-red-700">{error}</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Members List */}
                <div className="bg-white shadow overflow-hidden sm:rounded-lg">
                    <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
                        <h3 className="text-lg leading-6 font-medium text-gray-900">Team Members</h3>
                        <p className="mt-1 max-w-2xl text-sm text-gray-500">
                            {members.length} members in this team
                        </p>
                    </div>
                    <ul className="divide-y divide-gray-200">
                        {members.map((member) => (
                            <li key={member.id} className="px-4 py-4 sm:px-6">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center">
                                        <div className="flex-shrink-0 h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center text-gray-500 font-bold">
                                            {member.user_name ? member.user_name.charAt(0).toUpperCase() : member.user_email.charAt(0).toUpperCase()}
                                        </div>
                                        <div className="ml-4">
                                            <div className="text-sm font-medium text-gray-900">{member.user_name || 'Unknown'}</div>
                                            <div className="text-sm text-gray-500">{member.user_email}</div>
                                        </div>
                                    </div>
                                    <div className="flex items-center space-x-4">
                                        <select
                                            value={member.team_role}
                                            onChange={(e) => handleUpdateRole(member.user_id, e.target.value)}
                                            className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                                        >
                                            <option value="team_manager">Manager</option>
                                            <option value="team_member">Member</option>
                                            <option value="team_viewer">Viewer</option>
                                        </select>
                                        <TeamRoleBadge role={member.team_role} />
                                        <button
                                            onClick={() => handleRemoveMember(member.user_id)}
                                            className="text-red-600 hover:text-red-900"
                                        >
                                            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                            </li>
                        ))}
                        {members.length === 0 && (
                            <li className="px-4 py-8 text-center text-gray-500">
                                No members in this team.
                            </li>
                        )}
                    </ul>
                </div>
            </div>

            {/* Add Member Modal */}
            {showAddMemberModal && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0, 0, 0, 0.6)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000,
                    padding: '20px'
                }} onClick={() => setShowAddMemberModal(false)}>
                    <div style={{
                        width: '100%',
                        maxWidth: '520px',
                        background: 'white',
                        borderRadius: '16px',
                        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                        overflow: 'hidden'
                    }} onClick={(e) => e.stopPropagation()}>
                        {/* Header with Gradient */}
                        <div style={{
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            padding: '24px',
                            color: 'white'
                        }}>
                            <h2 style={{
                                margin: 0,
                                fontSize: '24px',
                                fontWeight: '700',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '10px'
                            }}>
                                <span style={{ fontSize: '28px' }}>👤</span>
                                Add Team Member
                            </h2>
                            <p style={{
                                margin: '8px 0 0 0',
                                fontSize: '14px',
                                opacity: 0.9
                            }}>
                                Add an existing user to this team
                            </p>
                        </div>

                        <form onSubmit={handleAddMember} style={{ padding: '28px' }}>
                            <div style={{ marginBottom: '24px' }}>
                                <label style={{
                                    display: 'block',
                                    marginBottom: '8px',
                                    fontWeight: '600',
                                    fontSize: '14px',
                                    color: '#374151'
                                }}>
                                    Select User <span style={{ color: '#ef4444' }}>*</span>
                                </label>
                                <select
                                    id="user-select"
                                    required
                                    value={newMemberId}
                                    onChange={(e) => setNewMemberId(e.target.value)}
                                    style={{
                                        width: '100%',
                                        padding: '12px 16px',
                                        borderRadius: '8px',
                                        border: '2px solid #e5e7eb',
                                        fontSize: '14px',
                                        backgroundColor: '#f9fafb',
                                        color: '#111827',
                                        cursor: 'pointer',
                                        outline: 'none',
                                        transition: 'all 0.2s'
                                    }}
                                    onFocus={(e) => {
                                        e.target.style.borderColor = '#667eea';
                                        e.target.style.backgroundColor = 'white';
                                    }}
                                    onBlur={(e) => {
                                        e.target.style.borderColor = '#e5e7eb';
                                        e.target.style.backgroundColor = '#f9fafb';
                                    }}
                                >
                                    <option value="">Select a user...</option>
                                    {availableUsers.map(user => (
                                        <option key={user.id} value={user.id}>
                                            {user.name || user.email} ({user.email})
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div style={{ marginBottom: '28px' }}>
                                <label style={{
                                    display: 'block',
                                    marginBottom: '8px',
                                    fontWeight: '600',
                                    fontSize: '14px',
                                    color: '#374151'
                                }}>
                                    Team Role
                                </label>
                                <select
                                    id="role-select"
                                    value={newMemberRole}
                                    onChange={(e) => setNewMemberRole(e.target.value)}
                                    style={{
                                        width: '100%',
                                        padding: '12px 16px',
                                        borderRadius: '8px',
                                        border: '2px solid #e5e7eb',
                                        fontSize: '14px',
                                        backgroundColor: '#f9fafb',
                                        color: '#111827',
                                        cursor: 'pointer',
                                        outline: 'none',
                                        transition: 'all 0.2s'
                                    }}
                                    onFocus={(e) => {
                                        e.target.style.borderColor = '#667eea';
                                        e.target.style.backgroundColor = 'white';
                                    }}
                                    onBlur={(e) => {
                                        e.target.style.borderColor = '#e5e7eb';
                                        e.target.style.backgroundColor = '#f9fafb';
                                    }}
                                >
                                    {teamRoles.map(role => (
                                        <option key={role.value} value={role.value}>
                                            {role.label}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div style={{
                                display: 'flex',
                                gap: '12px',
                                justifyContent: 'flex-end'
                            }}>
                                <button
                                    type="button"
                                    onClick={() => setShowAddMemberModal(false)}
                                    style={{
                                        padding: '12px 24px',
                                        borderRadius: '8px',
                                        border: '2px solid #e5e7eb',
                                        background: 'white',
                                        color: '#374151',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s'
                                    }}
                                    onMouseEnter={(e) => e.target.style.background = '#f3f4f6'}
                                    onMouseLeave={(e) => e.target.style.background = 'white'}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={addingMember}
                                    style={{
                                        padding: '12px 28px',
                                        borderRadius: '8px',
                                        border: 'none',
                                        background: addingMember ? '#9ca3af' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                        color: 'white',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        cursor: addingMember ? 'not-allowed' : 'pointer',
                                        boxShadow: addingMember ? 'none' : '0 4px 12px rgba(102, 126, 234, 0.4)',
                                        transition: 'all 0.2s'
                                    }}
                                    onMouseEnter={(e) => !addingMember && (e.target.style.transform = 'translateY(-2px)')}
                                    onMouseLeave={(e) => !addingMember && (e.target.style.transform = 'translateY(0)')}
                                >
                                    {addingMember ? '⏳ Adding...' : '✨ Add Member'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Edit Team Modal */}
            {showEditModal && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0, 0, 0, 0.6)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000,
                    padding: '20px'
                }} onClick={() => setShowEditModal(false)}>
                    <div style={{
                        width: '100%',
                        maxWidth: '520px',
                        background: 'white',
                        borderRadius: '16px',
                        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                        overflow: 'hidden'
                    }} onClick={(e) => e.stopPropagation()}>
                        {/* Header with Gradient */}
                        <div style={{
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            padding: '24px',
                            color: 'white'
                        }}>
                            <h2 style={{
                                margin: 0,
                                fontSize: '24px',
                                fontWeight: '700',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '10px'
                            }}>
                                <span style={{ fontSize: '28px' }}>✏️</span>
                                Edit Team
                            </h2>
                            <p style={{
                                margin: '8px 0 0 0',
                                fontSize: '14px',
                                opacity: 0.9
                            }}>
                                Update team details
                            </p>
                        </div>

                        <form onSubmit={handleUpdateTeam} style={{ padding: '28px' }}>
                            <div style={{ marginBottom: '24px' }}>
                                <label style={{
                                    display: 'block',
                                    marginBottom: '8px',
                                    fontWeight: '600',
                                    fontSize: '14px',
                                    color: '#374151'
                                }}>
                                    Team Name <span style={{ color: '#ef4444' }}>*</span>
                                </label>
                                <input
                                    type="text"
                                    id="edit-name"
                                    required
                                    value={editName}
                                    onChange={(e) => setEditName(e.target.value)}
                                    style={{
                                        width: '100%',
                                        padding: '12px 16px',
                                        border: '2px solid #e5e7eb',
                                        borderRadius: '8px',
                                        fontSize: '14px',
                                        backgroundColor: '#f9fafb',
                                        color: '#111827',
                                        transition: 'all 0.2s',
                                        outline: 'none'
                                    }}
                                    onFocus={(e) => {
                                        e.target.style.borderColor = '#667eea';
                                        e.target.style.backgroundColor = 'white';
                                    }}
                                    onBlur={(e) => {
                                        e.target.style.borderColor = '#e5e7eb';
                                        e.target.style.backgroundColor = '#f9fafb';
                                    }}
                                />
                            </div>

                            <div style={{ marginBottom: '28px' }}>
                                <label style={{
                                    display: 'block',
                                    marginBottom: '8px',
                                    fontWeight: '600',
                                    fontSize: '14px',
                                    color: '#374151'
                                }}>
                                    Description
                                </label>
                                <textarea
                                    id="edit-desc"
                                    rows="3"
                                    value={editDesc}
                                    onChange={(e) => setEditDesc(e.target.value)}
                                    style={{
                                        width: '100%',
                                        padding: '12px 16px',
                                        border: '2px solid #e5e7eb',
                                        borderRadius: '8px',
                                        fontSize: '14px',
                                        backgroundColor: '#f9fafb',
                                        color: '#111827',
                                        transition: 'all 0.2s',
                                        outline: 'none',
                                        resize: 'vertical',
                                        fontFamily: 'inherit'
                                    }}
                                    onFocus={(e) => {
                                        e.target.style.borderColor = '#667eea';
                                        e.target.style.backgroundColor = 'white';
                                    }}
                                    onBlur={(e) => {
                                        e.target.style.borderColor = '#e5e7eb';
                                        e.target.style.backgroundColor = '#f9fafb';
                                    }}
                                />
                            </div>

                            <div style={{
                                display: 'flex',
                                gap: '12px',
                                justifyContent: 'flex-end'
                            }}>
                                <button
                                    type="button"
                                    onClick={() => setShowEditModal(false)}
                                    style={{
                                        padding: '12px 24px',
                                        borderRadius: '8px',
                                        border: '2px solid #e5e7eb',
                                        background: 'white',
                                        color: '#374151',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s'
                                    }}
                                    onMouseEnter={(e) => e.target.style.background = '#f3f4f6'}
                                    onMouseLeave={(e) => e.target.style.background = 'white'}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={saving}
                                    style={{
                                        padding: '12px 28px',
                                        borderRadius: '8px',
                                        border: 'none',
                                        background: saving ? '#9ca3af' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                        color: 'white',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        cursor: saving ? 'not-allowed' : 'pointer',
                                        boxShadow: saving ? 'none' : '0 4px 12px rgba(102, 126, 234, 0.4)',
                                        transition: 'all 0.2s'
                                    }}
                                    onMouseEnter={(e) => !saving && (e.target.style.transform = 'translateY(-2px)')}
                                    onMouseLeave={(e) => !saving && (e.target.style.transform = 'translateY(0)')}
                                >
                                    {saving ? '⏳ Saving...' : '💾 Save Changes'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </AdminLayout>
    );
};

export default TeamDetailsPage;

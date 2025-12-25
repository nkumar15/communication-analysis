import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import teamApi from '../../../../core/api/teamClient';
import AdminLayout from '../layouts/AdminLayout';
import TeamRoleBadge from '../components/TeamRoleBadge';
import { formatDateTime } from '../../../../utils/dateUtils';
import useAuth from '../../../../core/hooks/useAuth';
import { DashboardSkeleton } from '../../../../core/components/LoadingSkeleton';

const TeamDetailsPage = () => {
    const { teamId } = useParams();
    const navigate = useNavigate();
    const { user, hasPermission } = useAuth();

    const [team, setTeam] = useState(null);
    const [members, setMembers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    // Add Member Modal State
    const [showAddMemberModal, setShowAddMemberModal] = useState(false);
    const [newMemberId, setNewMemberId] = useState('');
    const [newMemberRole, setNewMemberRole] = useState('team_contributor');
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

    // Check permissions
    const canManageTeam = hasPermission('teams', 'write');
    const isTeamManager = members.some(m =>
        m.user_id === user?.id &&
        (m.team_role === 'team_manager' || m.team_role?.can_manage_members)
    );
    const showManageActions = canManageTeam || isTeamManager;

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
            const users = await teamApi.getAvailableUsers(teamId);
            setAvailableUsers(users);
        } catch (err) {
            console.error('Failed to load available users:', err);
            // Show the actual error message from the backend if available
            const msg = err.message || 'Failed to load available users';
            setError(msg);
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
                <DashboardSkeleton />
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
        <AdminLayout>
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
                        {showManageActions && (
                            <>
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
                                >
                                    <svg style={{ width: '20px', height: '20px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                                    </svg>
                                    👤 Add Member
                                </button>
                            </>
                        )}
                    </div>
                </div>

                {error && (
                    <div style={{
                        marginBottom: '16px',
                        padding: '12px 16px',
                        backgroundColor: '#fef2f2',
                        border: '1px solid #fca5a5',
                        borderRadius: '8px',
                        color: '#dc2626',
                        fontSize: '14px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                    }}>
                        ❌ {error}
                    </div>
                )}

                {/* Members List */}
                <div style={{
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                    overflow: 'hidden',
                    border: '1px solid #e5e7eb'
                }}>
                    <div style={{
                        padding: '20px 24px',
                        borderBottom: '1px solid #e5e7eb'
                    }}>
                        <h3 style={{
                            fontSize: '18px',
                            fontWeight: '600',
                            color: '#111827',
                            margin: 0
                        }}>Team Members</h3>
                        <p style={{
                            marginTop: '4px',
                            fontSize: '14px',
                            color: '#6b7280'
                        }}>
                            {members.length} members in this team
                        </p>
                    </div>
                    <div>
                        {members.map((member, index) => (
                            <div key={member.id} style={{
                                padding: '16px 24px',
                                borderBottom: index < members.length - 1 ? '1px solid #e5e7eb' : 'none',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                gap: '16px'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                                    <div style={{
                                        width: '40px',
                                        height: '40px',
                                        borderRadius: '50%',
                                        backgroundColor: '#e5e7eb',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        fontSize: '16px',
                                        fontWeight: '600',
                                        color: '#6b7280'
                                    }}>
                                        {member.user_name ? member.user_name.charAt(0).toUpperCase() : member.user_email?.charAt(0).toUpperCase()}
                                    </div>
                                    <div>
                                        <div style={{
                                            fontSize: '14px',
                                            fontWeight: '500',
                                            color: '#111827'
                                        }}>
                                            {member.user_name || 'Unknown'}
                                        </div>
                                        <div style={{
                                            fontSize: '13px',
                                            color: '#6b7280'
                                        }}>
                                            {member.user_email}
                                        </div>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                    {/* Permission Logic for managing this member */}
                                    {(() => {
                                        // 1. Can user manage the team generally?
                                        const canManage = showManageActions;

                                        // 2. Is this member the current user? (Cannot remove/edit self in this view usually)
                                        const isSelf = member.user_id === user?.id;

                                        // 3. Is target a Manager? (Only global Admins can manage Managers)
                                        // We use hasPermission('teams', 'write') as proxy for Admin
                                        const isTargetManager = member.team_role === 'team_manager';
                                        const isAdmin = hasPermission('teams', 'write');

                                        // Rules:
                                        // - Can edit if: canManage AND NOT self AND (NOT targetManager OR isAdmin)
                                        // - Can remove if: canManage AND NOT self AND (NOT targetManager OR isAdmin)

                                        const canEditMember = canManage && !isSelf && (!isTargetManager || isAdmin);

                                        return (
                                            <>
                                                {canEditMember ? (
                                                    <select
                                                        value={member.team_role}
                                                        onChange={(e) => handleUpdateRole(member.user_id, e.target.value)}
                                                        style={{
                                                            padding: '6px 12px',
                                                            borderRadius: '6px',
                                                            border: '1px solid #d1d5db',
                                                            fontSize: '13px',
                                                            backgroundColor: 'white',
                                                            color: '#374151',
                                                            cursor: 'pointer'
                                                        }}
                                                    >
                                                        <option value="team_manager">Manager</option>
                                                        <option value="team_contributor">Contributor</option>
                                                        <option value="team_reader">Reader</option>
                                                    </select>
                                                ) : (
                                                    <TeamRoleBadge role={member.team_role} />
                                                )}

                                                {/* If editable, badge is shown inside select or hidden. 
                                                    Wait, design shows badge NEXT to Select. 
                                                    If readonly, we definitely show badge. 
                                                    If editable, we show BOTH? The screenshot showed BOTH. 
                                                    Let's keep badge always visible for clarity, or just when readonly.
                                                    Actually, screenshot has Badge AND Select. 
                                                */}
                                                {canEditMember && <TeamRoleBadge role={member.team_role} />}

                                                {canEditMember && (
                                                    <button
                                                        onClick={() => handleRemoveMember(member.user_id)}
                                                        style={{
                                                            padding: '6px 10px',
                                                            borderRadius: '6px',
                                                            border: '1px solid #fca5a5',
                                                            backgroundColor: '#fef2f2',
                                                            color: '#dc2626',
                                                            cursor: 'pointer',
                                                            fontSize: '13px',
                                                            fontWeight: '500',
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            gap: '4px'
                                                        }}
                                                        title="Remove from team"
                                                    >
                                                        🗑️ Remove
                                                    </button>
                                                )}
                                            </>
                                        );
                                    })()}
                                </div>
                            </div>
                        ))}
                        {members.length === 0 && (
                            <div style={{
                                padding: '40px',
                                textAlign: 'center',
                                color: '#6b7280'
                            }}>
                                No members in this team.
                            </div>
                        )}
                    </div>
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

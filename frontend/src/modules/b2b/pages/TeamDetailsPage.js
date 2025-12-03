import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import teamApi from '../../../core/api/teamClient';
import AdminLayout from '../layouts/AdminLayout';
import TeamRoleBadge from '../components/TeamRoleBadge';
import { formatDateTime } from '../../../utils/dateUtils';
import { UserPlusIcon, TrashIcon, PencilIcon, ArrowLeftIcon } from '@heroicons/react/24/outline';

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
            const invitationApi = require('../../../core/api/invitationClient').default;
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

    if (loading) return <AdminLayout><div>Loading...</div></AdminLayout>;
    if (!team) return <AdminLayout><div>Team not found</div></AdminLayout>;

    return (
        <AdminLayout>
            <div className="p-6">
                {/* Header */}
                <div className="mb-6">
                    <button
                        onClick={() => navigate('/b2b/teams')}
                        className="flex items-center text-sm text-gray-500 hover:text-gray-700 mb-4"
                    >
                        <ArrowLeftIcon className="h-4 w-4 mr-1" />
                        Back to Teams
                    </button>

                    <div className="flex justify-between items-start">
                        <div>
                            <div className="flex items-center">
                                <h1 className="text-2xl font-bold text-gray-900">{team.name}</h1>
                                {team.is_default && (
                                    <span className="ml-3 px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                        Default Team
                                    </span>
                                )}
                            </div>
                            <p className="text-sm text-gray-500 mt-1">{team.description || 'No description'}</p>
                        </div>
                        <div className="flex space-x-3">
                            <button
                                onClick={() => setShowEditModal(true)}
                                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none"
                            >
                                <PencilIcon className="-ml-0.5 mr-2 h-4 w-4" aria-hidden="true" />
                                Edit Team
                            </button>
                            <button
                                onClick={() => {
                                    loadAvailableUsers();
                                    setShowAddMemberModal(true);
                                }}
                                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none"
                            >
                                <UserPlusIcon className="-ml-1 mr-2 h-5 w-5" aria-hidden="true" />
                                Add Member
                            </button>
                        </div>
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
                                            <TrashIcon className="h-5 w-5" />
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
                <div className="fixed z-10 inset-0 overflow-y-auto">
                    <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
                        <div className="fixed inset-0 transition-opacity" aria-hidden="true">
                            <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
                        </div>
                        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
                        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
                            <form onSubmit={handleAddMember}>
                                <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                                    <div className="sm:flex sm:items-start">
                                        <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                                            <h3 className="text-lg leading-6 font-medium text-gray-900">
                                                Add Team Member
                                            </h3>
                                            <div className="mt-4 space-y-4">
                                                <div>
                                                    <label htmlFor="user-select" className="block text-sm font-medium text-gray-700">
                                                        Select User
                                                    </label>
                                                    <select
                                                        id="user-select"
                                                        required
                                                        className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                                                        value={newMemberId}
                                                        onChange={(e) => setNewMemberId(e.target.value)}
                                                    >
                                                        <option value="">Select a user...</option>
                                                        {availableUsers.map(user => (
                                                            <option key={user.id} value={user.id}>
                                                                {user.name || user.email} ({user.email})
                                                            </option>
                                                        ))}
                                                    </select>
                                                </div>
                                                <div>
                                                    <label htmlFor="role-select" className="block text-sm font-medium text-gray-700">
                                                        Team Role
                                                    </label>
                                                    <select
                                                        id="role-select"
                                                        className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                                                        value={newMemberRole}
                                                        onChange={(e) => setNewMemberRole(e.target.value)}
                                                    >
                                                        <option value="team_manager">Manager</option>
                                                        <option value="team_member">Member</option>
                                                        <option value="team_viewer">Viewer</option>
                                                    </select>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                                    <button
                                        type="submit"
                                        disabled={addingMember}
                                        className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none sm:ml-3 sm:w-auto sm:text-sm"
                                    >
                                        {addingMember ? 'Adding...' : 'Add'}
                                    </button>
                                    <button
                                        type="button"
                                        className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                                        onClick={() => setShowAddMemberModal(false)}
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}

            {/* Edit Team Modal */}
            {showEditModal && (
                <div className="fixed z-10 inset-0 overflow-y-auto">
                    <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
                        <div className="fixed inset-0 transition-opacity" aria-hidden="true">
                            <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
                        </div>
                        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
                        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
                            <form onSubmit={handleUpdateTeam}>
                                <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                                    <div className="sm:flex sm:items-start">
                                        <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                                            <h3 className="text-lg leading-6 font-medium text-gray-900">
                                                Edit Team
                                            </h3>
                                            <div className="mt-4 space-y-4">
                                                <div>
                                                    <label htmlFor="edit-name" className="block text-sm font-medium text-gray-700">
                                                        Team Name
                                                    </label>
                                                    <input
                                                        type="text"
                                                        id="edit-name"
                                                        required
                                                        className="mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md"
                                                        value={editName}
                                                        onChange={(e) => setEditName(e.target.value)}
                                                    />
                                                </div>
                                                <div>
                                                    <label htmlFor="edit-desc" className="block text-sm font-medium text-gray-700">
                                                        Description
                                                    </label>
                                                    <textarea
                                                        id="edit-desc"
                                                        rows="3"
                                                        className="mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md"
                                                        value={editDesc}
                                                        onChange={(e) => setEditDesc(e.target.value)}
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                                    <button
                                        type="submit"
                                        disabled={saving}
                                        className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none sm:ml-3 sm:w-auto sm:text-sm"
                                    >
                                        {saving ? 'Saving...' : 'Save Changes'}
                                    </button>
                                    <button
                                        type="button"
                                        className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                                        onClick={() => setShowEditModal(false)}
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}
        </AdminLayout>
    );
};

export default TeamDetailsPage;

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import teamApi from '../../../../core/api/teamClient';
import AdminLayout from '../layouts/AdminLayout';
import { useAuth } from '../../../../core/hooks/useAuth';
import { formatDateTime } from '../../../../utils/dateUtils';
import { DashboardSkeleton } from '../../../../core/components/LoadingSkeleton';

const TeamsPage = () => {
    const [teams, setTeams] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newTeamName, setNewTeamName] = useState('');
    const [newTeamDesc, setNewTeamDesc] = useState('');
    const [creating, setCreating] = useState(false);

    const navigate = useNavigate();
    const { user } = useAuth();

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);
            const [teamsData, statsData] = await Promise.all([
                teamApi.listTeams(),
                teamApi.getStats()
            ]);
            setTeams(teamsData);
            setStats(statsData);
        } catch (err) {
            console.error('Failed to load teams:', err);
            setError('Failed to load teams');
        } finally {
            setLoading(false);
        }
    };

    const handleCreateTeam = async (e) => {
        e.preventDefault();
        setCreating(true);
        setError('');
        setSuccess('');
        try {
            await teamApi.createTeam({
                name: newTeamName,
                description: newTeamDesc
            });
            setShowCreateModal(false);
            setNewTeamName('');
            setNewTeamDesc('');
            setSuccess('Team created successfully');
            loadData();
        } catch (err) {
            setError(err.message || 'Failed to create team');
        } finally {
            setCreating(false);
        }
    };

    const handleDeleteTeam = async (teamId) => {
        if (!window.confirm('Are you sure you want to delete this team? This action cannot be undone.')) {
            return;
        }
        setError('');
        setSuccess('');
        try {
            await teamApi.deleteTeam(teamId);
            setSuccess('Team deleted successfully');
            loadData();
        } catch (err) {
            setError(err.message || 'Failed to delete team');
        }
    };

    if (loading) {
        return (
            <AdminLayout title="Teams" subtitle="Manage teams and their members">
                <DashboardSkeleton />
            </AdminLayout>
        );
    }

    return (
        <AdminLayout title="Teams" subtitle="Manage teams and their members">
            <div style={{ padding: '32px', maxWidth: '1400px', margin: '0 auto' }}>
                {/* Header with Create Button */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '24px'
                }}>
                    <div>
                        <h1 style={{ fontSize: '28px', fontWeight: '700', color: '#111827', margin: '0 0 4px 0' }}>
                            🏢 Teams
                        </h1>
                        <p style={{ fontSize: '14px', color: '#6B7280', margin: 0 }}>
                            Manage teams and their members
                        </p>
                    </div>
                    <button
                        onClick={() => setShowCreateModal(true)}
                        style={{
                            padding: '12px 20px',
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
                            gap: '8px'
                        }}
                    >
                        <svg style={{ width: '20px', height: '20px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                        Create Team
                    </button>
                </div>

                {/* Error Message */}
                {error && (
                    <div style={{
                        marginBottom: '24px',
                        padding: '12px 16px',
                        backgroundColor: '#FEE2E2',
                        border: '1px solid #FCA5A5',
                        borderLeft: '4px solid #EF4444',
                        borderRadius: '6px',
                        color: '#991B1B',
                        fontSize: '14px'
                    }}>
                        ❌ {error}
                    </div>
                )}

                {/* Success Message */}
                {success && (
                    <div style={{
                        marginBottom: '24px',
                        padding: '12px 16px',
                        backgroundColor: '#D1FAE5',
                        border: '1px solid #6EE7B7',
                        borderLeft: '4px solid #10B981',
                        borderRadius: '6px',
                        color: '#065F46',
                        fontSize: '14px'
                    }}>
                        ✅ {success}
                    </div>
                )}

                {/* Stats Cards */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                    gap: '20px',
                    marginBottom: '32px'
                }}>
                    <div style={{
                        backgroundColor: 'white',
                        padding: '24px',
                        borderRadius: '12px',
                        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                        border: '1px solid #E5E7EB'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <div style={{ fontSize: '32px' }}>👥</div>
                            <div>
                                <div style={{ fontSize: '12px', color: '#6B7280', marginBottom: '4px', textTransform: 'uppercase', fontWeight: '600' }}>
                                    Total Teams
                                </div>
                                <div style={{ fontSize: '24px', fontWeight: '700', color: '#111827' }}>
                                    {stats?.total_teams || 0}
                                </div>
                            </div>
                        </div>
                    </div>
                    <div style={{
                        backgroundColor: 'white',
                        padding: '24px',
                        borderRadius: '12px',
                        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                        border: '1px solid #E5E7EB'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <div style={{ fontSize: '32px' }}>⭐</div>
                            <div>
                                <div style={{ fontSize: '12px', color: '#6B7280', marginBottom: '4px', textTransform: 'uppercase', fontWeight: '600' }}>
                                    My Teams
                                </div>
                                <div style={{ fontSize: '24px', fontWeight: '700', color: '#111827' }}>
                                    {stats?.user_teams_count || 0}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Teams List */}
                <div style={{
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                    border: '1px solid #E5E7EB',
                    overflow: 'hidden'
                }}>
                    {teams.length === 0 ? (
                        <div style={{ padding: '60px 24px', textAlign: 'center', color: '#9CA3AF' }}>
                            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📋</div>
                            <p style={{ fontSize: '16px', margin: 0 }}>No teams found. Create one to get started.</p>
                        </div>
                    ) : (
                        teams.map((team, index) => (
                            <div
                                key={team.id}
                                onClick={() => navigate(`/b2b/teams/${team.id}`)}
                                style={{
                                    padding: '20px 24px',
                                    borderBottom: index < teams.length - 1 ? '1px solid #F3F4F6' : 'none',
                                    cursor: 'pointer',
                                    transition: 'background-color 0.15s'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#F9FAFB'}
                                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}
                            >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                        <h3 style={{
                                            margin: 0,
                                            fontSize: '16px',
                                            fontWeight: '600',
                                            color: '#3b82f6'
                                        }}>
                                            {team.name}
                                        </h3>
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
                                                ✓ Default
                                            </span>
                                        )}
                                    </div>
                                    <span style={{
                                        padding: '4px 12px',
                                        borderRadius: '9999px',
                                        fontSize: '12px',
                                        fontWeight: '600',
                                        backgroundColor: '#f3f4f6',
                                        color: '#374151'
                                    }}>
                                        👤 {team.member_count || 0} members
                                    </span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <p style={{ margin: 0, fontSize: '14px', color: '#6B7280' }}>
                                        {team.description || 'No description'}
                                    </p>
                                    <p style={{ margin: 0, fontSize: '13px', color: '#9CA3AF' }}>
                                        Created {formatDateTime(team.created_at)}
                                    </p>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Create Team Modal */}
            {showCreateModal && (
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
                }} onClick={() => setShowCreateModal(false)}>
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
                                <span style={{ fontSize: '28px' }}>🏢</span>
                                Create New Team
                            </h2>
                            <p style={{
                                margin: '8px 0 0 0',
                                fontSize: '14px',
                                opacity: 0.9
                            }}>
                                Organize your users into teams
                            </p>
                        </div>

                        {/* Form Body */}
                        <form onSubmit={handleCreateTeam} style={{ padding: '28px' }}>
                            {/* Team Name Field */}
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
                                    name="team-name"
                                    id="team-name"
                                    required
                                    value={newTeamName}
                                    onChange={(e) => setNewTeamName(e.target.value)}
                                    placeholder="e.g., Engineering Team"
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

                            {/* Description Field */}
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
                                    name="team-desc"
                                    id="team-desc"
                                    rows="3"
                                    value={newTeamDesc}
                                    onChange={(e) => setNewTeamDesc(e.target.value)}
                                    placeholder="Brief description of this team's purpose..."
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

                            {/* Action Buttons */}
                            <div style={{
                                display: 'flex',
                                gap: '12px',
                                justifyContent: 'flex-end'
                            }}>
                                <button
                                    type="button"
                                    onClick={() => setShowCreateModal(false)}
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
                                    disabled={creating}
                                    style={{
                                        padding: '12px 28px',
                                        borderRadius: '8px',
                                        border: 'none',
                                        background: creating ? '#9ca3af' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                        color: 'white',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        cursor: creating ? 'not-allowed' : 'pointer',
                                        boxShadow: creating ? 'none' : '0 4px 12px rgba(102, 126, 234, 0.4)',
                                        transition: 'all 0.2s'
                                    }}
                                >
                                    {creating ? '⏳ Creating...' : '✨ Create Team'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </AdminLayout>
    );
};

export default TeamsPage;

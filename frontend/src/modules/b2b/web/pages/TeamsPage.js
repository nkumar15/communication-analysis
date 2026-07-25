import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import teamApi from '../../../../core/api/teamClient';
import AdminLayout from '../layouts/AdminLayout';
import { useAuth } from '../../../../core/hooks/useAuth';
import { formatDateTime } from '../../../../utils/dateUtils';
import { DashboardSkeleton } from '../../../../core/components/LoadingSkeleton';

import TeamParentSelector from '../components/TeamParentSelector';
import RegionSelector from '../components/RegionSelector';

const TeamsPage = () => {
    const [teams, setTeams] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [showCreateModal, setShowCreateModal] = useState(false);

    // Form State
    const [newTeamName, setNewTeamName] = useState('');
    const [newTeamDesc, setNewTeamDesc] = useState('');
    const [parentId, setParentId] = useState(null);
    const [regionCode, setRegionCode] = useState('');
    const [creating, setCreating] = useState(false);

    const navigate = useNavigate();
    const { user } = useAuth();

    // Check Features & Plugins
    const features = user?.active_features || {};
    const plugins = features.plugins || [];
    const hasHierarchy = plugins.includes('hierarchical_teams');
    const hasGeo = plugins.includes('geographic_boundaries');

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
            // Construct Payload
            const payload = {
                name: newTeamName,
                description: newTeamDesc,
                config_data: {}
            };

            // Add Hierarchy
            if (hasHierarchy && parentId) {
                payload.parent_team_id = parentId;
                payload.team_type = 'hierarchical';
            }

            // Add Geography
            if (hasGeo && regionCode) {
                payload.config_data.region_code = regionCode;
            }

            await teamApi.createTeam(payload);

            setShowCreateModal(false);
            setNewTeamName('');
            setNewTeamDesc('');
            setParentId(null);
            setRegionCode('');
            setSuccess('Team created successfully');
            loadData();
        } catch (err) {
            setError(err.message || 'Failed to create team');
        } finally {
            setCreating(false);
        }
    };

    // Recursive Tree Builder
    const getTeamTree = (allTeams) => {
        const teamMap = {};
        allTeams.forEach(t => teamMap[t.id] = { ...t, children: [] });

        const roots = [];
        allTeams.forEach(t => {
            if (t.parent_team_id && teamMap[t.parent_team_id]) {
                teamMap[t.parent_team_id].children.push(teamMap[t.id]);
            } else {
                roots.push(teamMap[t.id]);
            }
        });
        return roots;
    };

    const rootTeams = getTeamTree(teams);

    const handleAddChild = (e, parentTeamId) => {
        e.stopPropagation();
        setParentId(parentTeamId);
        setShowCreateModal(true);
    };

    // Recursive Item Component
    const TeamTreeItem = ({ team, level = 0, isLast = false, onAddChild }) => {
        const [expanded, setExpanded] = useState(true);
        const hasChildren = team.children && team.children.length > 0;

        return (
            <div style={{ position: 'relative' }}>
                <div
                    onClick={() => navigate(`/b2b/teams/${team.id}`)}
                    style={{
                        padding: '16px 24px',
                        paddingLeft: `${level * 40 + 24}px`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        borderBottom: '1px solid #F3F4F6',
                        transition: 'background-color 0.15s',
                        position: 'relative',
                        backgroundColor: 'white'
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = '#F9FAFB';
                        // Show actions
                        const actions = e.currentTarget.querySelector('.team-actions');
                        if (actions) actions.style.opacity = '1';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'white';
                        const actions = e.currentTarget.querySelector('.team-actions');
                        if (actions) actions.style.opacity = '0';
                    }}
                >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                        {/* Network Lines */}
                        {level > 0 && (
                            <div style={{
                                position: 'absolute',
                                left: `${(level - 1) * 40 + 44}px`,
                                top: '-20px',
                                bottom: '50%',
                                width: '2px',
                                backgroundColor: '#E5E7EB',
                                zIndex: 0
                            }} />
                        )}
                        {level > 0 && (
                            <div style={{
                                position: 'absolute',
                                left: `${(level - 1) * 40 + 44}px`,
                                top: '50%',
                                width: '20px',
                                height: '2px',
                                backgroundColor: '#E5E7EB',
                                zIndex: 0
                            }} />
                        )}

                        {/* Expander */}
                        <div
                            onClick={(e) => {
                                e.stopPropagation();
                                setExpanded(!expanded);
                            }}
                            style={{
                                width: '24px',
                                height: '24px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                borderRadius: '4px',
                                cursor: hasChildren ? 'pointer' : 'default',
                                color: '#6B7280',
                                zIndex: 1
                            }}
                        >
                            {hasChildren ? (
                                <svg
                                    style={{
                                        width: '14px',
                                        height: '14px',
                                        transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
                                        transition: 'transform 0.2s'
                                    }}
                                    fill="none" viewBox="0 0 24 24" stroke="currentColor"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
                                </svg>
                            ) : (
                                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#E5E7EB' }}></span>
                            )}
                        </div>

                        {/* Icon & Name */}
                        <div style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: '8px',
                            backgroundColor: level === 0 ? '#EEF2FF' : '#F3F4F6',
                            color: level === 0 ? '#4F46E5' : '#6B7280',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '16px'
                        }}>
                            {level === 0 ? '🏢' : '📂'}
                        </div>

                        <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <h3 style={{ margin: 0, fontSize: '15px', fontWeight: '600', color: '#111827' }}>
                                    {team.name}
                                </h3>
                                {team.is_default && (
                                    <span style={{
                                        padding: '2px 8px',
                                        borderRadius: '9999px',
                                        fontSize: '11px',
                                        fontWeight: '600',
                                        backgroundColor: '#ecfdf5',
                                        color: '#059669',
                                        border: '1px solid #10b981'
                                    }}>
                                        Default
                                    </span>
                                )}
                            </div>
                            <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#6B7280' }}>
                                {team.description || 'No description'}
                            </p>
                        </div>
                    </div>

                    {/* Right Side Info & Actions */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
                        <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '12px', fontWeight: '600', color: '#374151' }}>
                                {team.member_count} members
                            </div>
                            <div style={{ fontSize: '12px', color: '#9CA3AF' }}>
                                Created {formatDateTime(team.created_at).split(',')[0]}
                            </div>
                        </div>

                        {/* Hover Actions */}
                        {/* Hover Actions */}
                        <div className="team-actions" style={{ opacity: 0, transition: 'opacity 0.2s', display: 'flex', gap: '8px' }}>
                            {/* Only show Add Child button if hierarchy plugin is enabled */}
                            {hasHierarchy && (
                                <button
                                    onClick={(e) => onAddChild(e, team.id)}
                                    title="Add Child Team"
                                    style={{
                                        width: '32px',
                                        height: '32px',
                                        borderRadius: '6px',
                                        border: '1px solid #E5E7EB',
                                        backgroundColor: 'white',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        color: '#4B5563',
                                        boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
                                    }}
                                    onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#667eea'; e.currentTarget.style.color = '#667eea'; }}
                                    onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#E5E7EB'; e.currentTarget.style.color = '#4B5563'; }}
                                >
                                    <svg style={{ width: '16px', height: '16px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                    </svg>
                                </button>
                            )}
                        </div>
                    </div>
                </div>

                {/* Recursive Children */}
                {expanded && hasChildren && (
                    <div style={{ position: 'relative' }}>
                        {/* Vertical line connecting children */}
                        <div style={{
                            position: 'absolute',
                            left: `${level * 40 + 44}px`,
                            top: '0',
                            bottom: '24px', // Stop before last item center
                            width: '2px',
                            backgroundColor: '#E5E7EB',
                            zIndex: 0
                        }} />

                        {team.children.map((child, idx) => (
                            <TeamTreeItem
                                key={child.id}
                                team={child}
                                level={level + 1}
                                isLast={idx === team.children.length - 1}
                                onAddChild={onAddChild}
                            />
                        ))}
                    </div>
                )}
            </div>
        );
    };


    if (loading) {
        return (
            <AdminLayout title="Teams" subtitle="Manage teams and their members">
                <DashboardSkeleton />
            </AdminLayout>
        );
    }

    return (
        <AdminLayout>
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
                            Manage hierarchical teams and permissions
                        </p>
                    </div>
                    <button
                        onClick={() => {
                            setParentId(null);
                            setShowCreateModal(true);
                        }}
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
                        New Team
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
                    {/* ... stats kept same ... */}
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

                {/* Tree View */}
                <div style={{
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                    border: '1px solid #E5E7EB',
                    overflow: 'hidden'
                }}>
                    {rootTeams.length === 0 ? (
                        <div style={{ padding: '60px 24px', textAlign: 'center', color: '#9CA3AF' }}>
                            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📋</div>
                            <p style={{ fontSize: '16px', margin: 0 }}>No teams found. Create one to get started.</p>
                        </div>
                    ) : (
                        rootTeams.map((team) => (
                            <TeamTreeItem key={team.id} team={team} onAddChild={handleAddChild} />
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

                            {/* DYNAMIC PLUGIN FIELDS */}
                            {hasHierarchy && (
                                <TeamParentSelector
                                    value={parentId}
                                    onChange={setParentId}
                                />
                            )}

                            {hasGeo && (
                                <RegionSelector
                                    value={regionCode}
                                    onChange={setRegionCode}
                                />
                            )}

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

import React from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Widget showing user's teams with role badges
 */
const MyTeamsWidget = ({ teams = [], loading = false }) => {
    const navigate = useNavigate();

    const getRoleBadgeStyle = (role) => {
        const styles = {
            team_manager: { backgroundColor: '#7C3AED', color: 'white' },
            team_contributor: { backgroundColor: '#2563EB', color: 'white' },
            team_reader: { backgroundColor: '#6B7280', color: 'white' },
        };
        return styles[role] || styles.team_contributor;
    };

    const formatRoleName = (role) => {
        const names = {
            team_manager: 'Manager',
            team_contributor: 'Contributor',
            team_reader: 'Reader',
        };
        return names[role] || role;
    };

    if (loading) {
        return (
            <div style={cardStyle}>
                <h3 style={headerStyle}>🏢 My Teams</h3>
                <div style={{ textAlign: 'center', padding: '20px', color: '#6B7280' }}>
                    Loading...
                </div>
            </div>
        );
    }

    return (
        <div style={cardStyle}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={headerStyle}>🏢 My Teams</h3>
                <span style={{ fontSize: '14px', color: '#6B7280' }}>{teams.length} teams</span>
            </div>

            {teams.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '20px', color: '#6B7280' }}>
                    You're not part of any teams yet.
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {teams.map((team) => (
                        <div
                            key={team.id}
                            onClick={() => navigate(`/b2b/teams/${team.id}`)}
                            style={{
                                padding: '12px 16px',
                                backgroundColor: '#F9FAFB',
                                borderRadius: '8px',
                                border: '1px solid #E5E7EB',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center'
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.backgroundColor = '#EEF2FF';
                                e.currentTarget.style.borderColor = '#C7D2FE';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.backgroundColor = '#F9FAFB';
                                e.currentTarget.style.borderColor = '#E5E7EB';
                            }}
                        >
                            <div>
                                <div style={{ fontWeight: '600', color: '#111827', marginBottom: '4px' }}>
                                    {team.name}
                                </div>
                                <div style={{ fontSize: '13px', color: '#6B7280' }}>
                                    {team.member_count} members
                                </div>
                            </div>
                            <span style={{
                                padding: '4px 10px',
                                borderRadius: '12px',
                                fontSize: '12px',
                                fontWeight: '500',
                                ...getRoleBadgeStyle(team.team_role)
                            }}>
                                {team.team_role_display || formatRoleName(team.team_role)}
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

const cardStyle = {
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '24px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
    border: '1px solid #E5E7EB'
};

const headerStyle = {
    margin: 0,
    fontSize: '18px',
    fontWeight: '600',
    color: '#111827'
};

export default MyTeamsWidget;

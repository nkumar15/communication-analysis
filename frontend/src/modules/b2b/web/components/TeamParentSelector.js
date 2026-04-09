import React, { useState, useEffect } from 'react';
import teamApi from '../../../../core/api/teamClient';

const TeamParentSelector = ({ value, onChange, label = "Reports To (Parent Team)", excludeTeamId = null }) => {
    const [teams, setTeams] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const loadTeams = async () => {
            setLoading(true);
            try {
                const data = await teamApi.listTeams();
                // Filter out the current team (if editing) and potential cycles
                const filtered = excludeTeamId
                    ? data.filter(t => t.id !== excludeTeamId)
                    : data;
                setTeams(filtered);
            } catch (err) {
                console.error("Failed to load teams for selector:", err);
            } finally {
                setLoading(false);
            }
        };
        loadTeams();
    }, [excludeTeamId]);

    return (
        <div style={{ marginBottom: '24px' }}>
            <label style={{
                display: 'block',
                marginBottom: '8px',
                fontWeight: '600',
                fontSize: '14px',
                color: '#374151'
            }}>
                {label}
            </label>
            <select
                value={value || ''}
                onChange={(e) => onChange(e.target.value || null)}
                disabled={loading}
                style={{
                    width: '100%',
                    padding: '12px 16px',
                    border: '2px solid #e5e7eb',
                    borderRadius: '8px',
                    fontSize: '14px',
                    backgroundColor: '#f9fafb',
                    color: '#111827',
                    outline: 'none',
                    cursor: 'pointer'
                }}
            >
                <option value="">No Parent (Top Level)</option>
                {teams.map(team => (
                    <option key={team.id} value={team.id}>
                        {team.name}
                    </option>
                ))}
            </select>
            {loading && <span style={{ fontSize: '12px', color: '#6B7280' }}>Loading teams...</span>}
        </div>
    );
};

export default TeamParentSelector;

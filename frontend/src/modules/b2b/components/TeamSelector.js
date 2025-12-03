import React, { useState, useEffect } from 'react';
import teamApi from '../../../core/api/teamClient';

const TeamSelector = ({ value, onChange, label = "Team", required = false, disabled = false }) => {
    const [teams, setTeams] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadTeams();
    }, []);

    const loadTeams = async () => {
        try {
            setLoading(true);
            const data = await teamApi.listTeams();
            setTeams(data);

            // If required and no value selected, select default or first
            if (required && !value && data.length > 0) {
                const defaultTeam = data.find(t => t.is_default);
                if (defaultTeam) {
                    onChange(defaultTeam.id);
                } else {
                    onChange(data[0].id);
                }
            }
        } catch (err) {
            console.error('Failed to load teams:', err);
            setError('Failed to load teams');
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="text-sm text-gray-500">Loading teams...</div>;
    if (error) return <div className="text-sm text-red-500">{error}</div>;

    return (
        <div className="form-group">
            <label className="block text-sm font-medium text-gray-700 mb-1">
                {label} {required && <span className="text-red-500">*</span>}
            </label>
            <select
                value={value || ''}
                onChange={(e) => onChange(e.target.value)}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            >
                <option value="">Select a team...</option>
                {teams.map(team => (
                    <option key={team.id} value={team.id}>
                        {team.name} {team.is_default ? '(Default)' : ''}
                    </option>
                ))}
            </select>
        </div>
    );
};

export default TeamSelector;

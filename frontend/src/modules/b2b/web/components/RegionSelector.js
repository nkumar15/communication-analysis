import React, { useState, useEffect } from 'react';
import b2bClient from '../../../../core/api/b2bClient';

const RegionSelector = ({ value, onChange, label = "Restricted Region" }) => {
    const [regions, setRegions] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const loadRegions = async () => {
            setLoading(true);
            try {
                const data = await b2bClient.listRegions();
                setRegions(data);
            } catch (err) {
                console.error("Failed to load regions:", err);
            } finally {
                setLoading(false);
            }
        };
        loadRegions();
    }, []);

    return (
        <div style={{ marginBottom: '24px' }}>
            <label style={{
                display: 'block',
                marginBottom: '8px',
                fontWeight: '600',
                fontSize: '14px',
                color: '#374151'
            }}>
                {label} (Optional)
            </label>
            <select
                value={value || ''}
                onChange={(e) => onChange(e.target.value)}
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
                <option value="">No Restrictions (Global)</option>
                {regions.map(region => (
                    <option key={region.id} value={region.code}>
                        {region.name} ({region.code})
                    </option>
                ))}
            </select>
            {loading && <span style={{ fontSize: '12px', color: '#6B7280' }}>Loading regions...</span>}
            <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#6B7280' }}>
                Limits access to data tagged with this region.
            </p>
        </div>
    );
};

export default RegionSelector;

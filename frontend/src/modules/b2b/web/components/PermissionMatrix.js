import React, { useEffect, useState } from 'react';
import apiService from '../../../../core/api/b2bClient';

/**
 * PermissionMatrix Component
 * 
 * Displays a grid of resource × action checkboxes for granular permission selection.
 * 
 * Props:
 * - selectedPermissions: string[] - Array of 'resource:action' strings
 * - onChange: (permissions: string[]) => void - Callback when permissions change
 */
const PermissionMatrix = ({ selectedPermissions = [], onChange }) => {
    const [resources, setResources] = useState([]);
    const [actions, setActions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchPermissionData();
    }, []);

    const fetchPermissionData = async () => {
        try {
            setLoading(true);
            const data = await apiService.get('/api/b2b/team-roles/actions');

            // Show all resources - no filtering
            // TODO: Backend should provide is_team_level flag if needed
            setResources(data.resources || []);
            setActions(data.actions || []);
        } catch (err) {
            console.error('Failed to fetch permissions data:', err);
            setError('Failed to load permissions');
        } finally {
            setLoading(false);
        }
    };

    // Filter actions based on resource type using backend-provided mapping
    const getApplicableActions = (resourceName) => {
        return actions.filter(action => {
            // If applicable_resources is null or undefined, action applies to all resources
            if (!action.applicable_resources || action.applicable_resources.length === 0) {
                return true;
            }

            // Check if this resource is in the applicable list
            return action.applicable_resources.includes(resourceName);
        });
    };

    const isPermissionSelected = (resourceName, actionName) => {
        const permission = `${resourceName}:${actionName}`;
        return selectedPermissions.includes(permission);
    };

    const togglePermission = (resourceName, actionName) => {
        const permission = `${resourceName}:${actionName}`;
        let newPermissions;

        if (isPermissionSelected(resourceName, actionName)) {
            // Remove permission
            newPermissions = selectedPermissions.filter(p => p !== permission);
        } else {
            // Add permission
            newPermissions = [...selectedPermissions, permission];
        }

        onChange(newPermissions);
    };

    const toggleAllForResource = (resourceName) => {
        const applicableActions = getApplicableActions(resourceName);
        const resourcePermissions = applicableActions.map(action => `${resourceName}:${action.name}`);
        const allSelected = resourcePermissions.every(p => selectedPermissions.includes(p));

        let newPermissions;
        if (allSelected) {
            // Deselect all for this resource
            newPermissions = selectedPermissions.filter(p => !resourcePermissions.includes(p));
        } else {
            // Select all for this resource
            const toAdd = resourcePermissions.filter(p => !selectedPermissions.includes(p));
            newPermissions = [...selectedPermissions, ...toAdd];
        }

        onChange(newPermissions);
    };

    const isAllSelectedForResource = (resourceName) => {
        return actions.every(action => isPermissionSelected(resourceName, action.name));
    };

    if (loading) {
        return (
            <div className="permission-matrix-loading">
                <div className="spinner"></div>
                <p>Loading permissions...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="permission-matrix-error">
                <p>❌ {error}</p>
            </div>
        );
    }

    return (
        <div className="permission-matrix">
            <div className="matrix-hint">
                <p>Select specific permissions for this role. Each checkbox represents a <code>resource:action</code> permission.</p>
            </div>

            <div className="matrix-container">
                <table className="permissions-table">
                    <thead>
                        <tr>
                            <th className="resource-column">Resource</th>
                            {actions.map(action => (
                                <th key={action.id} className="action-column">
                                    {action.display_name || action.name}
                                </th>
                            ))}
                            <th className="select-all-column">All</th>
                        </tr>
                    </thead>
                    <tbody>
                        {resources.map(resource => {
                            const applicableActions = getApplicableActions(resource.name);

                            return (
                                <tr key={resource.id}>
                                    <td className="resource-name">
                                        <strong>{resource.display_name || resource.name}</strong>
                                        {resource.description && (
                                            <small>{resource.description}</small>
                                        )}
                                    </td>
                                    {actions.map(action => {
                                        const isApplicable = applicableActions.some(a => a.id === action.id);

                                        if (!isApplicable) {
                                            // Show empty cell with disabled state
                                            return (
                                                <td key={action.id} className="permission-cell disabled">
                                                    <span className="not-applicable">—</span>
                                                </td>
                                            );
                                        }

                                        return (
                                            <td key={action.id} className="permission-cell">
                                                <div className="checkbox-wrapper">
                                                    <input
                                                        type="checkbox"
                                                        checked={isPermissionSelected(resource.name, action.name)}
                                                        onChange={() => togglePermission(resource.name, action.name)}
                                                    />
                                                    <div className="tooltip-text">
                                                        {resource.display_name}: {action.display_name}
                                                    </div>
                                                </div>
                                            </td>
                                        );
                                    })}
                                    <td className="select-all-cell">
                                        <input
                                            type="checkbox"
                                            checked={applicableActions.every(action =>
                                                isPermissionSelected(resource.name, action.name)
                                            )}
                                            onChange={() => toggleAllForResource(resource.name)}
                                        />
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {selectedPermissions.length > 0 && (
                <div className="selected-permissions-preview">
                    <strong>Selected Permissions ({selectedPermissions.length}):</strong>
                    <div className="permission-tags">
                        {selectedPermissions.slice(0, 10).map(perm => (
                            <span key={perm} className="permission-tag">{perm}</span>
                        ))}
                        {selectedPermissions.length > 10 && (
                            <span className="permission-tag more">+{selectedPermissions.length - 10} more</span>
                        )}
                    </div>
                </div>
            )}

            <style jsx>{`
                .permission-matrix {
                    width: 100%;
                }
                .matrix-hint {
                    margin-bottom: 0.75rem;  /* Reduced from 1rem */
                    padding: 0.5rem 0.75rem;  /* Reduced */
                    background: #eff6ff;
                    border-left: 3px solid #3b82f6;
                    border-radius: 4px;
                }
                .matrix-hint p {
                    margin: 0;
                    font-size: 0.8rem;  /* Reduced from 0.9rem */
                    color: #1e40af;
                    line-height: 1.4;
                }
                .matrix-hint code {
                    background: #dbeafe;
                    padding: 0.125rem 0.375rem;
                    border-radius: 3px;
                    font-size: 0.75rem;  /* Reduced from 0.85rem */
                }
                .matrix-container {
                    overflow-x: auto;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                }
                .permissions-table {\n                    width: 100%;\n                    border-collapse: collapse;\n                    background: white;\n                    font-size: 0.8rem;  /* Smaller overall */
                }
                .permissions-table thead {
                    background: #f9fafb;
                    border-bottom: 2px solid #e5e7eb;
                }
                .permissions-table th {
                    padding: 0.5rem;  /* Reduced from 0.75rem */
                    text-align: center;
                    font-weight: 600;
                    font-size: 0.75rem;  /* Reduced from 0.85rem */
                    color: #374151;
                    border-right: 1px solid #e5e7eb;
                }
                .permissions-table th.resource-column {
                    text-align: left;
                    min-width: 160px;  /* Reduced from 180px */
                }
                .permissions-table th.select-all-column {
                    background: #f3f4f6;
                    font-size: 0.7rem;  /* Reduced */
                    color: #6b7280;
                    width: 50px;  /* Fixed width */
                }
                .permissions-table tbody tr {
                    border-bottom: 1px solid #e5e7eb;
                }
                .permissions-table tbody tr:hover {
                    background: #f9fafb;
                }
                .permissions-table td {
                    padding: 0.4rem;  /* Reduced from 0.75rem */
                    border-right: 1px solid #e5e7eb;
                }
                .resource-name {
                    text-align: left;
                }
                .resource-name strong {
                    display: block;
                    color: #111827;
                    font-size: 0.85rem;  /* Reduced from 0.95rem */
                    font-weight: 600;
                }
                .resource-name small {
                    display: block;
                    color: #6b7280;
                    font-size: 0.7rem;  /* Reduced from 0.8rem */
                    margin-top: 0.125rem;  /* Reduced from 0.25rem */
                    line-height: 1.2;
                }
                .permission-cell,
                .select-all-cell {
                    text-align: center;
                    position: relative;
                }
                .permission-cell.disabled {
                    background: #f9fafb;
                    cursor: not-allowed;
                }
                .permission-cell.disabled .not-applicable {
                    color: #d1d5db;
                    font-size: 1.2rem;
                }
                .checkbox-wrapper {
                    position: relative;
                    display: inline-block;
                    cursor: pointer;
                }
                .checkbox-wrapper input[type="checkbox"] {
                    width: 18px;
                    height: 18px;
                    cursor: pointer;
                }
                .tooltip-text {
                    visibility: hidden;
                    position: absolute;
                    bottom: 125%;
                    left: 50%;
                    transform: translateX(-50%);
                    background-color: #1f2937;
                    color: white;
                    padding: 0.5rem 0.75rem;
                    border-radius: 6px;
                    font-size: 0.8125rem;
                    white-space: nowrap;
                    z-index: 1000;
                    opacity: 0;
                    transition: opacity 0.2s;
                    pointer-events: none;
                }
                .tooltip-text::after {
                    content: "";
                    position: absolute;
                    top: 100%;
                    left: 50%;
                    transform: translateX(-50%);
                    border: 4px solid transparent;
                    border-top-color: #1f2937;
                }
                .checkbox-wrapper:hover .tooltip-text {
                    visibility: visible;
                    opacity: 1;
                }
                .permission-cell input[type="checkbox"],
                .select-all-cell input[type="checkbox"] {
                    width: 18px;
                    height: 18px;
                    cursor: pointer;
                }
                .select-all-cell {
                    background: #f9fafb;
                }
                .selected-permissions-preview {
                    margin-top: 1rem;
                    padding: 0.75rem;
                    background: #f9fafb;
                    border-radius: 6px;
                }
                .selected-permissions-preview strong {
                    display: block;
                    margin-bottom: 0.5rem;
                    color: #374151;
                    font-size: 0.9rem;
                }
                .permission-tags {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 0.5rem;
                }
                .permission-tag {
                    display: inline-block;
                    padding: 0.25rem 0.5rem;
                    background: #dbeafe;
                    color: #1e40af;
                    border-radius: 4px;
                    font-size: 0.75rem;
                    font-family: monospace;
                }
                .permission-tag.more {
                    background: #e5e7eb;
                    color: #6b7280;
                    font-family: inherit;
                }
                .permission-matrix-loading,
                .permission-matrix-error {
                    padding: 2rem;
                    text-align: center;
                    color: #6b7280;
                }
                .spinner {
                    width: 40px;
                    height: 40px;
                    border: 3px solid #e5e7eb;
                    border-top-color: #4f46e5;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 1rem;
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
};

export default PermissionMatrix;

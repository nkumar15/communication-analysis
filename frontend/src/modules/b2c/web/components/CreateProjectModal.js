import React, { useEffect, useState, useRef } from 'react';

const CreateProjectModal = ({ isOpen, onClose, workspaceId, onSuccess }) => {
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        due_date: ''
    });
    const [creating, setCreating] = useState(false);
    const [error, setError] = useState('');
    const modalRef = useRef(null);

    useEffect(() => {
        if (!isOpen) return;

        const handleClickOutside = (event) => {
            if (modalRef.current && !modalRef.current.contains(event.target)) {
                onClose();
            }
        };

        const handleEscape = (event) => {
            if (event.key === 'Escape') {
                onClose();
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        document.addEventListener('keydown', handleEscape);

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
            document.removeEventListener('keydown', handleEscape);
        };
    }, [isOpen, onClose]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setCreating(true);

        try {
            const { mockApi } = await import('../services/mockData');
            const newProject = await mockApi.createProject(workspaceId, formData);

            setFormData({ name: '', description: '', due_date: '' });

            if (onSuccess) {
                onSuccess(newProject);
            }

            onClose();
        } catch (err) {
            setError(err.message || 'Failed to create project');
        } finally {
            setCreating(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px'
        }}>
            <div
                ref={modalRef}
                style={{
                    width: '100%',
                    maxWidth: '500px',
                    backgroundColor: '#FFFFFF',
                    borderRadius: '16px',
                    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                    overflow: 'hidden'
                }}
            >
                {/* Header */}
                <div style={{
                    background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
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
                        <span style={{ fontSize: '28px' }}>📁</span>
                        Create Project
                    </h2>
                    <p style={{
                        margin: '8px 0 0 0',
                        fontSize: '14px',
                        opacity: 0.9
                    }}>
                        Add a new project to your workspace
                    </p>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} style={{ padding: '28px' }}>
                    {error && (
                        <div style={{
                            padding: '12px 16px',
                            backgroundColor: '#FEE2E2',
                            border: '1px solid #FCA5A5',
                            borderRadius: '8px',
                            color: '#DC2626',
                            fontSize: '14px',
                            marginBottom: '20px'
                        }}>
                            {error}
                        </div>
                    )}

                    {/* Project Name */}
                    <div style={{ marginBottom: '20px' }}>
                        <label style={{
                            display: 'block',
                            marginBottom: '8px',
                            fontWeight: '600',
                            fontSize: '14px',
                            color: '#374151'
                        }}>
                            Project Name <span style={{ color: '#EF4444' }}>*</span>
                        </label>
                        <input
                            type="text"
                            required
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            placeholder="e.g., Website Redesign"
                            style={{
                                width: '100%',
                                padding: '12px 16px',
                                border: '2px solid #E5E7EB',
                                borderRadius: '8px',
                                fontSize: '14px',
                                backgroundColor: '#F9FAFB',
                                outline: 'none'
                            }}
                            onFocus={(e) => {
                                e.target.style.borderColor = '#10B981';
                                e.target.style.backgroundColor = 'white';
                            }}
                            onBlur={(e) => {
                                e.target.style.borderColor = '#E5E7EB';
                                e.target.style.backgroundColor = '#F9FAFB';
                            }}
                        />
                    </div>

                    {/* Description */}
                    <div style={{ marginBottom: '20px' }}>
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
                            rows="3"
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            placeholder="What is this project about?"
                            style={{
                                width: '100%',
                                padding: '12px 16px',
                                border: '2px solid #E5E7EB',
                                borderRadius: '8px',
                                fontSize: '14px',
                                backgroundColor: '#F9FAFB',
                                outline: 'none',
                                resize: 'vertical',
                                fontFamily: 'inherit'
                            }}
                            onFocus={(e) => {
                                e.target.style.borderColor = '#10B981';
                                e.target.style.backgroundColor = 'white';
                            }}
                            onBlur={(e) => {
                                e.target.style.borderColor = '#E5E7EB';
                                e.target.style.backgroundColor = '#F9FAFB';
                            }}
                        />
                    </div>

                    {/* Due Date */}
                    <div style={{ marginBottom: '28px' }}>
                        <label style={{
                            display: 'block',
                            marginBottom: '8px',
                            fontWeight: '600',
                            fontSize: '14px',
                            color: '#374151'
                        }}>
                            Due Date (Optional)
                        </label>
                        <input
                            type="date"
                            value={formData.due_date}
                            onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                            style={{
                                width: '100%',
                                padding: '12px 16px',
                                border: '2px solid #E5E7EB',
                                borderRadius: '8px',
                                fontSize: '14px',
                                backgroundColor: '#F9FAFB',
                                outline: 'none'
                            }}
                            onFocus={(e) => {
                                e.target.style.borderColor = '#10B981';
                                e.target.style.backgroundColor = 'white';
                            }}
                            onBlur={(e) => {
                                e.target.style.borderColor = '#E5E7EB';
                                e.target.style.backgroundColor = '#F9FAFB';
                            }}
                        />
                    </div>

                    {/* Actions */}
                    <div style={{
                        display: 'flex',
                        gap: '12px',
                        justifyContent: 'flex-end'
                    }}>
                        <button
                            type="button"
                            onClick={onClose}
                            style={{
                                padding: '12px 24px',
                                borderRadius: '8px',
                                border: '2px solid #E5E7EB',
                                background: 'white',
                                color: '#374151',
                                fontSize: '14px',
                                fontWeight: '600',
                                cursor: 'pointer'
                            }}
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
                                background: creating ? '#9CA3AF' : 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                                color: 'white',
                                fontSize: '14px',
                                fontWeight: '600',
                                cursor: creating ? 'not-allowed' : 'pointer',
                                boxShadow: creating ? 'none' : '0 4px 12px rgba(16, 185, 129, 0.4)'
                            }}
                        >
                            {creating ? '⏳ Creating...' : '📁 Create Project'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default CreateProjectModal;

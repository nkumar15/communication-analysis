import React, { useState, useEffect, useRef } from 'react';

const CreateWorkspaceModal = ({ isOpen, onClose, onSuccess }) => {
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        type: 'personal'
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
            // Real API call
            const b2cWorkspaceClient = (await import('../../../../core/api/b2cWorkspaceClient')).default;
            const newWorkspace = await b2cWorkspaceClient.createWorkspace(formData);

            // Reset form
            setFormData({ name: '', description: '', type: 'personal' });

            // Call success callback
            if (onSuccess) {
                onSuccess(newWorkspace);
            }

            // Close modal
            onClose();
        } catch (err) {
            setError(err.message || 'Failed to create workspace');
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
                    background: 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)',
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
                        <span style={{ fontSize: '28px' }}>✨</span>
                        Create Workspace
                    </h2>
                    <p style={{
                        margin: '8px 0 0 0',
                        fontSize: '14px',
                        opacity: 0.9
                    }}>
                        Create a new workspace for your projects and tasks
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

                    {/* Workspace Name */}
                    <div style={{ marginBottom: '20px' }}>
                        <label style={{
                            display: 'block',
                            marginBottom: '8px',
                            fontWeight: '600',
                            fontSize: '14px',
                            color: '#374151'
                        }}>
                            Workspace Name <span style={{ color: '#EF4444' }}>*</span>
                        </label>
                        <input
                            type="text"
                            required
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            placeholder="e.g., Marketing Team"
                            style={{
                                width: '100%',
                                padding: '12px 16px',
                                border: '2px solid #E5E7EB',
                                borderRadius: '8px',
                                fontSize: '14px',
                                backgroundColor: '#F9FAFB',
                                color: '#111827',
                                transition: 'all 0.2s',
                                outline: 'none'
                            }}
                            onFocus={(e) => {
                                e.target.style.borderColor = '#6366F1';
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
                            placeholder="What will you work on in this workspace?"
                            style={{
                                width: '100%',
                                padding: '12px 16px',
                                border: '2px solid #E5E7EB',
                                borderRadius: '8px',
                                fontSize: '14px',
                                backgroundColor: '#F9FAFB',
                                color: '#111827',
                                transition: 'all 0.2s',
                                outline: 'none',
                                resize: 'vertical',
                                fontFamily: 'inherit'
                            }}
                            onFocus={(e) => {
                                e.target.style.borderColor = '#6366F1';
                                e.target.style.backgroundColor = 'white';
                            }}
                            onBlur={(e) => {
                                e.target.style.borderColor = '#E5E7EB';
                                e.target.style.backgroundColor = '#F9FAFB';
                            }}
                        />
                    </div>

                    {/* Workspace Type */}
                    <div style={{ marginBottom: '28px' }}>
                        <label style={{
                            display: 'block',
                            marginBottom: '12px',
                            fontWeight: '600',
                            fontSize: '14px',
                            color: '#374151'
                        }}>
                            Workspace Type
                        </label>
                        <div style={{ display: 'flex', gap: '12px' }}>
                            <label style={{
                                flex: 1,
                                padding: '16px',
                                border: formData.type === 'personal' ? '2px solid #6366F1' : '2px solid #E5E7EB',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                backgroundColor: formData.type === 'personal' ? '#EEF2FF' : '#FFFFFF',
                                transition: 'all 0.2s'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
                                    <input
                                        type="radio"
                                        name="type"
                                        value="personal"
                                        checked={formData.type === 'personal'}
                                        onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                                        style={{ marginRight: '8px', accentColor: '#6366F1' }}
                                    />
                                    <span style={{ fontWeight: '600', color: '#111827', fontSize: '15px' }}>Personal</span>
                                </div>
                                <div style={{ fontSize: '13px', color: '#4B5563', paddingLeft: '24px' }}>
                                    For individual use
                                </div>
                            </label>
                            <label style={{
                                flex: 1,
                                padding: '16px',
                                border: formData.type === 'team' ? '2px solid #6366F1' : '2px solid #E5E7EB',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                backgroundColor: formData.type === 'team' ? '#EEF2FF' : '#FFFFFF',
                                transition: 'all 0.2s'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
                                    <input
                                        type="radio"
                                        name="type"
                                        value="team"
                                        checked={formData.type === 'team'}
                                        onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                                        style={{ marginRight: '8px', accentColor: '#6366F1' }}
                                    />
                                    <span style={{ fontWeight: '600', color: '#111827', fontSize: '15px' }}>Team</span>
                                </div>
                                <div style={{ fontSize: '13px', color: '#4B5563', paddingLeft: '24px' }}>
                                    Collaborate with others
                                </div>
                            </label>
                        </div>
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
                                cursor: 'pointer',
                                transition: 'background-color 0.2s'
                            }}
                            onMouseEnter={(e) => e.target.style.background = '#F3F4F6'}
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
                                background: creating ? '#9CA3AF' : 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)',
                                color: 'white',
                                fontSize: '14px',
                                fontWeight: '600',
                                cursor: creating ? 'not-allowed' : 'pointer',
                                boxShadow: creating ? 'none' : '0 4px 12px rgba(99, 102, 241, 0.4)',
                                transition: 'all 0.2s'
                            }}
                        >
                            {creating ? '⏳ Creating...' : '✨ Create Workspace'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default CreateWorkspaceModal;

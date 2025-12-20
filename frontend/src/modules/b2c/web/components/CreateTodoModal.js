import React, { useState, useEffect, useRef } from 'react';

const CreateTodoModal = ({ isOpen, onClose, workspaceId, onSuccess }) => {
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        due_date: ''
    });
    const [creating, setCreating] = useState(false);
    const [error, setError] = useState('');
    const modalRef = useRef(null);

    useEffect(() => {
        if (!isOpen) return;
        const handleClickOutside = (e) => {
            if (modalRef.current && !modalRef.current.contains(e.target)) onClose();
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [isOpen, onClose]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setCreating(true);

        try {
            const b2cWorkspaceClient = (await import('../../../../core/api/b2cWorkspaceClient')).default;

            // Prepare payload
            const payload = {
                title: formData.title,
                description: formData.description || null,
                due_date: formData.due_date || null
            };

            const newTodo = await b2cWorkspaceClient.createTodo(workspaceId, payload);

            setFormData({ title: '', description: '', due_date: '' });
            if (onSuccess) onSuccess(newTodo);
            onClose();
        } catch (err) {
            setError(err.message || 'Failed to create task');
        } finally {
            setCreating(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000, padding: '20px'
        }}>
            <div ref={modalRef} style={{
                width: '100%', maxWidth: '500px', backgroundColor: '#FFFFFF',
                borderRadius: '16px', boxShadow: '0 20px 60px rgba(0,0,0,0.3)', overflow: 'hidden'
            }}>
                <div style={{
                    background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                    padding: '24px', color: 'white'
                }}>
                    <h2 style={{ margin: 0, fontSize: '24px', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span>✅</span> New Task
                    </h2>
                </div>

                <form onSubmit={handleSubmit} style={{ padding: '28px' }}>
                    {error && <div style={{ color: 'red', marginBottom: '10px' }}>{error}</div>}

                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Task Title *</label>
                        <input
                            type="text" required autoFocus
                            value={formData.title}
                            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                            style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '2px solid #E5E7EB' }}
                            placeholder="What needs to be done?"
                        />
                    </div>

                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Description</label>
                        <textarea
                            rows="2"
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '2px solid #E5E7EB' }}
                            placeholder="Add details..."
                        />
                    </div>

                    <div style={{ marginBottom: '28px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Due Date</label>
                        <input
                            type="date"
                            value={formData.due_date}
                            onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                            style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '2px solid #E5E7EB' }}
                        />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                        <button type="button" onClick={onClose} style={{ padding: '12px 24px', borderRadius: '8px', border: '1px solid #E5E7EB', background: 'white' }}>Cancel</button>
                        <button type="submit" disabled={creating} style={{ padding: '12px 24px', borderRadius: '8px', border: 'none', background: '#10B981', color: 'white', fontWeight: '600' }}>
                            {creating ? 'Creating...' : 'Create Task'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default CreateTodoModal;

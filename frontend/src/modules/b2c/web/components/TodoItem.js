import React from 'react';

const TodoItem = ({ todo, onToggle, onDelete }) => {
    const getStatusColor = (isCompleted) => {
        return isCompleted ? '#10B981' : '#6366F1';
    };

    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            backgroundColor: '#FFFFFF',
            borderRadius: '8px',
            padding: '16px',
            border: '1px solid #E5E7EB',
            marginBottom: '12px',
            transition: 'all 0.2s'
        }}>
            {/* Checkbox */}
            <div
                onClick={() => onToggle(todo)}
                style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '6px',
                    border: `2px solid ${todo.is_completed ? '#10B981' : '#D1D5DB'}`,
                    backgroundColor: todo.is_completed ? '#10B981' : 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginRight: '16px',
                    cursor: 'pointer',
                    flexShrink: 0,
                    transition: 'all 0.2s'
                }}
            >
                {todo.is_completed && (
                    <span style={{ color: 'white', fontSize: '14px', fontWeight: 'bold' }}>✓</span>
                )}
            </div>

            {/* Content */}
            <div style={{ flex: 1 }}>
                <h3 style={{
                    margin: '0 0 4px 0',
                    fontSize: '16px',
                    fontWeight: '500',
                    color: todo.is_completed ? '#9CA3AF' : '#111827',
                    textDecoration: todo.is_completed ? 'line-through' : 'none',
                    transition: 'all 0.2s'
                }}>
                    {todo.title}
                </h3>
                {todo.description && (
                    <p style={{
                        margin: 0,
                        fontSize: '14px',
                        color: '#6B7280',
                        display: '-webkit-box',
                        WebkitLineClamp: 1,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden'
                    }}>
                        {todo.description}
                    </p>
                )}
            </div>

            {/* Meta */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                {todo.due_date && (
                    <span style={{
                        fontSize: '12px',
                        color: todo.is_completed ? '#9CA3AF' : '#6B7280',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        backgroundColor: '#F3F4F6',
                        padding: '4px 8px',
                        borderRadius: '6px'
                    }}>
                        <span>📅</span>
                        {new Date(todo.due_date).toLocaleDateString()}
                    </span>
                )}

                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        onDelete(todo.id);
                    }}
                    style={{
                        background: 'none',
                        border: 'none',
                        color: '#9CA3AF',
                        cursor: 'pointer',
                        padding: '4px',
                        fontSize: '18px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'color 0.2s'
                    }}
                    onMouseEnter={(e) => e.target.style.color = '#EF4444'}
                    onMouseLeave={(e) => e.target.style.color = '#9CA3AF'}
                >
                    🗑️
                </button>
            </div>
        </div>
    );
};

export default TodoItem;

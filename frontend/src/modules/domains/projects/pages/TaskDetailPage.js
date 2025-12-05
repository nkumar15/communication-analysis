import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AdminLayout from '../../../b2b/layouts/AdminLayout';
import useAuth from '../../../../core/hooks/useAuth';
import { tasksApi, commentsApi } from '../../../../core/api/projectsClient';

const TaskDetailPage = () => {
    const { taskId } = useParams();
    const navigate = useNavigate();
    const { user } = useAuth();
    const [task, setTask] = useState(null);
    const [comments, setComments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [newComment, setNewComment] = useState('');
    const [replyTo, setReplyTo] = useState(null);

    useEffect(() => {
        loadData();
    }, [taskId]);

    const loadData = async () => {
        try {
            setLoading(true);
            const [taskData, commentsData] = await Promise.all([
                tasksApi.get(taskId),
                commentsApi.listForTask(taskId)
            ]);
            setTask(taskData);
            setComments(commentsData);
        } catch (err) {
            setError('Failed to load task');
        } finally {
            setLoading(false);
        }
    };

    const handleStatusChange = async (newStatus) => {
        try {
            await tasksApi.updateStatus(taskId, newStatus);
            setTask({ ...task, status: newStatus });
        } catch (err) {
            alert('Failed to update status');
        }
    };

    const handleAddComment = async (e) => {
        e.preventDefault();
        if (!newComment.trim()) return;

        try {
            await commentsApi.create({
                task_id: taskId,
                content: newComment,
                parent_comment_id: replyTo
            });
            setNewComment('');
            setReplyTo(null);
            loadData();
        } catch (err) {
            alert('Failed to add comment');
        }
    };

    if (loading) {
        return (
            <AdminLayout title="Task" subtitle="Loading...">
                <div style={{ padding: '48px', textAlign: 'center' }}>
                    <p style={{ color: '#666' }}>Loading task...</p>
                </div>
            </AdminLayout>
        );
    }

    if (!task) {
        return (
            <AdminLayout title="Task" subtitle="Not found">
                <div style={{ padding: '48px', textAlign: 'center' }}>
                    <p style={{ color: '#666' }}>Task not found</p>
                </div>
            </AdminLayout>
        );
    }

    return (
        <AdminLayout title={task.title} subtitle="Task details">
            <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
                {error && (
                    <div style={{ padding: '12px', backgroundColor: '#fee2e2', color: '#b91c1c', borderRadius: '8px', marginBottom: '16px' }}>
                        {error}
                    </div>
                )}

                {/* Task Header */}
                <div style={{ backgroundColor: 'white', padding: '24px', borderRadius: '8px', marginBottom: '24px', border: '1px solid #e5e7eb' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '16px' }}>
                        <h2 style={{ margin: 0, fontSize: '24px', fontWeight: '700' }}>{task.title}</h2>
                        <div style={{ display: 'flex', gap: '8px' }}>
                            {['todo', 'in_progress', 'done'].map(status => (
                                <button
                                    key={status}
                                    onClick={() => handleStatusChange(status)}
                                    style={{
                                        padding: '6px 12px',
                                        borderRadius: '6px',
                                        border: task.status === status ? 'none' : '1px solid #d1d5db',
                                        backgroundColor:
                                            task.status === status
                                                ? (status === 'done' ? '#10b981' : status === 'in_progress' ? '#f59e0b' : '#3b82f6')
                                                : 'white',
                                        color: task.status === status ? 'white' : '#374151',
                                        fontSize: '12px',
                                        fontWeight: '500',
                                        cursor: 'pointer'
                                    }}
                                >
                                    {status.replace('_', ' ')}
                                </button>
                            ))}
                        </div>
                    </div>

                    {task.description && (
                        <p style={{ margin: '0 0 16px 0', fontSize: '16px', color: '#374151', lineHeight: '1.6' }}>
                            {task.description}
                        </p>
                    )}

                    <div style={{ display: 'flex', gap: '24px', fontSize: '14px', color: '#6b7280' }}>
                        {task.due_date && (
                            <div>
                                <strong>Due:</strong> {new Date(task.due_date).toLocaleDateString()}
                            </div>
                        )}
                        <div>
                            <strong>Created:</strong> {new Date(task.created_at).toLocaleDateString()}
                        </div>
                    </div>
                </div>

                {/* Comments Section */}
                <div style={{ backgroundColor: 'white', padding: '24px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                    <h3 style={{ margin: '0 0 20px 0', fontSize: '18px', fontWeight: '600' }}>
                        Comments ({comments.length})
                    </h3>

                    {/* Comment Form */}
                    <form onSubmit={handleAddComment} style={{ marginBottom: '24px' }}>
                        {replyTo && (
                            <div style={{
                                padding: '8px 12px',
                                backgroundColor: '#f3f4f6',
                                borderRadius: '6px',
                                marginBottom: '8px',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center'
                            }}>
                                <span style={{ fontSize: '14px', color: '#6b7280' }}>Replying to comment...</span>
                                <button
                                    type="button"
                                    onClick={() => setReplyTo(null)}
                                    style={{
                                        padding: '4px 8px',
                                        backgroundColor: 'transparent',
                                        border: 'none',
                                        color: '#6b7280',
                                        cursor: 'pointer',
                                        fontSize: '12px'
                                    }}
                                >
                                    Cancel
                                </button>
                            </div>
                        )}
                        <textarea
                            value={newComment}
                            onChange={(e) => setNewComment(e.target.value)}
                            placeholder={replyTo ? "Write a reply..." : "Add a comment..."}
                            rows={3}
                            style={{
                                width: '100%',
                                padding: '12px',
                                borderRadius: '6px',
                                border: '1px solid #d1d5db',
                                fontSize: '14px',
                                fontFamily: 'inherit',
                                resize: 'vertical',
                                marginBottom: '8px'
                            }}
                        />
                        <button
                            type="submit"
                            disabled={!newComment.trim()}
                            style={{
                                padding: '8px 16px',
                                backgroundColor: '#4f46e5',
                                color: 'white',
                                border: 'none',
                                borderRadius: '6px',
                                fontSize: '14px',
                                fontWeight: '500',
                                cursor: newComment.trim() ? 'pointer' : 'not-allowed',
                                opacity: newComment.trim() ? 1 : 0.5
                            }}
                        >
                            {replyTo ? 'Reply' : 'Comment'}
                        </button>
                    </form>

                    {/* Comments List */}
                    {comments.length === 0 ? (
                        <p style={{ textAlign: 'center', color: '#9ca3af', padding: '24px' }}>
                            No comments yet. Be the first to comment!
                        </p>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            {comments.map(comment => (
                                <CommentItem
                                    key={comment.id}
                                    comment={comment}
                                    currentUserId={user?.id}
                                    onReply={setReplyTo}
                                    onReload={loadData}
                                    depth={0}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </AdminLayout>
    );
};

const CommentItem = ({ comment, currentUserId, onReply, onReload, depth = 0 }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editContent, setEditContent] = useState(comment.content);

    const handleEdit = async () => {
        try {
            await commentsApi.update(comment.id, { content: editContent });
            setIsEditing(false);
            onReload();
        } catch (err) {
            alert('Failed to update comment');
        }
    };

    const handleDelete = async () => {
        if (!confirm('Delete this comment?')) return;
        try {
            await commentsApi.delete(comment.id);
            onReload();
        } catch (err) {
            alert('Failed to delete comment');
        }
    };

    const isOwner = comment.created_by === currentUserId;

    return (
        <div style={{ marginLeft: depth * 32 + 'px' }}>
            <div style={{
                padding: '12px',
                backgroundColor: depth === 0 ? '#f9fafb' : '#ffffff',
                borderRadius: '8px',
                border: '1px solid #e5e7eb'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '8px' }}>
                    <div style={{ fontSize: '12px', color: '#6b7280' }}>
                        {new Date(comment.created_at).toLocaleString()}
                    </div>
                    {isOwner && (
                        <div style={{ display: 'flex', gap: '8px' }}>
                            <button
                                onClick={() => setIsEditing(!isEditing)}
                                style={{
                                    padding: '4px 8px',
                                    backgroundColor: 'transparent',
                                    border: 'none',
                                    color: '#6b7280',
                                    cursor: 'pointer',
                                    fontSize: '12px'
                                }}
                            >
                                {isEditing ? 'Cancel' : 'Edit'}
                            </button>
                            <button
                                onClick={handleDelete}
                                style={{
                                    padding: '4px 8px',
                                    backgroundColor: 'transparent',
                                    border: 'none',
                                    color: '#ef4444',
                                    cursor: 'pointer',
                                    fontSize: '12px'
                                }}
                            >
                                Delete
                            </button>
                        </div>
                    )}
                </div>

                {isEditing ? (
                    <div>
                        <textarea
                            value={editContent}
                            onChange={(e) => setEditContent(e.target.value)}
                            rows={2}
                            style={{
                                width: '100%',
                                padding: '8px',
                                borderRadius: '4px',
                                border: '1px solid #d1d5db',
                                fontSize: '14px',
                                fontFamily: 'inherit',
                                marginBottom: '8px'
                            }}
                        />
                        <button
                            onClick={handleEdit}
                            style={{
                                padding: '6px 12px',
                                backgroundColor: '#4f46e5',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '12px',
                                cursor: 'pointer'
                            }}
                        >
                            Save
                        </button>
                    </div>
                ) : (
                    <>
                        <p style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#111827' }}>
                            {comment.content}
                        </p>
                        <button
                            onClick={() => onReply(comment.id)}
                            style={{
                                padding: '4px 8px',
                                backgroundColor: 'transparent',
                                border: 'none',
                                color: '#6b7280',
                                cursor: 'pointer',
                                fontSize: '12px',
                                fontWeight: '500'
                            }}
                        >
                            Reply
                        </button>
                    </>
                )}
            </div>

            {/* Render nested replies */}
            {comment.replies && comment.replies.length > 0 && (
                <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {comment.replies.map(reply => (
                        <CommentItem
                            key={reply.id}
                            comment={reply}
                            currentUserId={currentUserId}
                            onReply={onReply}
                            onReload={onReload}
                            depth={depth + 1}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

export default TaskDetailPage;

import React, { useState } from 'react';

const HelpWidget = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [message, setMessage] = useState('');

    const handleSendMessage = (e) => {
        e.preventDefault();
        if (!message.trim()) return;

        // Placeholder for future chatbot integration
        alert('Chatbot integration coming soon! Your message: ' + message);
        setMessage('');
    };

    return (
        <>
            {/* Chat Window */}
            {isOpen && (
                <div style={{
                    position: 'fixed',
                    bottom: '90px',
                    right: '24px',
                    width: '380px',
                    height: '520px',
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    boxShadow: '0 10px 40px rgba(0, 0, 0, 0.15)',
                    border: '1px solid #E5E7EB',
                    zIndex: 999,
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden'
                }}>
                    {/* Chat Header */}
                    <div style={{
                        padding: '20px',
                        borderBottom: '1px solid #E5E7EB',
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        color: 'white'
                    }}>
                        <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '700' }}>
                            💬 Help & Support
                        </h3>
                        <p style={{ margin: '4px 0 0 0', fontSize: '13px', opacity: 0.9 }}>
                            We typically reply in a few minutes
                        </p>
                    </div>

                    {/* Chat Messages Area */}
                    <div style={{
                        flex: 1,
                        padding: '20px',
                        overflowY: 'auto',
                        backgroundColor: '#F9FAFB'
                    }}>
                        {/* Welcome Message */}
                        <div style={{ marginBottom: '16px' }}>
                            <div style={{
                                backgroundColor: 'white',
                                borderRadius: '12px',
                                padding: '12px 16px',
                                boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
                                maxWidth: '85%'
                            }}>
                                <div style={{ fontSize: '13px', color: '#6B7280', marginBottom: '4px', fontWeight: '600' }}>
                                    Support Bot
                                </div>
                                <p style={{ margin: 0, fontSize: '14px', color: '#374151', lineHeight: '1.5' }}>
                                    👋 Hi! How can we help you today?
                                </p>
                            </div>
                            <div style={{ fontSize: '11px', color: '#9CA3AF', marginTop: '4px' }}>
                                Just now
                            </div>
                        </div>

                        {/* Quick Actions */}
                        <div style={{ marginBottom: '16px' }}>
                            <div style={{ fontSize: '12px', color: '#6B7280', marginBottom: '8px', fontWeight: '600' }}>
                                Quick Actions
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {[
                                    { icon: '📚', label: 'View Documentation' },
                                    { icon: '🎥', label: 'Watch Tutorials' },
                                    { icon: '📧', label: 'Email Support' }
                                ].map((action, idx) => (
                                    <button
                                        key={idx}
                                        style={{
                                            padding: '10px 12px',
                                            backgroundColor: 'white',
                                            border: '1px solid #E5E7EB',
                                            borderRadius: '8px',
                                            fontSize: '13px',
                                            color: '#374151',
                                            cursor: 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '8px',
                                            transition: 'all 0.2s',
                                            textAlign: 'left'
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.backgroundColor = '#F3F4F6';
                                            e.currentTarget.style.borderColor = '#D1D5DB';
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.backgroundColor = 'white';
                                            e.currentTarget.style.borderColor = '#E5E7EB';
                                        }}
                                        onClick={() => alert(`${action.label} - Coming soon!`)}
                                    >
                                        <span style={{ fontSize: '16px' }}>{action.icon}</span>
                                        <span style={{ fontWeight: '500' }}>{action.label}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Chat Input */}
                    <form onSubmit={handleSendMessage} style={{
                        padding: '16px',
                        borderTop: '1px solid #E5E7EB',
                        backgroundColor: 'white'
                    }}>
                        <div style={{ display: 'flex', gap: '8px' }}>
                            <input
                                type="text"
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                                placeholder="Type your message..."
                                style={{
                                    flex: 1,
                                    padding: '10px 12px',
                                    border: '1px solid #D1D5DB',
                                    borderRadius: '8px',
                                    fontSize: '14px',
                                    outline: 'none'
                                }}
                                onFocus={(e) => e.target.style.borderColor = '#4F46E5'}
                                onBlur={(e) => e.target.style.borderColor = '#D1D5DB'}
                            />
                            <button
                                type="submit"
                                style={{
                                    padding: '10px 16px',
                                    backgroundColor: '#4F46E5',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '8px',
                                    fontSize: '14px',
                                    fontWeight: '600',
                                    cursor: 'pointer',
                                    transition: 'background-color 0.2s'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#4338CA'}
                                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#4F46E5'}
                            >
                                Send
                            </button>
                        </div>
                        <p style={{ margin: '8px 0 0 0', fontSize: '11px', color: '#9CA3AF' }}>
                            Chatbot integration coming soon
                        </p>
                    </form>
                </div>
            )}

            {/* Floating Help Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    position: 'fixed',
                    bottom: '24px',
                    right: '24px',
                    width: '56px',
                    height: '56px',
                    borderRadius: '50%',
                    backgroundColor: '#4F46E5',
                    color: 'white',
                    border: 'none',
                    boxShadow: '0 4px 12px rgba(79, 70, 229, 0.4)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '24px',
                    transition: 'all 0.3s',
                    zIndex: 1000
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'scale(1.1)';
                    e.currentTarget.style.boxShadow = '0 6px 16px rgba(79, 70, 229, 0.5)';
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'scale(1)';
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(79, 70, 229, 0.4)';
                }}
                title="Help & Support"
            >
                {isOpen ? '✕' : '💬'}
            </button>

            {/* Backdrop to close chat */}
            {isOpen && (
                <div
                    onClick={() => setIsOpen(false)}
                    style={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        zIndex: 998
                    }}
                />
            )}
        </>
    );
};

export default HelpWidget;

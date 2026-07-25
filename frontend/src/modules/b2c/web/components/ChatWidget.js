import React, { useState, useRef, useEffect } from 'react';
import { auth } from '../../../../core/firebase/b2c-config';

const ChatWidget = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([
        {
            id: 1,
            type: 'bot',
            text: 'Hi! 👋 How can we help you today?',
            timestamp: new Date()
        }
    ]);
    const [inputValue, setInputValue] = useState('');
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        if (isOpen && messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isOpen]);

    // Focus input when opened
    useEffect(() => {
        if (isOpen && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isOpen]);

    const quickActions = [
        { icon: '💳', label: 'Billing Help', action: 'billing' },
        { icon: '🚀', label: 'Getting Started', action: 'start' },
        { icon: '🐛', label: 'Report Bug', action: 'bug' },
        { icon: '💡', label: 'Feature Request', action: 'feature' }
    ];

    const handleQuickAction = (action) => {
        const actionMessages = {
            billing: 'I need help with billing',
            start: 'How do I get started?',
            bug: 'I want to report a bug',
            feature: 'I have a feature request'
        };

        const userMessage = {
            id: messages.length + 1,
            type: 'user',
            text: actionMessages[action],
            timestamp: new Date()
        };

        const botResponses = {
            billing: 'I can help with billing! Visit the Billing Portal or check our FAQ. For urgent issues, email billing@support.com',
            start: 'Great! Here are some quick steps:\n1. Create a workspace\n2. Invite team members\n3. Create your first project\n\nNeed more help? Check our documentation!',
            bug: 'Thanks for reporting! Please describe the issue and we\'ll investigate. You can also email bugs@support.com with screenshots.',
            feature: 'We love hearing ideas! Share your feature request and we\'ll review it. You can also vote on features at feedback.ourapp.com'
        };

        const botMessage = {
            id: messages.length + 2,
            type: 'bot',
            text: botResponses[action],
            timestamp: new Date()
        };

        setMessages([...messages, userMessage, botMessage]);
    };

    const handleSendMessage = (e) => {
        e.preventDefault();
        if (!inputValue.trim()) return;

        const userMessage = {
            id: messages.length + 1,
            type: 'user',
            text: inputValue,
            timestamp: new Date()
        };

        // Simple bot response (in production, this would call an AI API)
        const botMessage = {
            id: messages.length + 2,
            type: 'bot',
            text: 'Thanks for your message! Our support team will get back to you shortly. For immediate help, try our quick actions above or email support@ourapp.com',
            timestamp: new Date()
        };

        setMessages([...messages, userMessage, botMessage]);
        setInputValue('');
    };

    return (
        <>
            {/* Chat Button */}
            {!isOpen && (
                <button
                    onClick={() => setIsOpen(true)}
                    style={{
                        position: 'fixed',
                        bottom: '24px',
                        right: '24px',
                        width: '60px',
                        height: '60px',
                        borderRadius: '50%',
                        border: 'none',
                        background: 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)',
                        color: 'white',
                        fontSize: '28px',
                        cursor: 'pointer',
                        boxShadow: '0 8px 24px rgba(99, 102, 241, 0.4)',
                        zIndex: 1000,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'transform 0.2s, box-shadow 0.2s'
                    }}
                    onMouseEnter={(e) => {
                        e.target.style.transform = 'scale(1.1)';
                        e.target.style.boxShadow = '0 12px 32px rgba(99, 102, 241, 0.5)';
                    }}
                    onMouseLeave={(e) => {
                        e.target.style.transform = 'scale(1)';
                        e.target.style.boxShadow = '0 8px 24px rgba(99, 102, 241, 0.4)';
                    }}
                    aria-label="Open chat"
                >
                    💬
                </button>
            )}

            {/* Chat Window */}
            {isOpen && (
                <div
                    style={{
                        position: 'fixed',
                        bottom: '24px',
                        right: '24px',
                        width: '380px',
                        height: '600px',
                        backgroundColor: 'white',
                        borderRadius: '16px',
                        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                        zIndex: 1000,
                        display: 'flex',
                        flexDirection: 'column',
                        overflow: 'hidden'
                    }}
                >
                    {/* Header */}
                    <div style={{
                        background: 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)',
                        padding: '20px',
                        color: 'white',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                    }}>
                        <div>
                            <h3 style={{ margin: '0 0 4px 0', fontSize: '18px', fontWeight: '600' }}>
                                Need Help?
                            </h3>
                            <p style={{ margin: 0, fontSize: '13px', opacity: 0.9 }}>
                                We're here to assist you
                            </p>
                        </div>
                        <button
                            onClick={() => setIsOpen(false)}
                            style={{
                                background: 'rgba(255, 255, 255, 0.2)',
                                border: 'none',
                                borderRadius: '50%',
                                width: '32px',
                                height: '32px',
                                color: 'white',
                                fontSize: '20px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}
                        >
                            ×
                        </button>
                    </div>

                    {/* Quick Actions */}
                    <div style={{
                        padding: '16px',
                        borderBottom: '1px solid #E5E7EB',
                        backgroundColor: '#F9FAFB'
                    }}>
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(2, 1fr)',
                            gap: '8px'
                        }}>
                            {quickActions.map((action) => (
                                <button
                                    key={action.action}
                                    onClick={() => handleQuickAction(action.action)}
                                    style={{
                                        padding: '10px 12px',
                                        borderRadius: '8px',
                                        border: '1px solid #E5E7EB',
                                        backgroundColor: 'white',
                                        cursor: 'pointer',
                                        fontSize: '13px',
                                        fontWeight: '500',
                                        color: '#374151',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px',
                                        transition: 'all 0.2s'
                                    }}
                                    onMouseEnter={(e) => {
                                        e.target.style.borderColor = '#6366F1';
                                        e.target.style.backgroundColor = '#EEF2FF';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.target.style.borderColor = '#E5E7EB';
                                        e.target.style.backgroundColor = 'white';
                                    }}
                                >
                                    <span>{action.icon}</span>
                                    <span>{action.label}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Messages */}
                    <div style={{
                        flex: 1,
                        overflowY: 'auto',
                        padding: '20px',
                        backgroundColor: '#FFFFFF'
                    }}>
                        {messages.map((message) => (
                            <div
                                key={message.id}
                                style={{
                                    marginBottom: '16px',
                                    display: 'flex',
                                    justifyContent: message.type === 'user' ? 'flex-end' : 'flex-start'
                                }}
                            >
                                <div style={{
                                    maxWidth: '75%',
                                    padding: '12px 16px',
                                    borderRadius: '12px',
                                    backgroundColor: message.type === 'user' ? '#6366F1' : '#F3F4F6',
                                    color: message.type === 'user' ? 'white' : '#111827',
                                    fontSize: '14px',
                                    lineHeight: '1.5',
                                    whiteSpace: 'pre-wrap'
                                }}>
                                    {message.text}
                                </div>
                            </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input */}
                    <form
                        onSubmit={handleSendMessage}
                        style={{
                            padding: '16px',
                            borderTop: '1px solid #E5E7EB',
                            backgroundColor: 'white'
                        }}
                    >
                        <div style={{ display: 'flex', gap: '8px' }}>
                            <input
                                ref={inputRef}
                                type="text"
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                placeholder="Type your message..."
                                style={{
                                    flex: 1,
                                    padding: '12px 16px',
                                    borderRadius: '8px',
                                    border: '2px solid #E5E7EB',
                                    fontSize: '14px',
                                    outline: 'none'
                                }}
                                onFocus={(e) => e.target.style.borderColor = '#6366F1'}
                                onBlur={(e) => e.target.style.borderColor = '#E5E7EB'}
                            />
                            <button
                                type="submit"
                                style={{
                                    padding: '12px 20px',
                                    borderRadius: '8px',
                                    border: 'none',
                                    background: 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)',
                                    color: 'white',
                                    fontSize: '18px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center'
                                }}
                                disabled={!inputValue.trim()}
                            >
                                ➤
                            </button>
                        </div>
                    </form>
                </div>
            )}
        </>
    );
};

export default ChatWidget;

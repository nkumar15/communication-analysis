import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth } from '../../../../core/firebase/b2c-config';

const UserMenu = ({ onClose }) => {
    const navigate = useNavigate();
    const menuRef = useRef(null);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                onClose();
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [onClose]);

    const handleLogout = async () => {
        try {
            await auth.signOut();
            navigate('/login');
        } catch (error) {
            console.error('Logout failed:', error);
        }
    };

    const menuItems = [
        {
            icon: '⚙️',
            label: 'Settings',
            onClick: () => {
                navigate('/settings');
                onClose();
            }
        },
        {
            icon: '💳',
            label: 'Subscription',
            onClick: () => {
                navigate('/subscription');
                onClose();
            }
        },
        {
            icon: '🧾',
            label: 'Billing History',
            onClick: () => {
                navigate('/billing');
                onClose();
            }
        },
        {
            icon: '🔔',
            label: 'Notifications',
            onClick: () => {
                navigate('/notifications');
                onClose();
            }
        },
        {
            icon: '🚪',
            label: 'Sign Out',
            onClick: handleLogout,
            danger: true
        }
    ];

    return (
        <div
            ref={menuRef}
            style={{
                position: 'absolute',
                top: 'calc(100% + 8px)',
                right: 0,
                width: '240px',
                backgroundColor: '#FFFFFF',
                borderRadius: '12px',
                boxShadow: '0 10px 25px rgba(0, 0, 0, 0.15)',
                border: '1px solid #E5E7EB',
                overflow: 'hidden',
                zIndex: 1000
            }}
        >
            {/* User Info */}
            <div style={{
                padding: '16px',
                borderBottom: '1px solid #E5E7EB',
                backgroundColor: '#F9FAFB'
            }}>
                <div style={{
                    fontSize: '14px',
                    fontWeight: '600',
                    color: '#111827',
                    marginBottom: '4px'
                }}>
                    {auth.currentUser?.displayName || 'User'}
                </div>
                <div style={{
                    fontSize: '13px',
                    color: '#6B7280',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                }}>
                    {auth.currentUser?.email}
                </div>
            </div>

            {/* Menu Items */}
            <div style={{ padding: '8px' }}>
                {menuItems.map((item, index) => (
                    <button
                        key={index}
                        onClick={item.onClick}
                        style={{
                            width: '100%',
                            padding: '12px 16px',
                            border: 'none',
                            backgroundColor: 'transparent',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px',
                            fontSize: '14px',
                            fontWeight: '500',
                            color: item.danger ? '#EF4444' : '#374151',
                            borderRadius: '8px',
                            transition: 'background-color 0.15s',
                            textAlign: 'left'
                        }}
                        onMouseEnter={(e) => {
                            e.target.style.backgroundColor = item.danger ? '#FEE2E2' : '#F3F4F6';
                        }}
                        onMouseLeave={(e) => {
                            e.target.style.backgroundColor = 'transparent';
                        }}
                    >
                        <span style={{ fontSize: '18px' }}>{item.icon}</span>
                        <span>{item.label}</span>
                    </button>
                ))}
            </div>
        </div>
    );
};

export default UserMenu;

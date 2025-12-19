import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { auth } from '../../../../core/firebase/b2c-config';
import UserMenu from './UserMenu';

const Navbar = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const [showUserMenu, setShowUserMenu] = useState(false);

    const currentUser = auth.currentUser;

    const isActive = (path) => location.pathname === path;

    const navItems = [
        { label: 'Dashboard', path: '/', icon: '🏠' },
        { label: 'Workspaces', path: '/workspaces', icon: '📁' },
        { label: 'Tasks', path: '/tasks', icon: '✓' },
    ];

    return (
        <nav style={{
            backgroundColor: '#FFFFFF',
            borderBottom: '1px solid #E5E7EB',
            position: 'sticky',
            top: 0,
            zIndex: 100,
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
            <div style={{
                maxWidth: '1400px',
                margin: '0 auto',
                padding: '0 24px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                height: '64px'
            }}>
                {/* Logo/Brand */}
                <div
                    onClick={() => navigate('/')}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        cursor: 'pointer',
                        fontSize: '20px',
                        fontWeight: '700',
                        color: '#111827'
                    }}
                >
                    <span style={{ fontSize: '28px' }}>🚀</span>
                    <span>My Workspace</span>
                </div>

                {/* Navigation Links */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                }}>
                    {navItems.map((item) => (
                        <button
                            key={item.path}
                            onClick={() => navigate(item.path)}
                            style={{
                                padding: '8px 16px',
                                borderRadius: '8px',
                                border: 'none',
                                backgroundColor: isActive(item.path) ? '#EEF2FF' : 'transparent',
                                color: isActive(item.path) ? '#6366F1' : '#6B7280',
                                fontSize: '14px',
                                fontWeight: isActive(item.path) ? '600' : '500',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                transition: 'background-color 0.15s, color 0.15s'
                            }}
                            onMouseEnter={(e) => {
                                if (!isActive(item.path)) {
                                    e.target.style.backgroundColor = '#F3F4F6';
                                    e.target.style.color = '#374151';
                                }
                            }}
                            onMouseLeave={(e) => {
                                if (!isActive(item.path)) {
                                    e.target.style.backgroundColor = 'transparent';
                                    e.target.style.color = '#6B7280';
                                }
                            }}
                        >
                            <span>{item.icon}</span>
                            <span>{item.label}</span>
                        </button>
                    ))}
                </div>

                {/* User Menu */}
                <div style={{ position: 'relative' }}>
                    <button
                        data-testid="user-menu-trigger"
                        onClick={() => setShowUserMenu(!showUserMenu)}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            padding: '8px 12px',
                            borderRadius: '8px',
                            border: '1px solid #E5E7EB',
                            backgroundColor: '#FFFFFF',
                            cursor: 'pointer',
                            transition: 'background-color 0.15s'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#F9FAFB'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#FFFFFF'}
                    >
                        <div style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: '50%',
                            backgroundColor: '#6366F1',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'white',
                            fontSize: '14px',
                            fontWeight: '600'
                        }}>
                            {currentUser?.displayName?.[0]?.toUpperCase() || currentUser?.email?.[0]?.toUpperCase() || 'U'}
                        </div>
                        <span style={{
                            fontSize: '14px',
                            color: '#374151',
                            fontWeight: '500',
                            maxWidth: '150px',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                        }}>
                            {currentUser?.displayName || currentUser?.email || 'User'}
                        </span>
                        <svg
                            style={{
                                width: '16px',
                                height: '16px',
                                transition: 'transform 0.2s',
                                transform: showUserMenu ? 'rotate(180deg)' : 'rotate(0deg)'
                            }}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                    </button>

                    {showUserMenu && (
                        <UserMenu onClose={() => setShowUserMenu(false)} />
                    )}
                </div>
            </div>
        </nav>
    );
};

export default Navbar;

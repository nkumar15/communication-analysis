import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const Sidebar = () => {
    const navigate = useNavigate();
    const location = useLocation();

    const menuItems = [
        { id: 'dashboard', label: 'Dashboard', icon: '🏠', path: '/dashboard' },
        { id: 'users', label: 'User Management', icon: '👥', path: '/invitations' },
        { id: 'roles', label: 'Role Management', icon: '🛡️', path: '/roles' },
        { id: 'farmers', label: 'Farmer Management', icon: '🚜', path: '/farmers' }
    ];

    const isActive = (path) => location.pathname === path;

    return (
        <div style={{
            width: '250px',
            height: '100vh',
            backgroundColor: '#1F2937',
            color: 'white',
            display: 'flex',
            flexDirection: 'column',
            position: 'fixed',
            left: 0,
            top: 0
        }}>
            {/* Logo */}
            <div style={{
                padding: '24px',
                borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
            }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px'
                }}>
                    <div style={{
                        width: '40px',
                        height: '40px',
                        backgroundColor: '#4F46E5',
                        borderRadius: '8px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '20px'
                    }}>
                        🔐
                    </div>
                    <div>
                        <div style={{ fontWeight: '700', fontSize: '16px' }}>SSO Portal</div>
                        <div style={{ fontSize: '12px', color: '#9CA3AF' }}>Admin Panel</div>
                    </div>
                </div>
            </div>

            {/* Navigation */}
            <nav style={{ flex: 1, padding: '16px 0' }}>
                {menuItems.map((item) => (
                    <button
                        key={item.id}
                        onClick={() => navigate(item.path)}
                        style={{
                            width: '100%',
                            padding: '12px 24px',
                            backgroundColor: isActive(item.path) ? '#374151' : 'transparent',
                            border: 'none',
                            borderLeft: isActive(item.path) ? '3px solid #4F46E5' : '3px solid transparent',
                            color: isActive(item.path) ? 'white' : '#9CA3AF',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px',
                            fontSize: '15px',
                            fontWeight: isActive(item.path) ? '600' : '500',
                            transition: 'all 0.2s',
                            textAlign: 'left'
                        }}
                        onMouseEnter={(e) => {
                            if (!isActive(item.path)) {
                                e.target.style.backgroundColor = '#374151';
                                e.target.style.color = 'white';
                            }
                        }}
                        onMouseLeave={(e) => {
                            if (!isActive(item.path)) {
                                e.target.style.backgroundColor = 'transparent';
                                e.target.style.color = '#9CA3AF';
                            }
                        }}
                    >
                        <span style={{ fontSize: '20px' }}>{item.icon}</span>
                        <span>{item.label}</span>
                    </button>
                ))}
            </nav>
        </div>
    );
};

export default Sidebar;

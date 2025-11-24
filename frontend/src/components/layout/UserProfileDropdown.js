import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import firebaseAuthService from '../../services/firebaseAuthService';
import apiService from '../../services/api';

const UserProfileDropdown = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [user, setUser] = useState(null);
    const dropdownRef = useRef(null);
    const navigate = useNavigate();

    useEffect(() => {
        loadUser();
    }, []);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };

        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isOpen]);

    const loadUser = async () => {
        try {
            const userInfo = await apiService.getCurrentUser();
            setUser(userInfo);
        } catch (err) {
            console.error('Failed to load user:', err);
        }
    };

    const handleLogout = async () => {
        try {
            await apiService.logout();
            navigate('/login');
        } catch (err) {
            console.error('Logout failed:', err);
        }
    };

    const getInitials = () => {
        if (user?.name) {
            return user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
        }
        return user?.email?.[0]?.toUpperCase() || 'U';
    };

    if (!user) return null;

    return (
        <div ref={dropdownRef} style={{ position: 'relative' }}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '8px 12px',
                    backgroundColor: 'white',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => e.target.style.backgroundColor = '#F9FAFB'}
                onMouseLeave={(e) => e.target.style.backgroundColor = 'white'}
            >
                <div style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '50%',
                    backgroundColor: '#4F46E5',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: '600',
                    fontSize: '14px'
                }}>
                    {getInitials()}
                </div>
                <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: '14px', fontWeight: '600', color: '#111827' }}>
                        {user.name || 'User'}
                    </div>
                    <div style={{ fontSize: '12px', color: '#6B7280' }}>
                        {user.role}
                    </div>
                </div>
                <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" style={{ color: '#6B7280' }}>
                    <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
            </button>

            {isOpen && (
                <div style={{
                    position: 'absolute',
                    right: 0,
                    top: '100%',
                    marginTop: '8px',
                    width: '280px',
                    backgroundColor: 'white',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                    overflow: 'hidden',
                    zIndex: 50
                }}>
                    {/* User Info */}
                    <div style={{ padding: '16px', borderBottom: '1px solid #F3F4F6' }}>
                        <div style={{ fontSize: '14px', fontWeight: '600', color: '#111827', marginBottom: '4px' }}>
                            {user.name || 'User'}
                        </div>
                        <div style={{ fontSize: '13px', color: '#6B7280', marginBottom: '8px' }}>
                            {user.email}
                        </div>
                        <div style={{
                            display: 'inline-block',
                            padding: '4px 8px',
                            backgroundColor: '#EDE9FE',
                            color: '#7C3AED',
                            borderRadius: '4px',
                            fontSize: '12px',
                            fontWeight: '500'
                        }}>
                            {user.role}
                        </div>
                    </div>

                    {/* Tenant Info */}
                    <div style={{ padding: '12px 16px', borderBottom: '1px solid #F3F4F6', backgroundColor: '#F9FAFB' }}>
                        <div style={{ fontSize: '11px', color: '#6B7280', marginBottom: '4px', textTransform: 'uppercase', fontWeight: '600' }}>
                            Organization
                        </div>
                        <div style={{ fontSize: '13px', color: '#111827', fontWeight: '500' }}>
                            {user.tenant_name}
                        </div>
                    </div>

                    {/* Logout Button */}
                    <button
                        onClick={handleLogout}
                        style={{
                            width: '100%',
                            padding: '12px 16px',
                            backgroundColor: 'white',
                            border: 'none',
                            textAlign: 'left',
                            cursor: 'pointer',
                            fontSize: '14px',
                            color: '#DC2626',
                            fontWeight: '500',
                            transition: 'background-color 0.2s',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#FEF2F2'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = 'white'}
                    >
                        <span>🚪</span>
                        <span>Logout</span>
                    </button>
                </div>
            )}
        </div>
    );
};

export default UserProfileDropdown;

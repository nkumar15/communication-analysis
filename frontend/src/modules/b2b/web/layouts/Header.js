import React from 'react';
import UserProfileDropdown from './UserProfileDropdown';

const Header = ({ title, subtitle }) => {
    return (
        <div style={{
            height: '72px',
            backgroundColor: 'white',
            borderBottom: '1px solid #E5E7EB',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 32px',
            position: 'sticky',
            top: 0,
            zIndex: 10
        }}>
            <div>
                {title && (
                    <h1 style={{
                        margin: 0,
                        fontSize: '20px',
                        fontWeight: '700',
                        color: '#111827'
                    }}>
                        {title}
                    </h1>
                )}
                {subtitle && (
                    <p style={{
                        margin: '4px 0 0 0',
                        fontSize: '14px',
                        color: '#6B7280'
                    }}>
                        {subtitle}
                    </p>
                )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                    style={{
                        position: 'relative',
                        background: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        padding: '8px',
                        borderRadius: '50%',
                        color: '#6B7280',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'background-color 0.2s'
                    }}
                    onMouseEnter={(e) => e.target.style.backgroundColor = '#F3F4F6'}
                    onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
                    title="Notifications"
                >
                    <span style={{ fontSize: '20px' }}>🔔</span>
                    {/* Badge placeholder */}
                    <span style={{
                        position: 'absolute',
                        top: '6px',
                        right: '6px',
                        width: '8px',
                        height: '8px',
                        backgroundColor: '#EF4444',
                        borderRadius: '50%',
                        border: '2px solid white'
                    }}></span>
                </button>
                <UserProfileDropdown />
            </div>
        </div>
    );
};

export default Header;

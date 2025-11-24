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

            <UserProfileDropdown />
        </div>
    );
};

export default Header;

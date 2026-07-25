import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import ChatWidget from '../components/ChatWidget';

const B2CLayout = ({ children }) => {
    return (
        <div style={{
            minHeight: '100vh',
            backgroundColor: '#F9FAFB',
            display: 'flex',
            flexDirection: 'column'
        }}>
            <Navbar />

            <main style={{
                flex: 1,
                width: '100%',
                maxWidth: '1200px',
                margin: '0 auto',
                padding: '24px',
            }}>
                {children || <Outlet />}
            </main>

            {/* Optional Footer */}
            <footer style={{
                padding: '24px',
                textAlign: 'center',
                fontSize: '14px',
                color: '#6B7280',
                borderTop: '1px solid #E5E7EB'
            }}>
                © 2025 Your SaaS Platform. All rights reserved.
            </footer>

            {/* Chat Widget */}
            <ChatWidget />
        </div>
    );
};

export default B2CLayout;

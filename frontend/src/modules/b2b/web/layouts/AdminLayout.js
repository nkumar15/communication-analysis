import React, { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import Header from './Header';
import HelpWidget from '../../../../core/components/HelpWidget';

const AdminLayout = ({ children, title, subtitle }) => {
    const [isCollapsed, setIsCollapsed] = useState(() => {
        const saved = localStorage.getItem('sidebar_collapsed');
        return saved === 'true';
    });

    useEffect(() => {
        const handleStorageChange = () => {
            const saved = localStorage.getItem('sidebar_collapsed');
            setIsCollapsed(saved === 'true');
        };

        window.addEventListener('storage', handleStorageChange);
        // Also listen for changes in the same window
        const interval = setInterval(() => {
            const saved = localStorage.getItem('sidebar_collapsed');
            setIsCollapsed(saved === 'true');
        }, 100);

        return () => {
            window.removeEventListener('storage', handleStorageChange);
            clearInterval(interval);
        };
    }, []);

    return (
        <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: '#F9FAFB', color: '#111827' }}>
            <Sidebar />

            <div style={{
                marginLeft: isCollapsed ? '80px' : '250px',
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                transition: 'margin-left 0.3s ease'
            }}>
                <Header title={title} subtitle={subtitle} />

                <main style={{ flex: 1, overflow: 'auto' }}>
                    {children}
                </main>
            </div>

            {/* Global Help Widget */}
            <HelpWidget />
        </div>
    );
};

export default AdminLayout;

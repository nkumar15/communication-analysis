import React from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

const AdminLayout = ({ children, title, subtitle }) => {
    return (
        <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: '#F9FAFB' }}>
            <Sidebar />

            <div style={{ marginLeft: '250px', flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Header title={title} subtitle={subtitle} />

                <main style={{ flex: 1, overflow: 'auto' }}>
                    {children}
                </main>
            </div>
        </div>
    );
};

export default AdminLayout;

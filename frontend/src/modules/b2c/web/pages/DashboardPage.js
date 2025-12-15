
import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { auth } from '../../../../core/firebase/b2c-config';

const DashboardPage = () => {
    const navigate = useNavigate();
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const unsubscribe = auth.onAuthStateChanged(async (firebaseUser) => {
            if (!firebaseUser) {
                navigate('/login');
                return;
            }

            try {
                const idToken = await firebaseUser.getIdToken();
                const response = await fetch('/api/b2c/auth/me', {
                    headers: {
                        'Authorization': `Bearer ${idToken}`
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    setUser(data);
                } else {
                    if (response.status === 404 || response.status === 401) {
                        await auth.signOut();
                        navigate('/login');
                    }
                }
            } catch (error) {
                console.error('Failed to fetch user profile:', error);
            } finally {
                setLoading(false);
            }
        });

        return () => unsubscribe();
    }, [navigate]);

    const handleLogout = async () => {
        await auth.signOut();
        navigate('/login');
    };

    if (loading) {
        return (
            <div className="loading-container">
                <div className="spinner large"></div>
            </div>
        );
    }

    return (
        <div className="dashboard-container">
            <nav className="dashboard-nav">
                <div className="nav-content">
                    <div className="nav-brand">
                        <span style={{ fontSize: '1.5rem' }}>🚀</span>
                        <span className="brand-text">My Workspace</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>
                            {user?.display_name || user?.email}
                        </span>
                        <button
                            onClick={handleLogout}
                            className="logout-button"
                        >
                            Sign out
                        </button>
                    </div>
                </div>
            </nav>

            <main className="dashboard-main">
                <header className="welcome-header">
                    <div className="user-avatar">
                        {user?.display_name ? user.display_name.charAt(0).toUpperCase() : 'U'}
                    </div>
                    <div className="welcome-text">
                        <h1>Welcome, {user?.display_name?.split(' ')[0] || 'User'}!</h1>
                        <p className="user-email">{user?.email}</p>
                    </div>
                </header>

                <section style={{ marginBottom: 'var(--spacing-lg)' }}>
                    <h2 style={{ fontSize: '1.5rem', marginBottom: 'var(--spacing-md)', fontWeight: 600 }}>Your Workspaces</h2>

                    <div className="dashboard-content">
                        {user?.workspaces?.map((workspace) => (
                            <div
                                key={workspace.id}
                                className="content-card"
                                style={{ cursor: 'pointer' }}
                                onClick={() => navigate(`/workspace/${workspace.id}`)}
                            >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--spacing-sm)' }}>
                                    <span className={`status-badge ${workspace.type === 'personal' ? 'success' : ''}`}>
                                        {workspace.type === 'personal' ? 'Personal' : 'Team'}
                                    </span>
                                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{workspace.role}</span>
                                </div>

                                <h2>{workspace.name}</h2>
                                <p style={{ marginBottom: 'var(--spacing-md)', color: 'var(--text-secondary)' }}>
                                    Manage your projects and settings in this workspace.
                                </p>

                                <div style={{ display: 'flex', alignItems: 'center', color: '#667eea', fontWeight: 500 }}>
                                    Open Workspace <span className="arrow" style={{ marginLeft: '5px' }}>→</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

            </main>
        </div>
    );
};

export default DashboardPage;

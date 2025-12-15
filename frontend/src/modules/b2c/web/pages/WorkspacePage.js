
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { auth } from '../../../../core/firebase/b2c-config';

const WorkspacePage = () => {
    const { workspaceId } = useParams();
    const navigate = useNavigate();
    const [workspace, setWorkspace] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchWorkspace = async () => {
            const user = auth.currentUser;
            if (!user) {
                // Maybe wait for AuthStateChanged in a real hook, but for now simple check
                // Actually, if we refresh page, currentUser might be null initially.
                // We should wrap this in onAuthStateChanged or use a global context.
                // For simplicity in this demo, we assume Dashboard redirected correctly, 
                // but explicit check loop is better.
                // Let's attach listener to be safe.
            }
        };

        const unsubscribe = auth.onAuthStateChanged(async (user) => {
            if (!user) {
                navigate('/login');
                return;
            }

            try {
                const idToken = await user.getIdToken();
                const response = await fetch(`/api/b2c/workspaces/${workspaceId}`, {
                    headers: { 'Authorization': `Bearer ${idToken}` }
                });

                if (response.ok) {
                    const data = await response.json();
                    setWorkspace(data);
                } else {
                    navigate('/dashboard');
                }
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        });

        return () => unsubscribe();
    }, [workspaceId, navigate]);

    if (loading) return (
        <div className="loading-container">
            <div className="spinner"></div>
        </div>
    );

    if (!workspace) return <div className="error-state">Workspace not found</div>;

    return (
        <div className="dashboard-container">
            <nav className="dashboard-nav">
                <div className="nav-content">
                    <div className="nav-brand" style={{ cursor: 'pointer' }} onClick={() => navigate('/dashboard')}>
                        <span style={{ fontSize: '1.2rem' }}>←</span>
                        <span className="brand-text">Back to Dashboard</span>
                    </div>
                    <div>
                        <span className="status-badge" style={{ background: 'rgba(255,255,255,0.1)' }}>
                            {workspace.name}
                        </span>
                    </div>
                </div>
            </nav>

            <main className="dashboard-main">
                <div className="welcome-card" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
                    <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🚧</div>
                    <h1>Projects Coming Soon</h1>
                    <p style={{ color: 'var(--text-secondary)', maxWidth: '400px', margin: '0 0 2rem 0', display: 'inline-block' }}>
                        We are building the project management features for your workspace. Stay tuned!
                    </p>
                    <div>
                        <button className="submit-button" disabled style={{ width: 'auto', display: 'inline-flex' }}>
                            Create Project
                        </button>
                    </div>
                </div>

                <div className="info-grid">
                    <div className="info-item">
                        <div className="info-label">Workspace Type</div>
                        <div className="info-value" style={{ textTransform: 'capitalize' }}>{workspace.type}</div>
                    </div>
                    <div className="info-item">
                        <div className="info-label">Your Role</div>
                        <div className="info-value" style={{ textTransform: 'capitalize' }}>{workspace.role}</div>
                    </div>
                    <div className="info-item">
                        <div className="info-label">Subscription</div>
                        <div className="info-value" style={{ textTransform: 'capitalize' }}>{workspace.subscription_tier || 'Free'}</div>
                    </div>
                </div>

            </main>
        </div>
    );
};

export default WorkspacePage;

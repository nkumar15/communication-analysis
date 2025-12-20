import { useProduct } from '../layouts/SuperAdminLayout';

function WorkspacesPage() {
    const { selectedProduct } = useProduct();

    // Redirect to dashboard if not in B2C mode
    if (selectedProduct !== 'b2c') {
        return (
            <div>
                <div className="platform-page-header">
                    <h1 className="platform-page-title">Workspaces</h1>
                </div>
                <div className="platform-card">
                    <div style={{ textAlign: 'center', padding: '3rem 0' }}>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔒</div>
                        <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '0.5rem', color: '#1f2937' }}>B2C Mode Required</h2>
                        <p style={{ color: '#6b7280' }}>Switch to B2C mode to manage workspaces.</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div>
            <div className="platform-page-header">
                <div>
                    <h1 className="platform-page-title">B2C Workspaces</h1>
                    <p style={{ color: '#6b7280', marginTop: '0.25rem' }}>
                        Manage personal and team workspaces for B2C users.
                    </p>
                </div>
            </div>

            <div className="platform-card">
                <div style={{ textAlign: 'center', padding: '3rem 0' }}>
                    <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📁</div>
                    <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '0.5rem', color: '#1f2937' }}>Workspace Management Coming Soon</h2>
                    <p style={{ color: '#6b7280' }}>View and manage B2C user workspaces will be available here.</p>
                </div>
            </div>
        </div>
    );
}

export default WorkspacesPage;

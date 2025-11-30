import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom';
import platformApiService from '../../../core/api/platformClient';
import '../styles/platform.css';

function SuperAdminLayout() {
    const navigate = useNavigate();
    const location = useLocation();

    const handleLogout = async () => {
        try {
            await platformApiService.logout();
            navigate('/platform-login');
        } catch (error) {
            console.error('Logout failed:', error);
        }
    };

    const isActive = (path) => location.pathname.includes(path);

    return (
        <div className="platform-layout">
            <aside className="platform-sidebar">
                <div className="platform-brand">
                    <span>⚡ SaaS Platform</span>
                </div>

                <nav className="platform-nav">
                    <Link to="/super-admin/dashboard" className={`platform-nav-item ${isActive('/dashboard') ? 'active' : ''}`}>
                        <span>📊 Dashboard</span>
                    </Link>
                    <Link to="/super-admin/tenants" className={`platform-nav-item ${isActive('/tenants') ? 'active' : ''}`}>
                        <span>🏢 Tenants</span>
                    </Link>
                    <Link to="/super-admin/analytics" className={`platform-nav-item ${isActive('/analytics') ? 'active' : ''}`}>
                        <span>📈 Analytics</span>
                    </Link>
                    <Link to="/super-admin/settings" className={`platform-nav-item ${isActive('/settings') ? 'active' : ''}`}>
                        <span>⚙️ Settings</span>
                    </Link>
                </nav>
            </aside>

            <main className="platform-main">
                <header className="platform-header">
                    <div className="platform-header-title">Platform Overview</div>
                    <div className="platform-user-menu">
                        <span className="platform-badge">Platform Admin</span>
                        <button onClick={handleLogout} className="platform-btn platform-btn-outline">
                            Logout
                        </button>
                    </div>
                </header>

                <div className="platform-content">
                    <Outlet />
                </div>
            </main>
        </div>
    );
}

export default SuperAdminLayout;

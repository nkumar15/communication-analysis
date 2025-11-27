import { Link, Outlet, useNavigate } from 'react-router-dom';
import apiService from '../services/api';
import '../styles/super-admin.css';

function SuperAdminLayout() {
    const navigate = useNavigate();

    const handleLogout = async () => {
        try {
            await apiService.logout();
            navigate('/login');
        } catch (error) {
            console.error('Logout failed:', error);
        }
    };

    return (
        <div className="saas-layout">
            <aside className="saas-sidebar">
                <div className="saas-brand">
                    <span>⚡ SaaS Admin</span>
                </div>

                <nav className="saas-nav">
                    <Link to="/super-admin/dashboard" className="saas-nav-item active">
                        <span>📊 Dashboard</span>
                    </Link>
                    <Link to="/super-admin/tenants" className="saas-nav-item">
                        <span>🏢 Tenants</span>
                    </Link>
                    <Link to="/super-admin/analytics" className="saas-nav-item">
                        <span>📈 Analytics</span>
                    </Link>
                    <Link to="/super-admin/settings" className="saas-nav-item">
                        <span>⚙️ Settings</span>
                    </Link>
                </nav>
            </aside>

            <main className="saas-main">
                <header className="saas-header">
                    <div className="saas-header-title">Platform Overview</div>
                    <div className="saas-user-menu">
                        <span className="saas-badge active">Platform Admin</span>
                        <button onClick={handleLogout} className="saas-btn saas-btn-outline">
                            Logout
                        </button>
                    </div>
                </header>

                <div className="saas-content">
                    <Outlet />
                </div>
            </main>
        </div>
    );
}

export default SuperAdminLayout;

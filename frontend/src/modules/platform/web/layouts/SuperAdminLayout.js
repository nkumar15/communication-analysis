import { useState, createContext, useContext } from 'react';
import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom';
import platformApiService from '../../../../core/api/platformClient';
import '../styles/platform.css';

// Create context for product selection
export const ProductContext = createContext();

export function useProduct() {
    return useContext(ProductContext);
}

function SuperAdminLayout() {
    const navigate = useNavigate();
    const location = useLocation();
    const [selectedProduct, setSelectedProduct] = useState(() => {
        return localStorage.getItem('platform_product') || 'b2b';
    });

    const handleProductChange = (product) => {
        setSelectedProduct(product);
        localStorage.setItem('platform_product', product);
        navigate('/dashboard');
    };

    const handleLogout = async () => {
        try {
            await platformApiService.logout();
            navigate('/login');
        } catch (error) {
            console.error('Logout failed:', error);
        }
    };



    const isActive = (path) => location.pathname.includes(path);

    const products = [
        { id: 'b2b', label: '🏢 B2B Enterprise', color: '#6366f1' },
        { id: 'b2c', label: '👤 B2C Personal', color: '#10b981' }
    ];

    const currentProduct = products.find(p => p.id === selectedProduct);

    return (
        <ProductContext.Provider value={{ selectedProduct, setSelectedProduct }}>
            <div className="platform-layout">
                <aside className="platform-sidebar">
                    <div className="platform-brand">
                        <span>⚡ SaaS Platform</span>
                    </div>

                    {/* Product Selector */}
                    <div style={{ padding: '0 1rem', marginBottom: '1rem' }}>
                        <select
                            value={selectedProduct}
                            onChange={(e) => handleProductChange(e.target.value)}
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                borderRadius: '0.5rem',
                                border: '1px solid rgba(255,255,255,0.2)',
                                background: 'rgba(255,255,255,0.1)',
                                color: 'white',
                                fontSize: '0.875rem',
                                fontWeight: '500',
                                cursor: 'pointer',
                                appearance: 'none',
                                backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%23fff' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`,
                                backgroundPosition: 'right 0.5rem center',
                                backgroundRepeat: 'no-repeat',
                                backgroundSize: '1.5em 1.5em'
                            }}
                        >
                            {products.map(p => (
                                <option key={p.id} value={p.id} style={{ background: '#1f2937', color: 'white' }}>
                                    {p.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    <nav className="platform-nav">
                        {/* Core */}
                        <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                            Core
                        </div>
                        <Link to="/dashboard" className={`platform-nav-item ${isActive('/dashboard') || location.pathname === '/' ? 'active' : ''}`}>
                            <span>📊 Dashboard</span>
                        </Link>
                        <Link to="/analytics" className={`platform-nav-item ${isActive('/analytics') ? 'active' : ''}`}>
                            <span>📈 Analytics</span>
                        </Link>

                        {/* Business */}
                        <div className="my-2 border-t border-gray-700/50"></div>
                        <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                            Business
                        </div>
                        {selectedProduct === 'b2b' ? (
                            <>
                                <Link to="/tenants" className={`platform-nav-item ${isActive('/tenants') ? 'active' : ''}`}>
                                    <span>🏢 Tenants</span>
                                </Link>
                                <Link to="/b2b-plans" className={`platform-nav-item ${isActive('/b2b-plans') ? 'active' : ''}`}>
                                    <span>💰 Plans</span>
                                </Link>
                            </>
                        ) : (
                            <>
                                <Link to="/workspaces" className={`platform-nav-item ${isActive('/workspaces') ? 'active' : ''}`}>
                                    <span>📁 Workspaces</span>
                                </Link>
                                <Link to="/plans" className={`platform-nav-item ${isActive('/plans') ? 'active' : ''}`}>
                                    <span>💰 Plans</span>
                                </Link>
                            </>
                        )}

                        {/* Billing */}
                        <div className="my-2 border-t border-gray-700/50"></div>
                        <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                            Billing
                        </div>
                        <Link to="/billing" className={`platform-nav-item ${isActive('/billing') && !isActive('/billing/coupons') ? 'active' : ''}`}>
                            <span>💳 Overview</span>
                        </Link>
                        <Link to="/billing/coupons" className={`platform-nav-item ${isActive('/billing/coupons') ? 'active' : ''}`}>
                            <span>🎟️ Coupons</span>
                        </Link>

                        {/* System */}
                        <div className="my-2 border-t border-gray-700/50"></div>
                        <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                            System
                        </div>
                        <Link to="/system-health" className={`platform-nav-item ${isActive('/system-health') ? 'active' : ''}`}>
                            <span>🏥 Health</span>
                        </Link>
                        <Link to="/audit-logs" className={`platform-nav-item ${isActive('/audit-logs') ? 'active' : ''}`}>
                            <span>📋 Audit Logs</span>
                        </Link>

                        {/* Management */}
                        <div className="my-2 border-t border-gray-700/50"></div>
                        <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                            Management
                        </div>
                        <Link to="/roles" className={`platform-nav-item ${isActive('/roles') ? 'active' : ''}`}>
                            <span>🛡️ Roles</span>
                        </Link>
                        <Link to="/users" className={`platform-nav-item ${isActive('/users') ? 'active' : ''}`}>
                            <span>👥 Users</span>
                        </Link>
                        <Link to="/settings" className={`platform-nav-item ${isActive('/settings') ? 'active' : ''}`}>
                            <span>⚙️ Settings</span>
                        </Link>
                    </nav>
                </aside>

                <main className="platform-main">
                    <header className="platform-header">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <span style={{
                                padding: '0.25rem 0.75rem',
                                borderRadius: '9999px',
                                fontSize: '0.75rem',
                                fontWeight: '600',
                                background: selectedProduct === 'b2b' ? 'rgba(99, 102, 241, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                                color: selectedProduct === 'b2b' ? '#6366f1' : '#10b981',
                                border: `1px solid ${selectedProduct === 'b2b' ? '#6366f1' : '#10b981'}`
                            }}>
                                {currentProduct?.label}
                            </span>
                            <span className="platform-header-title">Platform Admin</span>
                        </div>
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
        </ProductContext.Provider>
    );
}

export default SuperAdminLayout;

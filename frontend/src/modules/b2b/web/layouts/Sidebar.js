import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import useAuth from '../../../../core/hooks/useAuth';
import { TENANT_ROLES, getTenantRoleLabel } from '../../constants/roles';

const Sidebar = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { user, canAccess, loading } = useAuth();
    const [isCollapsed, setIsCollapsed] = useState(() => {
        const saved = localStorage.getItem('sidebar_collapsed');
        return saved === 'true';
    });


    useEffect(() => {
        localStorage.setItem('sidebar_collapsed', isCollapsed);
    }, [isCollapsed]);

    // Core menu items (always shown)
    const coreMenuItems = [
        { id: 'dashboard', label: 'Dashboard', icon: '🏠', path: '/dashboard', feature: 'dashboard' },
    ];


    // Domain-specific menus
    const domainMenus = {
        bank_surveillance: [
            { isHeader: true, label: 'Surveillance' },
            { id: 'surv-dashboard', label: 'Overview', icon: '📊', path: '/b2b/surveillance', feature: 'surveillance' },
            { id: 'communications', label: 'Communications', icon: '💬', path: '/b2b/surveillance/communications', feature: 'surveillance' },
            { id: 'investigations', label: 'Investigations', icon: '🔍', path: '/b2b/surveillance/investigations', feature: 'surveillance' },
            { id: 'rag-enron', label: 'Email Knowledge Base', icon: '📧', path: '/b2b/c/enron', feature: 'surveillance' },
            { id: 'ingestion', label: 'Data Ingestion', icon: '📥', path: '/b2b/surveillance/ingestion', feature: 'surveillance' },
        ],
        marketing_agency: [
            { isHeader: true, label: 'Campaigns' },
            { id: 'campaigns-active', label: 'Active Campaigns', icon: '📢', path: '/b2b/campaigns', feature: 'campaigns' },
            { id: 'campaigns-drafts', label: 'Drafts', icon: '📝', path: '/b2b/campaigns/drafts', feature: 'campaigns' },
            { isHeader: true, label: 'Social Media' },
            { id: 'social-posts', label: 'Posts', icon: '📱', path: '/b2b/social/posts', feature: 'social_posts' },
            { id: 'social-scheduler', label: 'Scheduler', icon: '📅', path: '/b2b/social/scheduler', feature: 'social_posts' },
        ],
        default: []
    };

    // Common Domains (always shown below specific domains)
    const commonDomainItems = [
        { isHeader: true, label: 'Domains' },
        { id: 'projects', label: 'Projects', icon: '📋', path: '/projects', feature: 'projects' },
    ];

    // Organization & Config (always shown)
    const organizationMenuItems = [
        { isHeader: true, label: 'Organization' },
        { id: 'teams', label: 'Teams', icon: '🏢', path: '/b2b/teams', feature: 'teams' },
        { id: 'users', label: 'User Management', icon: '👥', path: '/invitations', feature: 'users' },

        { isHeader: true, label: 'Configuration' },
        { id: 'roles', label: 'Tenant Roles', icon: '🛡️', path: '/roles', feature: 'roles' },
        { id: 'team-roles', label: 'Team Roles', icon: '🎯', path: '/team-roles', feature: 'roles' }
    ];

    // Determine domain menu items
    // Hybrid approach: Respect explicit tenant domain_type, but also allow permissions to unlock domains
    // This supports "Default" tenants having teams that use specific domain features (like Surveillance)

    let domainItems = [];
    const userDomainType = user?.domain_type || 'default';

    // 1. Start with tenant's configured domain menu (if not default/empty)
    if (userDomainType !== 'default' && domainMenus[userDomainType]) {
        domainItems = domainMenus[userDomainType];
    }

    // 2. Add Surveillance menu if user has access (via specific Team Role)
    // even if tenant is 'default'
    if (canAccess('surveillance') && userDomainType !== 'bank_surveillance') {
        const surveillanceMenu = domainMenus.bank_surveillance;
        // Avoid duplicates if we already added it (rare case of overlapping types)
        if (domainItems !== surveillanceMenu) {
            domainItems = [...domainItems, ...surveillanceMenu];
        }
    }

    // 3. Fallback: if absolutely nothing is selected, use default
    if (domainItems.length === 0) {
        domainItems = domainMenus.default;
    }

    // Build complete menu
    const allMenuItems = [
        ...coreMenuItems,
        ...domainItems,
        ...commonDomainItems,
        ...organizationMenuItems
    ];

    // Filter menu items based on user permissions
    // Note: This simple filter leaves headers even if all their children are hidden.
    // Ideally we'd do a reduce or smarter filter, but this is acceptable for now.
    const menuItems = allMenuItems.filter(item => item.isHeader || canAccess(item.feature));

    const isActive = (path) => location.pathname === path;

    // Show loading state
    if (loading) {
        return (
            <div style={{
                width: '250px',
                height: '100vh',
                backgroundColor: '#1F2937',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
            }}>
                <div style={{ color: '#9CA3AF' }}>Loading...</div>
            </div>
        );
    }

    return (
        <div style={{
            width: isCollapsed ? '80px' : '250px',
            height: '100vh',
            backgroundColor: '#1F2937',
            color: 'white',
            display: 'flex',
            flexDirection: 'column',
            position: 'fixed',
            left: 0,
            top: 0,
            transition: 'width 0.3s ease'
        }}>
            {/* Logo */}
            <div style={{
                padding: isCollapsed ? '16px' : '24px',
                borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                transition: 'padding 0.3s ease'
            }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    justifyContent: isCollapsed ? 'center' : 'flex-start'
                }}>
                    <div style={{
                        width: '40px',
                        height: '40px',
                        backgroundColor: '#4F46E5',
                        borderRadius: '8px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '20px'
                    }}>
                        🔐
                    </div>
                    {!isCollapsed && (
                        <div>
                            <div style={{ fontWeight: '700', fontSize: '16px' }}>B2B SaaS App</div>
                            <div style={{ fontSize: '12px', color: '#9CA3AF' }}>
                                {getTenantRoleLabel(user?.role)}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Navigation */}
            <nav style={{ flex: 1, padding: '16px 0', overflowY: 'auto' }}>
                {menuItems.map((item, index) => {
                    if (item.isHeader) {
                        if (isCollapsed) return null; // Hide headers when collapsed
                        return (
                            <div key={`header-${index}`} style={{
                                padding: '24px 24px 8px',
                                fontSize: '11px',
                                textTransform: 'uppercase',
                                color: '#9CA3AF',
                                fontWeight: '600',
                                letterSpacing: '0.05em'
                            }}>
                                {item.label}
                            </div>
                        );
                    }

                    return (
                        <button
                            key={item.id}
                            onClick={() => navigate(item.path)}
                            title={isCollapsed ? item.label : ''}
                            style={{
                                width: '100%',
                                padding: isCollapsed ? '12px' : '10px 24px',
                                backgroundColor: isActive(item.path) ? 'rgba(255, 255, 255, 0.05)' : 'transparent',
                                border: 'none',
                                borderLeft: isActive(item.path) ? '3px solid #6366F1' : '3px solid transparent',
                                color: isActive(item.path) ? 'white' : '#D1D5DB',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: isCollapsed ? 'center' : 'flex-start',
                                gap: '12px',
                                fontSize: '14px',
                                fontWeight: isActive(item.path) ? '500' : '400',
                                transition: 'all 0.15s',
                                textAlign: 'left',
                                marginBottom: '2px'
                            }}
                            onMouseEnter={(e) => {
                                if (!isActive(item.path)) {
                                    e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.05)';
                                    e.target.style.color = 'white';
                                }
                            }}
                            onMouseLeave={(e) => {
                                if (!isActive(item.path)) {
                                    e.target.style.backgroundColor = 'transparent';
                                    e.target.style.color = '#D1D5DB';
                                }
                            }}
                        >
                            <span style={{ fontSize: '18px', opacity: isActive(item.path) ? 1 : 0.7 }}>{item.icon}</span>
                            {!isCollapsed && <span>{item.label}</span>}
                        </button>
                    );
                })}
            </nav>

            {/* Collapse Toggle Button */}
            <button
                onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setIsCollapsed(!isCollapsed);
                }}
                style={{
                    padding: '16px',
                    backgroundColor: '#374151',
                    border: 'none',
                    borderTop: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#9CA3AF',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    fontSize: '14px',
                    fontWeight: '500',
                    transition: 'background-color 0.2s, color 0.2s'
                }}
                onMouseEnter={(e) => {
                    e.target.style.backgroundColor = '#4B5563';
                    e.target.style.color = 'white';
                }}
                onMouseLeave={(e) => {
                    e.target.style.backgroundColor = '#374151';
                    e.target.style.color = '#9CA3AF';
                }}
            >
                <span style={{ fontSize: '18px' }}>{isCollapsed ? '▶' : '◀'}</span>
                {!isCollapsed && <span>Collapse</span>}
            </button>
        </div>
    );
};

export default Sidebar;

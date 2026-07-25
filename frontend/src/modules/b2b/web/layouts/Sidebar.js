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


    // Hardcoded for Communication Surveillance as per requirement
    useEffect(() => {
        document.title = "Communication Surveillance";
    }, []);

    // Core menu items (Personal Workspace)
    const personalMenuItems = [
        { isHeader: true, label: 'Personal Workspace' },
        { id: 'dashboard', label: 'My Workspace', icon: '🏠', path: '/dashboard', feature: 'dashboard:read' },
    ];


    // Domain-specific menus
    // feature values use 'resource:action' strings directly — no mapping layer needed.
    const domainMenus = {
        bank_surveillance: [
            { isHeader: true, label: 'Surveillance Suite' },
            { id: 'surv-dashboard', label: 'Command Center', icon: '🚀', path: '/b2b/surveillance', feature: 'communications:read' },
            { id: 'alerts', label: 'Alerts', icon: '⚠️', path: '/b2b/surveillance/alerts', feature: 'alerts:read' },
            // { id: 'communications', label: 'Communications', icon: '💬', path: '/b2b/surveillance/communications', feature: 'communications:read' },
            { id: 'cases', label: 'Case Management', icon: '⚖️', path: '/b2b/surveillance/cases', feature: 'cases:read' },
            { id: 'regulatory-library', label: 'Regulatory Library', icon: '📜', path: '/b2b/surveillance/regulatory', feature: 'regulatory:read' },
            { id: 'surveillance-controls', label: 'Surveillance Controls', icon: '🛡️', path: '/b2b/surveillance/controls', feature: 'controls:read' },
            { id: 'knowledge-base', label: 'Search & Discover', icon: '📚', path: '/b2b/surveillance/knowledge-base', feature: 'rag_search:read' },
            { id: 'ingestion', label: 'Data Ingestion', icon: '📥', path: '/b2b/surveillance/ingestion', feature: 'ingestion:read' },
        ],
        marketing_agency: [
            { isHeader: true, label: 'Campaigns' },
            { id: 'campaigns-active', label: 'Active Campaigns', icon: '📢', path: '/b2b/campaigns', feature: 'campaigns:read' },
            { id: 'campaigns-drafts', label: 'Drafts', icon: '📝', path: '/b2b/campaigns/drafts', feature: 'campaigns:read' },
            { isHeader: true, label: 'Social Media' },
            { id: 'social-posts', label: 'Posts', icon: '📱', path: '/b2b/social/posts', feature: 'social_posts:read' },
            { id: 'social-scheduler', label: 'Scheduler', icon: '📅', path: '/b2b/social/scheduler', feature: 'social_posts:read' },
        ],
        default: []
    };

    // Common Domains (always shown below specific domains)
    const commonDomainItems = [
        { isHeader: true, label: 'Domains' },
        { id: 'projects', label: 'Projects', icon: '📋', path: '/projects', feature: 'projects:read' },
    ];

    // Organization & Config (always shown)
    const organizationMenuItems = [
        { isHeader: true, label: 'Organization' },
        { id: 'teams', label: 'Teams', icon: '🏢', path: '/b2b/teams', feature: 'teams:read' },
        { id: 'users', label: 'User Management', icon: '👥', path: '/invitations', feature: 'users:read' },
        { id: 'roles', label: 'Roles & Permissions', icon: '🛡️', path: '/roles', feature: 'roles:read' },
        { id: 'team-roles', label: 'Team Roles', icon: '👔', path: '/team-roles', feature: 'teams:write' },
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
    if (canAccess('communications:read') && userDomainType !== 'bank_surveillance') {
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
    // STRATEGIC CHANGE: Domain items come FIRST to emphasize the Product.
    // Personal/Foundational items move to the bottom.
    const allMenuItems = [
        ...domainItems,
        // ...commonDomainItems,
        ...organizationMenuItems,
        ...personalMenuItems
    ];

    // Filter menu items based on user permissions, removing orphan headers.
    // A header is kept only if at least one non-header item follows it and passes canAccess.
    const visibleItems = allMenuItems.filter(item => item.isHeader || canAccess(item.feature));
    const menuItems = visibleItems.filter((item, idx) => {
        if (!item.isHeader) return true;
        // Keep header only if the next item exists and is not itself a header
        const next = visibleItems[idx + 1];
        return next && !next.isHeader;
    });

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
                            <div style={{ fontWeight: '700', fontSize: '16px' }}>Communication Surveillance</div>
                            <div style={{ fontSize: '12px', color: '#9CA3AF' }}>
                                {user?.tenant_name || 'Organization'}
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

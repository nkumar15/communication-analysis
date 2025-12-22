/**
 * Platform Application Root Component
 * SaaS admin console for platform operators
 */
import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import SuperAdminLayout from './web/layouts/SuperAdminLayout';
import TenantList from './web/pages/TenantListPage';
import TenantDetailsPage from './web/pages/TenantDetailsPage';
import Dashboard from './web/pages/DashboardPage';
import WorkspacesPage from './web/pages/WorkspacesPage';
import AnalyticsPage from './web/pages/AnalyticsPage';
import SettingsPage from './web/pages/SettingsPage';
import AuditLogsPage from './web/pages/AuditLogsPage';
import SystemHealthPage from './web/pages/SystemHealthPage';
import PlanManagementPage from './web/pages/PlanManagementPage';
import B2BPlanManagementPage from './web/pages/B2BPlanManagementPage';
import BillingPage from './web/pages/BillingPage';
import BillingCouponsPage from './web/pages/BillingCouponsPage';
import RolesPage from './pages/RolesPage';
import UsersPage from './pages/UsersPage';
import PlatformLogin from './web/pages/LoginPage';
import PlatformAdminRoute from '../../core/components/PlatformAdminRoute';
import firebaseAuthService from '../../core/firebase/authService';
import '../../styles/main.css';

function PlatformApp() {
    const [initialized, setInitialized] = useState(false);

    useEffect(() => {
        const initAuth = async () => {
            await firebaseAuthService.auth.authStateReady();
            setInitialized(true);
        };
        initAuth();
    }, []);

    if (!initialized) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                <p>Loading...</p>
            </div>
        );
    }

    return (
        <BrowserRouter>
            <Routes>
                {/* Platform Login */}
                <Route path="/login" element={<PlatformLogin />} />

                {/* Protected Platform Routes */}
                <Route element={<PlatformAdminRoute />}>
                    <Route element={<SuperAdminLayout />}>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/dashboard" element={<Dashboard />} />
                        <Route path="/tenants" element={<TenantList />} />
                        <Route path="/tenants/:tenantId" element={<TenantDetailsPage />} />
                        <Route path="/roles" element={<RolesPage />} />
                        <Route path="/users" element={<UsersPage />} />
                        <Route path="/workspaces" element={<WorkspacesPage />} />
                        <Route path="/analytics" element={<AnalyticsPage />} />
                        <Route path="/audit-logs" element={<AuditLogsPage />} />
                        <Route path="/system-health" element={<SystemHealthPage />} />
                        <Route path="/settings" element={<SettingsPage />} />
                        <Route path="/plans" element={<PlanManagementPage />} />
                        <Route path="/b2b-plans" element={<B2BPlanManagementPage />} />
                        <Route path="/billing" element={<BillingPage />} />
                        <Route path="/billing/coupons" element={<BillingCouponsPage />} />
                    </Route>
                </Route>

                {/* Catch-all redirect */}
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </BrowserRouter>
    );
}

export default PlatformApp;

import { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './components/LoginPage';
import DashboardPage from './components/DashboardPage';
import ActivationPage from './components/ActivationPage';
import InvitationsPage from './components/InvitationsPage';
import InvitationAcceptPage from './components/InvitationAcceptPage';
import ProtectedRoute from './components/ProtectedRoute';
import firebaseAuthService from './services/firebaseAuthService';
import { auth } from './firebase-config';
import RoleManagementPage from './components/RoleManagementPage';
import FarmerManagementPage from './components/FarmerManagementPage';
import PlatformAdminRoute from './components/PlatformAdminRoute';
import SuperAdminLayout from './layouts/SuperAdminLayout';
import TenantList from './pages/super-admin/TenantList';
import Dashboard from './pages/super-admin/Dashboard';
import PlatformLogin from './components/PlatformLogin';

import apiService from './services/api';
import './styles/main.css';

function App() {
    const [initialized, setInitialized] = useState(false);

    useEffect(() => {
        const initAuth = async () => {
            console.log('⏳ Waiting for Firebase auth to be ready...');

            // Wait for Firebase to finish initializing and restoring any previous auth state
            await firebaseAuthService.auth.authStateReady();
            console.log('✅ Firebase auth is ready');

            setInitialized(true);
        };

        initAuth();

        // Set up auth state listener
        const unsubscribe = firebaseAuthService.onAuthStateChanged(async (user) => {
            if (user) {
                console.log('🔔 Auth state changed:', user.email);

                // Check if this is a platform admin tenant
                // Platform admins should NOT call sync-user (they use /api/platform/auth/me)
                const tenantId = localStorage.getItem('firebase_tenant_id') || auth.tenantId;
                const isPlatformAdmin = tenantId && (tenantId.includes('platform') || tenantId.includes('system'));

                if (!isPlatformAdmin) {
                    // User already signed in from previous session - sync with backend
                    try {
                        await apiService.syncUser();
                    } catch (error) {
                        console.error('❌ Error syncing user:', error);
                    }
                } else {
                    console.log('⚠️ Skipping syncUser for platform admin in App.js');
                }
            }
        });

        return () => unsubscribe();
    }, []);

    if (!initialized) {
        return (
            <div className="loading-container">
                <div className="spinner large"></div>
                <p>Initializing...</p>
            </div>
        );
    }

    return (
        <Router>
            <Routes>
                {/* Public routes */}
                <Route path="/login" element={<LoginPage />} />
                <Route path="/activate/:token" element={<ActivationPage />} />
                <Route path="/invite/:token" element={<InvitationAcceptPage />} />

                {/* Protected routes */}
                <Route
                    path="/dashboard"
                    element={
                        <ProtectedRoute>
                            <DashboardPage />
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/invitations"
                    element={
                        <ProtectedRoute>
                            <InvitationsPage />
                        </ProtectedRoute>
                    }
                />

                {/* New routes */}
                <Route path="/roles" element={<ProtectedRoute><RoleManagementPage /></ProtectedRoute>} />
                <Route path="/farmers" element={<ProtectedRoute><FarmerManagementPage /></ProtectedRoute>} />

                {/* SaaS Admin Console */}
                <Route
                    path="/super-admin"
                    element={
                        <PlatformAdminRoute>
                            <SuperAdminLayout />
                        </PlatformAdminRoute>
                    }
                >
                    <Route index element={<Navigate to="dashboard" replace />} />
                    <Route path="dashboard" element={<Dashboard />} />
                    <Route path="tenants" element={<TenantList />} />
                </Route>
                {/* Platform Admin Login */}
                <Route path="/platform-login" element={<PlatformLogin />} />

                {/* Default redirect */}
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
        </Router>
    );
}

export default App;

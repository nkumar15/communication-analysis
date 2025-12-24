import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { auth } from '../../core/firebase/b2c-config';

// Pages
import LoginPage from './web/pages/LoginPage';
import SignupPage from './web/pages/SignupPage';
import DashboardPage from './web/pages/DashboardPage';
import WorkspacesListPage from './web/pages/WorkspacesListPage';
import WorkspacePage from './web/pages/WorkspacePage';
import UserSettingsPage from './web/pages/UserSettingsPage';
import NotificationsPage from './web/pages/NotificationsPage';
import SubscriptionPage from './web/pages/SubscriptionPage';
import BillingHistoryPage from './web/pages/BillingHistoryPage';

import InvitationAcceptPage from './web/pages/InvitationAcceptPage';

// Protected Route Wrapper
const ProtectedRoute = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = React.useState(null);

    React.useEffect(() => {
        // E2E Test Backdoor: Check for mock JWT
        const e2eToken = sessionStorage.getItem('firebaseToken');
        if (e2eToken && e2eToken.includes('mock_signature')) {
            console.log('🧪 E2E: Bypassing Firebase auth check with mock JWT');
            setIsAuthenticated(true);
            return () => { }; // No cleanup needed
        }

        const unsubscribe = auth.onAuthStateChanged((user) => {
            setIsAuthenticated(!!user);
        });
        return () => unsubscribe();
    }, []);

    if (isAuthenticated === null) {
        return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
            <div style={{ fontSize: '48px' }}>⏳</div>
        </div>;
    }

    return isAuthenticated ? children : <Navigate to="/login" />;
};

const B2CApp = () => {
    return (
        <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/invite/:token" element={<InvitationAcceptPage />} />

            {/* Protected Routes */}
            <Route path="/" element={
                <ProtectedRoute>
                    <DashboardPage />
                </ProtectedRoute>
            } />

            <Route path="/workspaces" element={
                <ProtectedRoute>
                    <WorkspacesListPage />
                </ProtectedRoute>
            } />

            <Route path="/workspace/:workspaceId" element={
                <ProtectedRoute>
                    <WorkspacePage />
                </ProtectedRoute>
            } />

            <Route path="/settings" element={
                <ProtectedRoute>
                    <UserSettingsPage />
                </ProtectedRoute>
            } />

            <Route path="/notifications" element={
                <ProtectedRoute>
                    <NotificationsPage />
                </ProtectedRoute>
            } />

            <Route path="/subscription" element={
                <ProtectedRoute>
                    <SubscriptionPage />
                </ProtectedRoute>
            } />

            <Route path="/billing" element={
                <ProtectedRoute>
                    <BillingHistoryPage />
                </ProtectedRoute>
            } />

            {/* Catch-all redirect */}
            <Route path="*" element={<Navigate to="/" />} />
        </Routes>
    );
};

export default B2CApp;

import { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './modules/b2b/web/pages/LoginPage';
import DashboardPage from './modules/b2b/web/pages/DashboardPage';
import ActivationPage from './modules/b2b/web/pages/ActivationPage';
import InvitationsPage from './modules/b2b/web/pages/InvitationsPage';
import InvitationAcceptPage from './modules/b2b/web/pages/InvitationAcceptPage';
import TeamsPage from './modules/b2b/web/pages/TeamsPage';
import TeamDetailsPage from './modules/b2b/web/pages/TeamDetailsPage';
import AuditLogsPage from './modules/b2b/web/pages/AuditLogsPage';
import AccountSettingsPage from './modules/b2b/web/pages/AccountSettingsPage';
import ProtectedRoute from './core/components/ProtectedRoute';
import firebaseAuthService from './core/firebase/authService';
import { auth } from './core/firebase/config';
import RoleManagementPage from './modules/b2b/web/pages/RoleManagementPage';
import TeamRoleManagementPage from './modules/b2b/web/pages/TeamRoleManagementPage';
import ProjectsPage from './modules/domains/projects/pages/ProjectsPage';
import ProjectDetailPage from './modules/domains/projects/pages/ProjectDetailPage';
import TaskDetailPage from './modules/domains/projects/pages/TaskDetailPage';

import { SubscriptionSettingsPage, InvoicesListPage } from './modules/b2b/billing';
import SurveillanceDashboardPage from './modules/domains/surveillance/pages/SurveillanceDashboardPage';
import AlertsPage from './modules/domains/surveillance/pages/AlertsPage';
import AlertDetailPage from './modules/domains/surveillance/pages/AlertDetailPage';
import CommunicationsPage from './modules/domains/surveillance/pages/CommunicationsPage';
import CaseListPage from './modules/domains/surveillance/pages/CaseListPage';
import CaseDetailPage from './modules/domains/surveillance/pages/CaseDetailPage';
import KnowledgeBasePage from './modules/domains/surveillance/pages/KnowledgeBasePage';
import IngestionPage from './modules/domains/surveillance/pages/IngestionPage';
import RegulatoryLibraryPage from './modules/domains/surveillance/pages/RegulatoryLibraryPage';
import SurveillanceControlsPage from './modules/domains/surveillance/pages/SurveillanceControlsPage';

import apiService from './core/api/b2bClient';
import './styles/main.css';
function JoinRedirect() {
    const searchParams = new URLSearchParams(window.location.search);
    const token = searchParams.get('token');

    if (token) {
        window.location.replace(`/invite/${token}`);
        return null;
    }

    // No token, redirect to login
    window.location.replace('/login');
    return null;
}

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
                // Platform admins should NOT call B2B sync-user
                const tenantId = localStorage.getItem('firebase_tenant_id') || auth.tenantId;
                const isPlatformAdmin = tenantId && (tenantId.includes('platform') || tenantId.includes('system'));

                if (!isPlatformAdmin) {
                    // Regular B2B user - sync with backend
                    try {
                        await apiService.syncUser();
                    } catch (error) {
                        console.error('❌ Error syncing user:', error);
                    }
                } else {
                    console.log('⚠️ Skipping B2B syncUser for platform admin');
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
                <Route path="/join" element={<JoinRedirect />} />

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



                <Route
                    path="/b2b/surveillance/cases/:caseId"
                    element={
                        <ProtectedRoute>
                            <CaseDetailPage />
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/b2b/surveillance/knowledge-base"
                    element={
                        <ProtectedRoute>
                            <KnowledgeBasePage />
                        </ProtectedRoute>
                    }
                />

                {/* New routes */}
                <Route path="/roles" element={<ProtectedRoute><RoleManagementPage /></ProtectedRoute>} />
                <Route path="/team-roles" element={<ProtectedRoute><TeamRoleManagementPage /></ProtectedRoute>} />
                <Route path="/projects" element={<ProtectedRoute><ProjectsPage /></ProtectedRoute>} />
                <Route path="/projects/:projectId" element={<ProtectedRoute><ProjectDetailPage /></ProtectedRoute>} />
                <Route path="/tasks/:taskId" element={<ProtectedRoute><TaskDetailPage /></ProtectedRoute>} />
                <Route path="/b2b/teams" element={<ProtectedRoute><TeamsPage /></ProtectedRoute>} />
                <Route path="/b2b/teams/:teamId" element={<ProtectedRoute><TeamDetailsPage /></ProtectedRoute>} />
                <Route path="/audit-logs" element={<ProtectedRoute><AuditLogsPage /></ProtectedRoute>} />
                <Route path="/settings/account" element={<ProtectedRoute><AccountSettingsPage /></ProtectedRoute>} />

                {/* Surveillance routes */}
                <Route path="/b2b/surveillance" element={<ProtectedRoute><SurveillanceDashboardPage /></ProtectedRoute>} />
                <Route path="/b2b/surveillance/alerts" element={<ProtectedRoute><AlertsPage /></ProtectedRoute>} />
                <Route path="/b2b/surveillance/alerts/:alertId" element={<ProtectedRoute><AlertDetailPage /></ProtectedRoute>} />
                <Route path="/b2b/surveillance/communications" element={<ProtectedRoute><CommunicationsPage /></ProtectedRoute>} />
                <Route path="/b2b/surveillance/cases" element={<ProtectedRoute><CaseListPage /></ProtectedRoute>} />
                <Route path="/b2b/surveillance/ingestion" element={<ProtectedRoute><IngestionPage /></ProtectedRoute>} />
                <Route path="/b2b/surveillance/regulatory" element={<ProtectedRoute><RegulatoryLibraryPage /></ProtectedRoute>} />
                <Route path="/b2b/surveillance/controls" element={<ProtectedRoute><SurveillanceControlsPage /></ProtectedRoute>} />

                {/* Billing routes */}
                <Route path="/billing/subscription" element={<ProtectedRoute><SubscriptionSettingsPage /></ProtectedRoute>} />
                <Route path="/billing/invoices" element={<ProtectedRoute><InvoicesListPage /></ProtectedRoute>} />

                {/* Default redirect */}
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
        </Router>
    );
}

export default App;

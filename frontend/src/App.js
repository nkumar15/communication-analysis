import { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './components/LoginPage';
import Dashboard from './components/Dashboard';
import ActivationPage from './components/ActivationPage';
import InvitationsPage from './components/InvitationsPage';
import InvitationAcceptPage from './components/InvitationAcceptPage';
import ProtectedRoute from './components/ProtectedRoute';
import firebaseAuthService from './services/firebaseAuthService';
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
                // User already signed in from previous session
                try {
                    await apiService.syncUser();
                } catch (error) {
                    console.error('❌ Error syncing user:', error);
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
                            <Dashboard />
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

                {/* Default redirect */}
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
        </Router>
    );
}

export default App;

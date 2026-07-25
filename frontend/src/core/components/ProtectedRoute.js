import { useState, useEffect } from 'react';
import firebaseAuthService from '../firebase/authService';

function ProtectedRoute({ children }) {
    const [isAuthenticated, setIsAuthenticated] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // E2E Test Backdoor: Check for mock JWT token
        const e2eToken = sessionStorage.getItem('firebaseToken');
        if (e2eToken && e2eToken.includes('mock_signature')) {
            console.log('🧪 E2E: Bypassing Firebase auth check for test token');
            setIsAuthenticated(true);
            setLoading(false);
            return;
        }

        // Listen for Firebase auth state changes
        const unsubscribe = firebaseAuthService.onAuthStateChanged((user) => {
            setIsAuthenticated(!!user);
            setLoading(false);
        });

        // Cleanup subscription
        return () => unsubscribe();
    }, []);

    // Still loading
    if (loading || isAuthenticated === null) {
        return (
            <div className="loading-container">
                <div className="spinner large"></div>
            </div>
        );
    }

    // Not authenticated, redirect to login
    if (!isAuthenticated) {
        window.location.href = '/login';
        return null;
    }

    // Authenticated, render children
    return children;
}

export default ProtectedRoute;

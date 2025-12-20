import { useState, useEffect } from 'react';
import firebaseAuthService from '../firebase/authService';

function ProtectedRoute({ children }) {
    const [isAuthenticated, setIsAuthenticated] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
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

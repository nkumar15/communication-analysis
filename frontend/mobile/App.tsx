import React, { useEffect, useState } from 'react';
import { View, Text, Linking } from 'react-native';
import LoginScreen from './LoginScreen';
import ActivationScreen from './ActivationScreen';

/**
 * Main App Component
 * Routes between Login and Activation screens based on context
 */
export default function App() {
    const [currentScreen, setCurrentScreen] = useState('login'); // 'login' or 'activation'
    const [activationToken, setActivationToken] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    useEffect(() => {
        // Check for deep link on app launch

        const handleDeepLink = ({ url }) => {
            console.log('🔗 Deep link received:', url);
            if (url && url.includes('activate')) {
                let token = null;

                // Try path format: /activate/{token}
                const pathMatch = url.match(/\/activate\/([^?&#]+)/);
                if (pathMatch && pathMatch[1]) {
                    token = pathMatch[1];
                }

                // Try query format: ?token={token}
                if (!token) {
                    const queryMatch = url.match(/[?&]token=([^&#]*)/);
                    if (queryMatch && queryMatch[1]) {
                        token = queryMatch[1];
                    }
                }

                if (token) {
                    console.log('🎫 Activation token extracted:', token);
                    setActivationToken(token);
                    setCurrentScreen('activation');
                } else {
                    console.log('⚠️ No token found in URL');
                }
            }
        };

        // Handle initial URL (app was closed)
        Linking.getInitialURL().then((url) => {
            if (url) handleDeepLink({ url });
        });

        // Handle URL while app is running
        const subscription = Linking.addEventListener('url', handleDeepLink);
        return () => subscription.remove();
    }, []);

    const handleLoginSuccess = (userData) => {
        console.log('✅ Login successful, user data:', userData);
        setIsAuthenticated(true);
        // TODO: Navigate to Dashboard/Home screen
        // For now, just show success
    };

    const handleActivationSuccess = (userData) => {
        console.log('✅ Activation successful, user data:', userData);
        setIsAuthenticated(true);
        // TODO: Navigate to Dashboard/Home screen
    };

    // Render appropriate screen
    if (isAuthenticated) {
        // TODO: Replace with actual Dashboard/Home screen
        return (
            <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
                <Text style={{ fontSize: 24 }}>Welcome! (Dashboard Coming Soon)</Text>
            </View>
        );
    }

    if (currentScreen === 'activation') {
        return (
            <ActivationScreen
                token={activationToken}
                onSuccess={handleActivationSuccess}
            />
        );
    }

    return <LoginScreen onLoginSuccess={handleLoginSuccess} />;
}

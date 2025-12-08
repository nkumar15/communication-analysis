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
                // Extract token from URL
                const regex = /[?&]token=([^&#]*)/;
                const match = regex.exec(url);
                if (match && match[1]) {
                    setActivationToken(match[1]);
                    setCurrentScreen('activation');
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
    if (currentScreen === 'activation') {
        return (
            <ActivationScreen
                token={activationToken}
                onSuccess={handleActivationSuccess}
            />
        );
    }

    if (isAuthenticated) {
        // TODO: Replace with actual Dashboard/Home screen
        return (
            <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
                <Text style={{ fontSize: 24 }}>Welcome! (Dashboard Coming Soon)</Text>
            </View>
        );
    }

    return <LoginScreen onLoginSuccess={handleLoginSuccess} />;
}

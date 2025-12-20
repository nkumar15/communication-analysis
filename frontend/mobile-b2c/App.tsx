import React, { useEffect, useState } from 'react';
import { View, Text, Linking } from 'react-native';
import LoginScreen from './LoginScreen';
import SignupScreen from './SignupScreen';
import DashboardScreen from './DashboardScreen';
import auth from '@react-native-firebase/auth';

/**
 * Main App Component (B2C)
 * Routes: Login <-> Signup | Dashboard
 */
export default function App() {
    const [currentScreen, setCurrentScreen] = useState('login'); // 'login', 'signup'
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [userData, setUserData] = useState(null);
    const [loading, setLoading] = useState(true);

    // Listen for Firebase Auth state changes
    useEffect(() => {
        const subscriber = auth().onAuthStateChanged(async (user) => {
            if (user) {
                // Verified check
                if (user.emailVerified) {
                    console.log('✅ User authenticated & verified:', user.email);
                    // In real app, we might fetch full profile here if not in user object
                    // For now, construct basic user data from FirebaseUser
                    setUserData({
                        display_name: user.displayName,
                        email: user.email,
                        avatar_url: user.photoURL,
                        // id would come from token claims or backend sync
                    });
                    setIsAuthenticated(true);
                } else {
                    console.log('⚠️ User authenticated but NOT verified:', user.email);
                    setIsAuthenticated(false);
                }
            } else {
                setIsAuthenticated(false);
                setUserData(null);
            }
            setLoading(false);
        });
        return subscriber; // unsubscribe on unmount
    }, []);

    const handleLoginSuccess = (data) => {
        console.log('✅ Login successful, user data:', data);
        setUserData(data);
        setIsAuthenticated(true);
    };

    const handleLogout = async () => {
        try {
            await auth().signOut();
            setIsAuthenticated(false);
            setCurrentScreen('login');
        } catch (error) {
            console.error('Logout error:', error);
        }
    };

    // Mock Navigation Object
    const navigation = {
        navigate: (screen) => {
            console.log('Navigating to:', screen);
            if (screen === 'Login') setCurrentScreen('login');
            if (screen === 'Signup') setCurrentScreen('signup');
        }
    };

    if (loading) {
        return <View><Text>Loading...</Text></View>; // Replace with proper splash
    }

    // Authenticated -> Dashboard
    if (isAuthenticated) {
        return (
            <DashboardScreen
                userData={userData}
                onLogout={handleLogout}
            />
        );
    }

    // Unauthenticated -> Login/Signup
    if (currentScreen === 'signup') {
        return <SignupScreen navigation={navigation} />;
    }

    return <LoginScreen onLoginSuccess={handleLoginSuccess} navigation={navigation} />;
}

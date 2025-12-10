import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, Linking, ActivityIndicator, TouchableOpacity, Alert } from 'react-native';
import apiService from '../../../core/api/b2bClient';
import firebaseAuthService from '../../../core/firebase/authService';

/**
 * Mobile Activation Screen
 * Requirements: ONB-03 (Mobile Flow)
 * 
 * Flow:
 * 1. Catch Deep Link with token
 * 2. Validate Token (API)
 * 3. Show Welcome Screen
 * 4. User clicks "Get Started" -> SSO Login
 * 5. Sync User -> Complete Activation (API)
 * 6. Navigate to Home
 */
const ActivationScreen = ({ navigation }) => {
    const [status, setStatus] = useState('idle'); // idle, validating, welcome, processing, success, error
    const [message, setMessage] = useState('Waiting for activation link...');
    const [tenantInfo, setTenantInfo] = useState(null);
    const [token, setToken] = useState(null);

    useEffect(() => {
        // 1. Handle Deep Link
        const handleDeepLink = ({ url }) => {
            console.log("🔗 Deep link received:", url);
            if (url && url.includes('activate')) {
                // Extract token parameter manually or use a library query parser
                const regex = /[?&]token=([^&#]*)/;
                const match = regex.exec(url);
                if (match && match[1]) {
                    const extractedToken = match[1];
                    setToken(extractedToken);
                    validateToken(extractedToken);
                } else {
                    setStatus('error');
                    setMessage('Invalid link format: Missing token');
                }
            }
        };

        Linking.getInitialURL().then((url) => {
            if (url) handleDeepLink({ url });
        });

        const subscription = Linking.addEventListener('url', handleDeepLink);
        return () => subscription.remove();
    }, []);

    const validateToken = async (activationToken) => {
        try {
            setStatus('validating');
            setMessage('Validating activation token...');
            const data = await apiService.validateActivationToken(activationToken);
            setTenantInfo(data);
            setStatus('welcome');
        } catch (err) {
            console.error("Validation failed:", err);
            setStatus('error');
            setMessage(err.message || 'Invalid or expired activation link');
        }
    };

    const handleStartSSO = async () => {
        if (!tenantInfo || !token) return;

        try {
            setStatus('processing');
            setMessage('Setting up your session...');

            // 1. Get Tenant Info (already fetched, but ensuring we have provider ID)
            const config = await apiService.getActivationTenantInfo(tenantInfo.tenant_id);
            console.log('🔐 SSO Config:', config);
            const { oidc_provider_id, firebase_tenant_id } = config;

            if (!oidc_provider_id) {
                throw new Error('No OIDC provider configured for this tenant');
            }

            // 2. Get OIDC Config (Issuer, Client ID)
            // Using raw fetch since not in apiService yet (similar to LoginScreen)
            const API_URL = 'http://10.0.2.2:8000'; // Standard Android Emulator localhost alias
            const configResponse = await fetch(`${API_URL}/api/b2b/auth/oidc-config/${oidc_provider_id}`);

            if (!configResponse.ok) {
                throw new Error('Failed to load OIDC configuration');
            }
            const oidcConfig = await configResponse.json();
            console.log('✅ OIDC config retrieved:', oidcConfig.issuer);

            // 3. Perform Native OAuth Login (System Browser)
            // Import oidcAuthService dynamically or ensure it's imported at top
            const { idToken } = await require('../../../core/firebase/oidcAuthService.native').default.signInWithOIDC({
                issuer: oidcConfig.issuer,
                clientId: oidcConfig.client_id,
                scopes: oidcConfig.scopes,
                email: tenantInfo.admin_email, // Login hint
            });
            console.log('✅ OAuth successful, exchanging token...');

            // 4. Exchange OIDC token for Firebase custom token
            const tokenResponse = await fetch(`${API_URL}/api/b2b/auth/mobile-login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    oidc_id_token: idToken,
                    email: tenantInfo.admin_email, // Must match invitation email
                    firebase_tenant_id,
                }),
            });

            if (!tokenResponse.ok) {
                const error = await tokenResponse.json();
                throw new Error(error.detail || 'Authentication failed');
            }

            const { firebase_custom_token } = await tokenResponse.json();
            console.log('✅ Received Firebase custom token');

            // 5. Sign in to Firebase (Native SDK)
            // Explicitly set tenant ID first
            await firebaseAuthService.signInWithCustomToken(firebase_custom_token, firebase_tenant_id);
            console.log('✅ Firebase authentication successful');

            // 6. Sync User
            setMessage('Finalizing account setup...');
            await apiService.syncUser();

            // 7. Complete Activation
            await apiService.completeActivation(token);

            setStatus('success');
            setMessage('Account Activated! Redirecting...');

            // 8. Navigation
            setTimeout(() => {
                // Assuming navigation prop exists and 'Home' is the target
                if (navigation) navigation.navigate('Home');
            }, 2000);

        } catch (err) {
            console.error("Activation flow failed:", err);
            setStatus('error');
            setMessage(err.message || 'Activation process failed');
            Alert.alert("Activation Error", err.message);
        }
    };

    return (
        <View style={styles.container}>
            {/* Header / Brand */}
            <View style={styles.header}>
                <Text style={styles.brandTitle}>Enterprise SSO</Text>
            </View>

            <View style={styles.content}>
                <Text style={styles.title}>Tenant Activation</Text>

                {status === 'idle' && (
                    <Text style={styles.text}>{message}</Text>
                )}

                {(status === 'validating' || status === 'processing') && (
                    <View style={styles.center}>
                        <ActivityIndicator size="large" color="#4F46E5" />
                        <Text style={styles.loadingText}>{message}</Text>
                    </View>
                )}

                {status === 'error' && (
                    <View style={styles.errorContainer}>
                        <Text style={styles.errorTitle}>❌ Error</Text>
                        <Text style={styles.errorText}>{message}</Text>
                    </View>
                )}

                {status === 'welcome' && tenantInfo && (
                    <View style={styles.card}>
                        <Text style={styles.welcomeTitle}>Welcome to {tenantInfo.tenant_name}!</Text>
                        <Text style={styles.welcomeText}>
                            You have been invited to manage this organization.
                            Please tap below to sign in and activate your account.
                        </Text>
                        <View style={styles.infoBox}>
                            <Text style={styles.infoLabel}>Admin Email:</Text>
                            <Text style={styles.infoValue}>{tenantInfo.admin_email}</Text>
                        </View>

                        <TouchableOpacity style={styles.button} onPress={handleStartSSO}>
                            <Text style={styles.buttonText}>Activate & Login</Text>
                        </TouchableOpacity>
                    </View>
                )}

                {status === 'success' && (
                    <View style={styles.successContainer}>
                        <Text style={styles.successTitle}>✅ Success!</Text>
                        <Text style={styles.successText}>Your account is now active.</Text>
                    </View>
                )}
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F9FAFB', // Design Token: Background
    },
    header: {
        paddingTop: 60,
        paddingBottom: 20,
        alignItems: 'center',
        backgroundColor: 'white',
        borderBottomWidth: 1,
        borderBottomColor: '#E5E7EB',
    },
    brandTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: '#4F46E5',
    },
    content: {
        flex: 1,
        padding: 24,
        justifyContent: 'center',
        alignItems: 'center',
    },
    title: {
        fontSize: 24, // Design Token: Heading 1 (Mobile)
        fontWeight: '700',
        color: '#111827', // Design Token: Text Primary
        marginBottom: 24,
    },
    text: {
        fontSize: 16, // Design Token: Body Large
        color: '#6B7280', // Design Token: Text Secondary
        textAlign: 'center',
    },
    center: {
        alignItems: 'center',
        gap: 16,
    },
    loadingText: {
        marginTop: 16,
        fontSize: 16,
        color: '#4F46E5',
    },
    card: {
        backgroundColor: 'white',
        borderRadius: 12,
        padding: 24,
        width: '100%',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    welcomeTitle: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#111827',
        marginBottom: 12,
        textAlign: 'center',
    },
    welcomeText: {
        fontSize: 16,
        color: '#4B5563',
        marginBottom: 24,
        textAlign: 'center',
        lineHeight: 24,
    },
    infoBox: {
        backgroundColor: '#F3F4F6',
        padding: 16,
        borderRadius: 8,
        marginBottom: 24,
    },
    infoLabel: {
        fontSize: 14,
        color: '#6B7280',
        marginBottom: 4,
    },
    infoValue: {
        fontSize: 16,
        fontWeight: '500',
        color: '#111827',
    },
    button: {
        backgroundColor: '#4F46E5',
        paddingVertical: 14,
        borderRadius: 8,
        alignItems: 'center',
    },
    buttonText: {
        color: 'white',
        fontSize: 16,
        fontWeight: '600',
    },
    errorContainer: {
        alignItems: 'center',
        padding: 20,
        backgroundColor: '#FEF2F2',
        borderRadius: 8,
        width: '100%',
    },
    errorTitle: {
        color: '#DC2626',
        fontSize: 18,
        fontWeight: 'bold',
        marginBottom: 8,
    },
    errorText: {
        color: '#B91C1C',
        textAlign: 'center',
    },
    successContainer: {
        alignItems: 'center',
        padding: 20,
        backgroundColor: '#ECFDF5',
        borderRadius: 8,
        width: '100%',
    },
    successTitle: {
        color: '#059669',
        fontSize: 18,
        fontWeight: 'bold',
        marginBottom: 8,
    },
    successText: {
        color: '#047857',
        textAlign: 'center',
    }
});

export default ActivationScreen;

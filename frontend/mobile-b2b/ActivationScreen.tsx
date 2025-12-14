import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity, Alert } from 'react-native';
import apiService from '../src/core/api/b2bClient';
import firebaseAuthService from '../src/core/firebase/authService';
import oidcAuthService from '../src/core/firebase/oidcAuthService.native';

/**
 * Mobile Activation Screen
 * Requirements: ONB-03 (Mobile Flow)
 * 
 * Flow:
 * 1. Receive token as prop
 * 2. Validate Token (API)
 * 3. Show Welcome Screen
 * 4. User clicks "Activate" -> SSO Login
 * 5. Sync User -> Complete Activation (API)
 * 6. Call onSuccess callback
 */
export default function ActivationScreen({ token: initialToken, onSuccess }) {
    const [status, setStatus] = useState('idle'); // idle, validating, welcome, processing, success, error
    const [message, setMessage] = useState('Waiting for activation link...');
    const [tenantInfo, setTenantInfo] = useState(null);
    const [token, setToken] = useState(initialToken);


    useEffect(() => {
        // Validate token when it's provided
        if (token) {
            validateToken(token);
        }
    }, [token]);

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

            // 1. Get Tenant Info with Provider ID
            const config = await apiService.getActivationTenantInfo(tenantInfo.tenant_id);
            console.log('🔐 Tenant Config:', config);
            const { oidc_provider_id, mobile_oidc_provider_id, firebase_tenant_id } = config;
            const providerId = mobile_oidc_provider_id || oidc_provider_id;

            if (!providerId) {
                throw new Error('No OIDC provider configured for this tenant');
            }

            // 2. Get OIDC Config (Issuer, Client ID)
            // Using localhost alias for Android Emulator
            const API_URL = 'http://10.0.2.2:8000';
            const configResponse = await fetch(`${API_URL}/api/b2b/auth/oidc-config/${providerId}`);

            if (!configResponse.ok) {
                throw new Error('Failed to load OIDC configuration');
            }
            const oidcConfig = await configResponse.json();
            console.log('✅ OIDC config retrieved:', oidcConfig.issuer);

            // 3. Perform Native OAuth Login (System Browser)
            setMessage('Opening login page...');

            const { idToken, nonce } = await oidcAuthService.signInWithOIDC({
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
                    email: tenantInfo.admin_email,
                    firebase_tenant_id,
                    provider_id: providerId,
                    nonce: nonce,
                }),
            });

            if (!tokenResponse.ok) {
                const error = await tokenResponse.json();
                let errorMessage = 'Authentication failed';

                if (typeof error.detail === 'string') {
                    errorMessage = error.detail;
                } else if (Array.isArray(error.detail)) {
                    // Pydantic validation errors
                    errorMessage = error.detail.map(e => `${e.loc.join('.')}: ${e.msg}`).join('\n');
                } else {
                    errorMessage = JSON.stringify(error);
                }

                throw new Error(errorMessage);
            }

            const { firebase_custom_token } = await tokenResponse.json();
            console.log('✅ Received Firebase custom token');

            // 5. Sign in to Firebase (Native SDK) with Custom Token
            // Explicitly set tenant ID first
            await firebaseAuthService.signInWithCustomToken(firebase_custom_token, firebase_tenant_id);
            console.log('✅ Firebase Authentication Success');

            // 6. Sync User with Backend
            setMessage('Creating your account...');
            await apiService.syncUser();

            // 7. Complete Activation
            setMessage('Activating tenant...');
            await apiService.completeActivation(token);

            setStatus('success');
            setMessage('Account Activated! Redirecting...');

            // 8. Success callback
            if (onSuccess) {
                onSuccess({ status: 'activated' });
            }

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

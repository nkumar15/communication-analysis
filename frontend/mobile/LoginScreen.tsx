import React, { useState } from 'react';
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    StyleSheet,
    ActivityIndicator,
    Alert,
    KeyboardAvoidingView,
    Platform,
} from 'react-native';
import apiService from '../src/core/api/b2bClient';
import firebaseAuthService from '../src/core/firebase/authService';

/**
 * Login Screen Component
 * Matches web flow: Email → Resolve Tenant → OIDC Login
 */
export default function LoginScreen({ onLoginSuccess }) {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState('');

    const handleLogin = async () => {
        if (!email || !email.includes('@')) {
            Alert.alert('Invalid Email', 'Please enter a valid email address');
            return;
        }

        try {
            setLoading(true);
            setStatus('Looking up your organization...');

            // 1. Resolve tenant from email
            const response = await fetch('http://10.0.2.2:8000/api/b2b/auth/resolve-tenant', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Tenant not found');
            }

            const { firebase_tenant_id, oidc_provider_id } = await response.json();
            console.log('✅ Tenant resolved:', firebase_tenant_id);

            // 2. Set tenant context
            setStatus('Initializing authentication...');
            await firebaseAuthService.setTenantId(firebase_tenant_id);

            // 3. Trigger OIDC login (WebView)
            setStatus('Opening login page...');
            const userCredential = await firebaseAuthService.signInWithOIDC(
                oidc_provider_id,
                email
            );

            console.log('✅ Login successful:', userCredential.user.email);

            // 5. Sync user with backend
            setStatus('Syncing account...');
            const userData = await apiService.syncUser();

            setStatus('Success!');

            // 6. Navigate to home/dashboard
            if (onLoginSuccess) {
                onLoginSuccess(userData);
            }

        } catch (error) {
            console.error('❌ Login failed:', error);
            setLoading(false);
            setStatus('');
            Alert.alert('Login Failed', error.message || 'Unable to sign in');
        }
    };

    return (
        <KeyboardAvoidingView
            style={styles.container}
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
            <View style={styles.content}>
                {/* Header */}
                <Text style={styles.title}>Enterprise SSO</Text>
                <Text style={styles.subtitle}>Sign in to your account</Text>

                {/* Email Input */}
                <TextInput
                    style={styles.input}
                    placeholder="Email address"
                    placeholderTextColor="#999"
                    value={email}
                    onChangeText={setEmail}
                    keyboardType="email-address"
                    autoCapitalize="none"
                    autoCorrect={false}
                    editable={!loading}
                />

                {/* Status Message */}
                {status ? (
                    <View style={styles.statusContainer}>
                        <ActivityIndicator size="small" color="#6366F1" />
                        <Text style={styles.statusText}>{status}</Text>
                    </View>
                ) : null}

                {/* Login Button */}
                <TouchableOpacity
                    style={[styles.button, loading && styles.buttonDisabled]}
                    onPress={handleLogin}
                    disabled={loading}
                >
                    {loading ? (
                        <ActivityIndicator color="#FFF" />
                    ) : (
                        <Text style={styles.buttonText}>Continue</Text>
                    )}
                </TouchableOpacity>

                {/* Footer */}
                <Text style={styles.footer}>
                    Your organization uses single sign-on for secure access
                </Text>
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F9FAFB',
    },
    content: {
        flex: 1,
        justifyContent: 'center',
        paddingHorizontal: 24,
    },
    title: {
        fontSize: 32,
        fontWeight: 'bold',
        color: '#111827',
        textAlign: 'center',
        marginBottom: 8,
    },
    subtitle: {
        fontSize: 16,
        color: '#6B7280',
        textAlign: 'center',
        marginBottom: 48,
    },
    input: {
        backgroundColor: '#FFF',
        borderWidth: 1,
        borderColor: '#E5E7EB',
        borderRadius: 8,
        paddingHorizontal: 16,
        paddingVertical: 14,
        fontSize: 16,
        color: '#111827',
        marginBottom: 16,
    },
    statusContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 16,
        paddingVertical: 12,
        backgroundColor: '#EEF2FF',
        borderRadius: 8,
    },
    statusText: {
        marginLeft: 8,
        fontSize: 14,
        color: '#6366F1',
    },
    button: {
        backgroundColor: '#6366F1',
        paddingVertical: 16,
        borderRadius: 8,
        alignItems: 'center',
        marginBottom: 24,
    },
    buttonDisabled: {
        opacity: 0.6,
    },
    buttonText: {
        color: '#FFF',
        fontSize: 16,
        fontWeight: '600',
    },
    footer: {
        fontSize: 14,
        color: '#9CA3AF',
        textAlign: 'center',
        lineHeight: 20,
    },
});

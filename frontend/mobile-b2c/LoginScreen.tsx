import React, { useState, useEffect } from 'react';
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
import auth from '@react-native-firebase/auth';
import Config from 'react-native-config';

import { GoogleSignin } from '@react-native-google-signin/google-signin';

/**
 * Login Screen Component (B2C)
 * Standard Email/Password flow + Google Sign-In
 */
export default function LoginScreen({ onLoginSuccess, navigation }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState('');

    useEffect(() => {
        GoogleSignin.configure({
            webClientId: Config.REACT_APP_GOOGLE_WEB_CLIENT_ID, // From .env
        });
    }, []);

    const handleGoogleLogin = async () => {
        try {
            setLoading(true);
            setStatus('Connecting to Google...');
            console.log('🔹 Step 1: Starting Google Sign-In...');
            console.log('🔹 Web Client ID configured:', Config.REACT_APP_GOOGLE_WEB_CLIENT_ID);

            console.log('🔹 Step 2: Checking Play Services...');
            await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
            console.log('✅ Play Services available');

            console.log('🔹 Step 3: Requesting User Sign-In...');
            const response = await GoogleSignin.signIn();

            // Log the ENTIRE response structure for debugging
            console.log('🔹 Step 4: Raw Response Received');
            console.log('🔹 Response Type:', typeof response);
            console.log('🔹 Response Keys:', Object.keys(response || {}));
            console.log('🔹 Full Response:', JSON.stringify(response, null, 2));

            // Try multiple paths to extract idToken
            const idToken = response?.idToken
                || response?.data?.idToken
                || response?.user?.idToken
                || response?.serverAuthCode; // Sometimes this is returned instead

            console.log('🔹 Step 5: ID Token extraction');
            console.log('🔹 response.idToken:', response?.idToken);
            console.log('🔹 response.data?.idToken:', response?.data?.idToken);
            console.log('🔹 response.user?.idToken:', response?.user?.idToken);
            console.log('🔹 response.serverAuthCode:', response?.serverAuthCode);
            console.log('🔹 Extracted idToken:', idToken ? 'PRESENT' : 'MISSING');

            if (!idToken) {
                console.error('❌ Missing ID Token in response');
                console.error('❌ Available fields:', Object.keys(response || {}));
                throw new Error('Google Sign-In failed to return ID Token. Check Web Client ID configuration.');
            }

            console.log('🔹 Step 6: Creating Firebase Credential...');
            const googleCredential = auth.GoogleAuthProvider.credential(idToken);
            console.log('✅ Credential created');

            setStatus('Signing in...');
            console.log('🔹 Step 7: Signing in with Firebase...');
            const userCredential = await auth().signInWithCredential(googleCredential);
            const user = userCredential.user;
            console.log('✅ Firebase sign-in successful. User:', user.email);

            // Sync with backend
            setStatus('Syncing account...');
            console.log('🔹 Step 8: Syncing with backend...');
            const firebaseIdToken = await user.getIdToken(true);
            console.log('✅ Got Firebase ID Token');

            await syncWithBackend(firebaseIdToken, onLoginSuccess);
            console.log('✅ Backend sync complete');

        } catch (error) {
            console.error('❌ Error occurred at some step');
            console.error('❌ Error Type:', typeof error);
            console.error('❌ Error Code:', error?.code);
            console.error('❌ Error Message:', error?.message);
            console.error('❌ Error Stack:', error?.stack);
            console.error('❌ Full Error Object:', JSON.stringify(error, Object.getOwnPropertyNames(error), 2));

            setLoading(false);
            setStatus('');

            const errorCode = error?.code || 'UNKNOWN';
            const errorMessage = error?.message || 'An unknown error occurred';

            if (errorCode !== 'SIGN_IN_CANCELLED') {
                Alert.alert('Google Sign-In Failed', `${errorMessage}\n\nError Code: ${errorCode}\n\nCheck Metro logs for details.`);
            }
        }
    };

    const syncWithBackend = async (idToken, callback) => {
        const apiUrl = Config.REACT_APP_API_URL || 'http://10.0.2.2:8080';
        const response = await fetch(`${apiUrl}/api/b2c/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_token: idToken }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Backend sync failed');
        }

        const userData = await response.json();
        setStatus('Success!');
        if (callback) callback(userData);
    };

    const handleLogin = async () => {
        if (!email || !password) {
            Alert.alert('Error', 'Please enter email and password');
            return;
        }

        try {
            setLoading(true);
            setStatus('Signing in...');

            // 1. Firebase Login
            const userCredential = await auth().signInWithEmailAndPassword(email, password);
            const user = userCredential.user;

            // 2. Check Verification
            if (!user.emailVerified) {
                setLoading(false);
                setStatus('');
                Alert.alert(
                    'Email Not Verified',
                    'Please verify your email address to continue.',
                    [
                        {
                            text: 'Resend Email',
                            onPress: async () => {
                                await user.sendEmailVerification();
                                Alert.alert('Sent', 'Verification email resent.');
                            }
                        },
                        { text: 'OK' }
                    ]
                );
                await auth().signOut();
                return;
            }

            // 3. Force Refresh Token & Sync
            setStatus('Syncing account...');
            const idToken = await user.getIdToken(true);
            await syncWithBackend(idToken, onLoginSuccess);

        } catch (error) {
            console.error('❌ Login failed:', error);
            setLoading(false);
            setStatus('');
            let msg = error.message;
            if (error.code === 'auth/invalid-credential') msg = 'Invalid email or password';
            Alert.alert('Login Failed', msg);
        }
    };

    return (
        <KeyboardAvoidingView
            style={styles.container}
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
            <View style={styles.content}>
                {/* Header */}
                <View style={styles.header}>
                    <Text style={styles.icon}>🚀</Text>
                    <Text style={styles.title}>Welcome Back</Text>
                    <Text style={styles.subtitle}>Sign in to your personal workspace</Text>
                </View>

                {/* Email Input */}
                <TextInput
                    style={styles.input}
                    placeholder="Email address"
                    placeholderTextColor="#9CA3AF"
                    value={email}
                    onChangeText={setEmail}
                    keyboardType="email-address"
                    autoCapitalize="none"
                    autoCorrect={false}
                    editable={!loading}
                />

                {/* Password Input */}
                <TextInput
                    style={styles.input}
                    placeholder="Password"
                    placeholderTextColor="#9CA3AF"
                    value={password}
                    onChangeText={setPassword}
                    secureTextEntry
                    editable={!loading}
                />

                {/* Status Message */}
                {status ? (
                    <View style={styles.statusContainer}>
                        <ActivityIndicator size="small" color="#4F46E5" />
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
                        <Text style={styles.buttonText}>Sign In</Text>
                    )}
                </TouchableOpacity>

                {/* Google Sign In */}
                <TouchableOpacity
                    style={[styles.googleButton, loading && styles.buttonDisabled]}
                    onPress={handleGoogleLogin}
                    disabled={loading}
                >
                    <Text style={styles.googleButtonText}>Sign in with Google</Text>
                </TouchableOpacity>

                {/* Footer */}
                <View style={styles.footer}>
                    <Text style={styles.footerText}>Don't have an account? </Text>
                    <TouchableOpacity onPress={() => navigation.navigate('Signup')}>
                        <Text style={styles.link}>Sign up</Text>
                    </TouchableOpacity>
                </View>
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
    header: {
        alignItems: 'center',
        marginBottom: 48,
    },
    icon: {
        fontSize: 48,
        marginBottom: 16,
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
        color: '#4F46E5',
    },
    button: {
        backgroundColor: '#4F46E5',
        paddingVertical: 16,
        borderRadius: 8,
        alignItems: 'center',
        marginBottom: 16, // Reduced margin
        shadowColor: '#4F46E5',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.2,
        shadowRadius: 8,
        elevation: 4,
    },
    googleButton: {
        backgroundColor: '#FFF',
        paddingVertical: 16,
        borderRadius: 8,
        alignItems: 'center',
        marginBottom: 24,
        borderWidth: 1,
        borderColor: '#E5E7EB',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 2,
        elevation: 1,
    },
    googleButtonText: {
        color: '#1F2937',
        fontSize: 16,
        fontWeight: '600',
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
        flexDirection: 'row',
        justifyContent: 'center',
    },
    footerText: {
        fontSize: 14,
        color: '#6B7280',
    },
    link: {
        fontSize: 14,
        color: '#4F46E5',
        fontWeight: '600',
    },
});


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
import { GoogleSignin } from '@react-native-google-signin/google-signin';
import Config from 'react-native-config';

export default function SignupScreen({ navigation }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState('');

    useEffect(() => {
        GoogleSignin.configure({
            webClientId: Config.REACT_APP_GOOGLE_WEB_CLIENT_ID,
        });
    }, []);

    const handleGoogleSignup = async () => {
        try {
            setLoading(true);
            setStatus('Connecting to Google...');

            await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
            const { idToken } = await GoogleSignin.signIn();
            const googleCredential = auth.GoogleAuthProvider.credential(idToken);

            setStatus('Creating account...');
            const userCredential = await auth().signInWithCredential(googleCredential);
            const user = userCredential.user;

            // Sync with backend
            setStatus('Syncing account...');
            const firebaseIdToken = await user.getIdToken(true);
            await syncWithBackend(firebaseIdToken);

        } catch (error) {
            console.error('Google Sign-Up Error:', error);
            setLoading(false);
            setStatus('');
            if (error.code !== 'SIGN_IN_CANCELLED') {
                Alert.alert('Google Sign-Up Failed', error.message);
            }
        }
    };

    const syncWithBackend = async (idToken) => {
        const apiUrl = Config.REACT_APP_API_URL || 'http://10.0.2.2:8080';
        try {
            const response = await fetch(`${apiUrl}/api/b2c/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id_token: idToken }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Backend sync failed');
            }

            // Navigate to Dashboard (handled by Auth State Listener in App.tsx)
            // But we can show success message
            Alert.alert('Welcome!', 'Your account has been created successfully.');
        } catch (err) {
            console.error('Backend sync error:', err);
            // Even if backend sync fails specific API, auth state listener might pick it up.
            // But let's alert.
            Alert.alert('Sync Error', 'Account created but backend sync failed. Please check connection.');
        }
    };

    const handleSignup = async () => {
        if (!email || !password) {
            Alert.alert('Error', 'Please fill in all fields');
            return;
        }

        try {
            setLoading(true);
            // Create user
            const userCredential = await auth().createUserWithEmailAndPassword(email, password);
            const user = userCredential.user;

            // Send verification email
            await user.sendEmailVerification();

            setLoading(false);

            Alert.alert(
                'Account Created',
                'We have sent a verification email to your address. Please verify it before logging in.',
                [
                    { text: 'Go to Login', onPress: () => navigation.navigate('Login') }
                ]
            );

        } catch (error) {
            setLoading(false);
            let errorMessage = 'Something went wrong';
            if (error.code === 'auth/email-already-in-use') {
                errorMessage = 'That email address is already in use!';
            } else if (error.code === 'auth/invalid-email') {
                errorMessage = 'That email address is invalid!';
            } else if (error.code === 'auth/weak-password') {
                errorMessage = 'Password should be at least 6 characters';
            }
            Alert.alert('Signup Failed', errorMessage);
        }
    };

    return (
        <KeyboardAvoidingView
            style={styles.container}
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
            <View style={styles.content}>
                <View style={styles.header}>
                    <Text style={styles.icon}>✨</Text>
                    <Text style={styles.title}>Create Account</Text>
                    <Text style={styles.subtitle}>Start your journey today</Text>
                </View>

                <TextInput
                    style={styles.input}
                    placeholder="Email address"
                    placeholderTextColor="#9CA3AF"
                    value={email}
                    onChangeText={setEmail}
                    keyboardType="email-address"
                    autoCapitalize="none"
                />

                <TextInput
                    style={styles.input}
                    placeholder="Password"
                    placeholderTextColor="#9CA3AF"
                    value={password}
                    onChangeText={setPassword}
                    secureTextEntry
                />

                {/* Status Message */}
                {status ? (
                    <View style={styles.statusContainer}>
                        <ActivityIndicator size="small" color="#4F46E5" />
                        <Text style={styles.statusText}>{status}</Text>
                    </View>
                ) : null}

                <TouchableOpacity
                    style={[styles.button, loading && styles.buttonDisabled]}
                    onPress={handleSignup}
                    disabled={loading}
                >
                    {loading ? (
                        <ActivityIndicator color="#FFF" />
                    ) : (
                        <Text style={styles.buttonText}>Sign Up</Text>
                    )}
                </TouchableOpacity>

                {/* Google Sign Up */}
                <TouchableOpacity
                    style={[styles.googleButton, loading && styles.buttonDisabled]}
                    onPress={handleGoogleSignup}
                    disabled={loading}
                >
                    <Text style={styles.googleButtonText}>Sign up with Google</Text>
                </TouchableOpacity>

                <View style={styles.footer}>
                    <Text style={styles.footerText}>Already have an account? </Text>
                    <TouchableOpacity onPress={() => navigation.navigate('Login')}>
                        <Text style={styles.link}>Sign in</Text>
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
        fontSize: 30,
        fontWeight: 'bold',
        color: '#111827',
        marginBottom: 8,
    },
    subtitle: {
        fontSize: 16,
        color: '#6B7280',
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
        backgroundColor: '#4F46E5', // Primary Blue
        paddingVertical: 16,
        borderRadius: 8,
        alignItems: 'center',
        marginTop: 8,
        marginBottom: 16, // Reduced
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
        color: '#6B7280',
        fontSize: 14,
    },
    link: {
        color: '#4F46E5',
        fontSize: 14,
        fontWeight: '600',
    },
});

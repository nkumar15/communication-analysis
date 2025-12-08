import auth from '@react-native-firebase/auth';
import InAppBrowser from 'react-native-inappbrowser-reborn';
import AsyncStorage from '@react-native-async-storage/async-storage';

/**
 * WebView-based OIDC authentication for React Native
 * Matches the web Firebase GCIP multi-tenant OIDC flow
 */

/**
 * Build the OIDC authorization URL
 * This creates the same URL that Firebase Web SDK uses internally
 */
export function buildOIDCAuthorizationUrl(config) {
    const { apiKey, projectId, tenantId, providerId, loginHint } = config;

    // Firebase Identity Toolkit endpoint for OIDC
    const baseUrl = 'https://identitytoolkit.googleapis.com/v2/accounts:signInWithIdp';

    const params = new URLSearchParams({
        key: apiKey,
        providerId: providerId,
        tenantId: tenantId,
        // The redirect URL should match what's configured in Firebase Console
        continueUrl: 'https://app.example.com/__/auth/handler',
        // Custom parameters for the OIDC provider
        customParameter: JSON.stringify({
            login_hint: loginHint,
            screen_hint: 'login'
        }),
    });

    return `${baseUrl}?${params.toString()}`;
}

/**
 * Sign in with OIDC using WebView
 * Opens in-app browser, handles OAuth flow, extracts credentials
 */
export async function signInWithWebViewOIDC(tenantId, providerId, email, apiKey, projectId) {
    try {
        console.log('🔐 Starting WebView OIDC flow:', { tenantId, providerId, email });

        // 1. Set tenant context
        auth().tenantId = tenantId;
        await AsyncStorage.setItem('firebase_tenant_id', tenantId);

        // 2. Build authorization URL
        const authUrl = buildOIDCAuthorizationUrl({
            apiKey,
            projectId,
            tenantId,
            providerId,
            loginHint: email
        });

        console.log('🌐 Opening browser for OIDC auth...');

        // 3. Open in-app browser
        // Note: The redirect URL should be configured in your Firebase Console
        // and in your AndroidManifest.xml as an intent filter
        const result = await InAppBrowser.openAuth(
            authUrl,
            'https://app.example.com/__/auth/handler',
            {
                // iOS specific
                ephemeralWebSession: false,
                // Android specific
                showTitle: true,
                enableUrlBarHiding: true,
                enableDefaultShare: false,
            }
        );

        console.log('📱 Browser result:', result.type);

        if (result.type === 'success') {
            // 4. Extract credentials from callback URL
            const url = new URL(result.url);

            // Firebase returns the ID token as a URL parameter or fragment
            // The exact format depends on your OIDC provider configuration
            const idToken = url.searchParams.get('id_token') ||
                url.hash.match(/id_token=([^&]*)/)?.[1];

            const accessToken = url.searchParams.get('access_token') ||
                url.hash.match(/access_token=([^&]*)/)?.[1];

            if (!idToken) {
                throw new Error('No ID token received from OAuth flow');
            }

            console.log('✅ Got ID token from OAuth');

            // 5. Sign in with Firebase using the credential
            // For OIDC providers, we need to use signInWithCredential
            const credential = auth.OAuthProvider.credential(
                providerId,
                idToken,
                accessToken
            );

            const userCredential = await auth().signInWithCredential(credential);
            console.log('✅ Firebase sign-in successful:', userCredential.user.email);

            return userCredential;
        } else if (result.type === 'cancel') {
            throw new Error('Authentication cancelled by user');
        } else {
            throw new Error(`Authentication failed: ${result.type}`);
        }
    } catch (error) {
        console.error('❌ WebView OIDC error:', error);
        throw error;
    }
}

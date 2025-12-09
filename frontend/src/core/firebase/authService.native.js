import auth from '@react-native-firebase/auth';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { signInWithWebViewOIDC } from './webViewOAuth.native';

// Import Firebase Web SDK for multi-tenant custom token (native SDK has tenantId issues)
import { initializeApp, getApps } from 'firebase/app';
import {
    initializeAuth,
    getAuth,
    signInWithCustomToken as webSignInWithCustomToken,
    getReactNativePersistence
} from 'firebase/auth';

// Firebase config - matches google-services.json
const firebaseConfig = {
    apiKey: 'AIzaSyCtYXGa5VpSIvmR26hrdj4FqVXJAqxNdKk',
    authDomain: 'enterprisesso-babb5.firebaseapp.com',
    projectId: 'enterprisesso-babb5',
    storageBucket: 'enterprisesso-babb5.firebasestorage.app',
    messagingSenderId: '571096413866',
    appId: '1:571096413866:android:c759d8cd379cfe2001b9e3'
};

/**
 * Production React Native Firebase Auth Service
 * 
 * Uses HYBRID approach:
 * - Native SDK (@react-native-firebase/auth) for general auth operations
 * - Web SDK (firebase/auth) for signInWithCustomToken with multi-tenancy
 *   (Native SDK has a bug where tenantId setter doesn't work)
 */
class NativeFirebaseAuthService {
    constructor() {
        this.auth = auth();
        this.webAuth = null;
        console.log('🔥 Firebase Native SDK initialized');
    }

    /**
     * Get or initialize the Web Auth instance for multi-tenant operations
     */
    getWebAuth() {
        if (!this.webAuth) {
            let app;
            const apps = getApps();
            const existingApp = apps.find(a => a.name === 'webAuthTenant');

            if (existingApp) {
                app = existingApp;
            } else {
                app = initializeApp(firebaseConfig, 'webAuthTenant');
            }

            try {
                this.webAuth = initializeAuth(app, {
                    persistence: getReactNativePersistence(AsyncStorage)
                });
            } catch (e) {
                // Auth already initialized for this app
                this.webAuth = getAuth(app);
            }
        }
        return this.webAuth;
    }

    /**
     * Set Firebase tenant context
     */
    async setTenantId(tenantId) {
        console.log('🔧 Setting Firebase tenant ID:', tenantId);
        // Store for later use (Web SDK will use this)
        await AsyncStorage.setItem('firebase_tenant_id', tenantId);

        // Also try to set on native SDK (may not work but won't hurt)
        try {
            this.auth.tenantId = tenantId;
        } catch (e) {
            console.log('Note: Native SDK tenantId setter may not work');
        }
    }

    /**
     * Get current tenant ID
     */
    async getTenantId() {
        return await AsyncStorage.getItem('firebase_tenant_id');
    }

    /**
     * Sign in with OIDC provider using WebView
     */
    async signInWithOIDC(providerId, loginHint) {
        try {
            const tenantId = await this.getTenantId();
            if (!tenantId) {
                throw new Error('No tenant ID set. Call setTenantId() first.');
            }

            console.log('🔐 Starting OIDC sign-in:', { providerId, loginHint });

            const app = this.auth.app;
            const apiKey = app.options.apiKey;
            const projectId = app.options.projectId;

            console.log('🔥 Using Firebase project:', projectId);

            const userCredential = await signInWithWebViewOIDC(
                tenantId,
                providerId,
                loginHint,
                apiKey,
                projectId
            );

            return userCredential;
        } catch (error) {
            console.error('❌ OIDC sign-in error:', error);
            throw error;
        }
    }

    /**
     * Sign in with a custom token (for mobile OAuth flow)
     * 
     * IMPORTANT: Uses Firebase Web SDK because the native SDK's
     * tenantId setter doesn't work properly (returns null).
     * 
     * @param {string} customToken - Firebase custom token from backend
     * @param {string} tenantId - Firebase tenant ID to set before sign-in
     */
    async signInWithCustomToken(customToken, tenantId = null) {
        try {
            // Get tenant ID from parameter or storage
            const effectiveTenantId = tenantId || await this.getTenantId();

            console.log('🔐 signInWithCustomToken (using Web SDK)');
            console.log('   Tenant ID:', effectiveTenantId);

            if (!effectiveTenantId) {
                throw new Error('Tenant ID is required for multi-tenant sign-in');
            }

            // Use Web SDK which properly supports tenantId
            const webAuth = this.getWebAuth();

            // Set tenant ID on Web Auth (this works correctly)
            webAuth.tenantId = effectiveTenantId;
            console.log('   Web auth.tenantId set to:', webAuth.tenantId);

            // Sign in using Web SDK
            const userCredential = await webSignInWithCustomToken(webAuth, customToken);
            console.log('✅ Signed in with custom token (Web SDK):', userCredential.user?.uid);
            console.log('   User tenant ID:', userCredential.user?.tenantId);

            // Store the tenant ID for future use
            await AsyncStorage.setItem('firebase_tenant_id', effectiveTenantId);

            return userCredential;
        } catch (error) {
            console.error('❌ signInWithCustomToken error:', error);
            console.error('   Error code:', error.code);
            console.error('   Error message:', error.message);
            throw error;
        }
    }

    /**
     * Get Firebase ID token for API authentication
     * Tries Web SDK first (if signed in there), then native SDK
     */
    async getIdToken(forceRefresh = false) {
        // Try Web SDK first if available
        try {
            const webAuth = this.getWebAuth();
            if (webAuth.currentUser) {
                const token = await webAuth.currentUser.getIdToken(forceRefresh);
                console.log('✅ Got ID token from Web SDK (length:', token?.length, ')');
                return token;
            }
        } catch (e) {
            console.log('Web SDK user not available, trying native SDK');
        }

        // Fallback to native SDK
        const user = this.auth.currentUser;
        if (!user) {
            console.error('❌ No current user');
            return null;
        }

        try {
            const token = await user.getIdToken(forceRefresh);
            console.log('✅ Got ID token from Native SDK (length:', token?.length, ')');
            return token;
        } catch (error) {
            console.error('❌ Error getting ID token:', error);
            return null;
        }
    }

    /**
     * Get current user (checks both SDKs)
     */
    getCurrentUser() {
        // Try Web SDK first
        try {
            const webAuth = this.getWebAuth();
            if (webAuth.currentUser) {
                return webAuth.currentUser;
            }
        } catch (e) {
            // Ignore
        }
        return this.auth.currentUser;
    }

    /**
     * Sign out from both SDKs
     */
    async signOut() {
        try {
            // Sign out from Web SDK
            try {
                const webAuth = this.getWebAuth();
                await webAuth.signOut();
            } catch (e) {
                console.log('Web SDK signOut:', e.message);
            }

            // Sign out from native SDK
            await this.auth.signOut();
            await AsyncStorage.removeItem('firebase_tenant_id');
            console.log('✅ Signed out successfully');
        } catch (error) {
            console.error('❌ Sign out error:', error);
            throw error;
        }
    }

    /**
     * Listen for auth state changes (native SDK)
     */
    onAuthStateChanged(callback) {
        return this.auth.onAuthStateChanged(callback);
    }
}

export default new NativeFirebaseAuthService();

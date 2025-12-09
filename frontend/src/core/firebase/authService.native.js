import auth from '@react-native-firebase/auth';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { signInWithWebViewOIDC } from './webViewOAuth.native';

/**
 * Production React Native Firebase Auth Service
 * Uses native Firebase SDK with WebView for OIDC
 * 
 * Note: React Native Firebase auto-initializes from google-services.json
 * No manual initialization needed!
 */
class NativeFirebaseAuthService {
    constructor() {
        this.auth = auth();
        console.log('🔥 Firebase Native SDK initialized');
    }

    /**
     * Set Firebase tenant context
     */
    async setTenantId(tenantId) {
        console.log('🔧 Setting Firebase tenant ID:', tenantId);
        this.auth.tenantId = tenantId;
        await AsyncStorage.setItem('firebase_tenant_id', tenantId);
    }

    /**
     * Get current tenant ID
     */
    async getTenantId() {
        if (this.auth.tenantId) return this.auth.tenantId;
        return await AsyncStorage.getItem('firebase_tenant_id');
    }

    /**
     * Sign in with OIDC provider using WebView
     * This matches the web implementation but uses in-app browser
     * 
     * @param {string} providerId - e.g., 'oidc.auth0-company'
     * @param {string} loginHint - Email to pre-fill
     */
    async signInWithOIDC(providerId, loginHint) {
        try {
            const tenantId = await this.getTenantId();
            if (!tenantId) {
                throw new Error('No tenant ID set. Call setTenantId() first.');
            }

            console.log('🔐 Starting OIDC sign-in:', { providerId, loginHint });

            // Get Firebase config from the app instance
            // These come from google-services.json automatically
            const app = this.auth.app;
            const apiKey = app.options.apiKey;
            const projectId = app.options.projectId;

            console.log('🔥 Using Firebase project:', projectId);

            // Use WebView OAuth flow
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
     * Get Firebase ID token for API authentication
     */
    async getIdToken(forceRefresh = false) {
        const user = this.auth.currentUser;
        if (!user) {
            console.error('❌ No current user');
            return null;
        }

        try {
            const token = await user.getIdToken(forceRefresh);
            console.log('✅ Got ID token (length:', token?.length, ')');
            return token;
        } catch (error) {
            console.error('❌ Error getting ID token:', error);
            return null;
        }
    }

    /**
     * Get current user
     */
    getCurrentUser() {
        return this.auth.currentUser;
    }

    /**
     * Sign in with a custom token (for mobile OAuth flow)
     * Must have tenant ID set first!
     * 
     * IMPORTANT: For GCIP multi-tenancy, the auth.tenantId must match
     * the tenant_id embedded in the custom token by the server.
     * 
     * @param {string} customToken - Firebase custom token from backend
     * @param {string} tenantId - Firebase tenant ID to set before sign-in
     */
    async signInWithCustomToken(customToken, tenantId = null) {
        try {
            // Get tenant ID from parameter or storage
            const effectiveTenantId = tenantId || await this.getTenantId();

            console.log('🔐 signInWithCustomToken called');
            console.log('   Tenant ID from parameter:', tenantId);
            console.log('   Tenant ID from storage:', await this.getTenantId());
            console.log('   Effective tenant ID:', effectiveTenantId);
            console.log('   Current auth.tenantId:', this.auth.tenantId);

            // Critical: Set tenant ID on auth instance SYNCHRONOUSLY before sign-in
            if (effectiveTenantId) {
                this.auth.tenantId = effectiveTenantId;
                console.log('   Set auth.tenantId to:', this.auth.tenantId);
            } else {
                console.error('❌ No tenant ID available!');
                throw new Error('Tenant ID is required for multi-tenant sign-in');
            }

            const userCredential = await this.auth.signInWithCustomToken(customToken);
            console.log('✅ Signed in with custom token:', userCredential.user?.uid);
            console.log('   User tenant ID:', userCredential.user?.tenantId);
            return userCredential;
        } catch (error) {
            console.error('❌ signInWithCustomToken error:', error);
            console.error('   Error code:', error.code);
            console.error('   Error message:', error.message);
            throw error;
        }
    }

    /**
     * Sign out
     */
    async signOut() {
        try {
            await this.auth.signOut();
            await AsyncStorage.removeItem('firebase_tenant_id');
            console.log('✅ Signed out successfully');
        } catch (error) {
            console.error('❌ Sign out error:', error);
            throw error;
        }
    }

    /**
     * Listen for auth state changes
     */
    onAuthStateChanged(callback) {
        return this.auth.onAuthStateChanged(callback);
    }
}

export default new NativeFirebaseAuthService();

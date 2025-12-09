import auth from '@react-native-firebase/auth';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { signInWithWebViewOIDC } from './webViewOAuth.native';

/**
 * Production React Native Firebase Auth Service
 * Uses native Firebase SDK with proper setTenantId() method
 * 
 * Note: React Native Firebase uses setTenantId() METHOD, not property setter!
 */
class NativeFirebaseAuthService {
    constructor() {
        this.auth = auth();
        console.log('🔥 Firebase Native SDK initialized');
    }

    /**
     * Set Firebase tenant context
     * IMPORTANT: Uses setTenantId() async METHOD, not property setter!
     */
    async setTenantId(tenantId) {
        console.log('🔧 Setting Firebase tenant ID:', tenantId);
        // Use the ASYNC METHOD, not property setter
        await this.auth.setTenantId(tenantId);
        // Also store in AsyncStorage for persistence
        await AsyncStorage.setItem('firebase_tenant_id', tenantId);
        console.log('✅ Tenant ID set successfully:', this.auth.tenantId);
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
     * Sign in with a custom token (for mobile OAuth flow)
     * 
     * IMPORTANT: Must call setTenantId() BEFORE signInWithCustomToken()!
     * The tenantId in the custom token must match the auth.tenantId
     * 
     * @param {string} customToken - Firebase custom token from backend
     * @param {string} tenantId - Firebase tenant ID to set before sign-in
     */
    async signInWithCustomToken(customToken, tenantId = null) {
        try {
            // Get tenant ID from parameter or storage
            const effectiveTenantId = tenantId || await this.getTenantId();

            console.log('🔐 signInWithCustomToken starting');
            console.log('   Tenant ID:', effectiveTenantId);
            console.log('   Current auth.tenantId before set:', this.auth.tenantId);

            if (!effectiveTenantId) {
                throw new Error('Tenant ID is required for multi-tenant sign-in');
            }

            // Set tenant ID using the async METHOD (not property setter!)
            await this.auth.setTenantId(effectiveTenantId);
            console.log('   auth.tenantId after setTenantId():', this.auth.tenantId);

            // Now sign in with custom token
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

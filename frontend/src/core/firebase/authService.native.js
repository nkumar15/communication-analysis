import auth from '@react-native-firebase/auth';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { signInWithWebViewOIDC } from './webViewOAuth.native';

/**
 * Production React Native Firebase Auth Service
 * Uses native Firebase SDK with WebView for OIDC
 */
class NativeFirebaseAuthService {
    constructor() {
        this.auth = auth();
        // These will be loaded from env or google-services.json
        this.apiKey = null;
        this.projectId = null;
    }

    /**
     * Initialize with Firebase config
     * Call this before using the service
     */
    async initialize(config) {
        this.apiKey = config.apiKey;
        this.projectId = config.projectId;
        console.log('🔧 Firebase initialized:', this.projectId);
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
            if (!this.apiKey || !this.projectId) {
                throw new Error('Firebase not initialized. Call initialize() first.');
            }

            const tenantId = await this.getTenantId();
            if (!tenantId) {
                throw new Error('No tenant ID set. Call setTenantId() first.');
            }

            console.log('🔐 Starting OIDC sign-in:', { providerId, loginHint });

            // Use WebView OAuth flow
            const userCredential = await signInWithWebViewOIDC(
                tenantId,
                providerId,
                loginHint,
                this.apiKey,
                this.projectId
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

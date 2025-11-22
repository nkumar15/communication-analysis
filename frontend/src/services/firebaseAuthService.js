import { auth } from '../firebase-config';
import {
    signInWithPopup,
    getRedirectResult,
    OAuthProvider,
    signOut as firebaseSignOut
} from 'firebase/auth';

class FirebaseAuthService {
    constructor() {
        this.auth = auth;
    }

    /**
     * Set the Firebase tenant context
     * This must be called before signing in
     */
    setTenantId(tenantId) {
        this.auth.tenantId = tenantId;
        // Persist to localStorage so it survives the redirect
        localStorage.setItem('firebase_tenant_id', tenantId);
    }

    /**
     * Sign in with OIDC provider using popup flow
     * Popup flow is more reliable for multi-tenancy
     * 
     * @param {string} providerId - The OIDC provider ID from Google Cloud (e.g., 'oidc.auth0-firstcompany')
     */
    async signInWithOIDC(providerId = 'oidc.generic') {
        const provider = new OAuthProvider(providerId);

        // Use popup instead of redirect for better state management
        const result = await signInWithPopup(this.auth, provider);
        return result;
    }

    /**
     * Handle redirect result after authentication
     * Call this on app load to check if user was redirected back from IdP
     */
    async handleRedirectResult() {
        try {
            console.log('🔍 Getting redirect result from Firebase...');
            console.log('Auth state:', {
                currentUser: this.auth.currentUser?.email || 'none',
                tenantId: this.auth.tenantId,
                name: this.auth.name,
                config: this.auth.config
            });

            const result = await getRedirectResult(this.auth);

            console.log('📦 Raw result:', result);

            if (result) {
                console.log('✅ User signed in:', {
                    email: result.user?.email,
                    uid: result.user?.uid,
                    tenantId: result.user?.tenantId,
                    providerId: result.providerId
                });
            } else {
                console.log('⚠️ getRedirectResult returned null');
            }

            return result;
        } catch (error) {
            console.error('❌ Error in handleRedirectResult:', {
                code: error.code,
                message: error.message,
                stack: error.stack
            });
            throw error;
        }
    }

    /**
     * Get the current user's ID token
     * This token is used for authenticated API calls
     * 
     * @param {boolean} forceRefresh - Force token refresh (useful after just signing in)
     */
    async getIdToken(forceRefresh = false) {
        const user = this.auth.currentUser;
        if (!user) {
            console.error('❌ No current user when getting ID token');
            return null;
        }

        try {
            console.log('🔑 Getting ID token for user:', user.email, 'forceRefresh:', forceRefresh);
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
     * Sign out current user
     */
    async signOut() {
        try {
            await firebaseSignOut(this.auth);
        } catch (error) {
            console.error('Sign out error:', error);
            throw error;
        }
    }

    /**
     * Listen for authentication state changes
     */
    onAuthStateChanged(callback) {
        return this.auth.onAuthStateChanged(callback);
    }
}

export default new FirebaseAuthService();

import { auth } from './config';
import {
    signInWithPopup,
    getRedirectResult,
    signInWithCustomToken,
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
     * @param {string} loginHint - Optional email to pre-fill in IdP login form
     */
    async signInWithOIDC(providerId = 'oidc.generic', loginHint = null) {
        const provider = new OAuthProvider(providerId);

        // Pass email as login hint to pre-fill IdP login form
        const customParams = {};

        if (loginHint) {
            customParams.login_hint = loginHint;
        }

        // Suggest to IdP: show login screen only (not signup)
        // Note: Whether this is respected depends on your IdP configuration
        customParams.screen_hint = 'login';

        provider.setCustomParameters(customParams);

        // Use popup instead of redirect for better state management
        const result = await signInWithPopup(this.auth, provider);
        return result;
    }

    /**
     * Skeletal SAML Sign In
     * @param {string} providerId 
     */
    async signInWithSAML(providerId) {
        console.warn('⚠️ SAML Sign-In not yet implemented. Provider:', providerId);
        // TODO: Implement SAMLAuthProvider logic
        // const provider = new SAMLAuthProvider(providerId);
        // return signInWithPopup(this.auth, provider);
        alert("SAML Login is not fully implemented yet.");
        throw new Error("SAML_NOT_IMPLEMENTED");
    }

    /**
     * Sign In with Google (treated as OIDC)
     */
    async signInWithGoogle(providerId, loginHint) {
        return this.signInWithOIDC(providerId, loginHint);
    }

    /**
     * Sign In with Microsoft (treated as OIDC)
     */
    async signInWithMicrosoft(providerId, loginHint) {
        return this.signInWithOIDC(providerId, loginHint);
    }

    /**
     * Generic Sign In Dispatcher
     * @param {string} providerType - 'oidc', 'saml', 'google', 'microsoft'
     * @param {string} providerId 
     * @param {string} loginHint 
     */
    async signIn(providerType, providerId, loginHint) {
        console.log(`🔐 Signing in with ${providerType} (${providerId})`);

        switch (providerType) {
            case 'saml':
                return this.signInWithSAML(providerId);
            case 'google':
                return this.signInWithGoogle(providerId, loginHint);
            case 'microsoft':
                return this.signInWithMicrosoft(providerId, loginHint);
            case 'oidc':
            default:
                return this.signInWithOIDC(providerId, loginHint);
        }
    }

    /**
     * Sign in with a Firebase custom token (for E2E testing)
     * 
     * @param {string} customToken - Firebase custom token from Admin SDK
     */
    async signInWithCustomToken(customToken) {
        const result = await signInWithCustomToken(this.auth, customToken);
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

            // Clear tenant context from the auth instance
            this.auth.tenantId = null;

            // Clear stored tenant context to prevent stale sessions
            localStorage.removeItem('firebase_tenant_id');
            localStorage.removeItem('token');
            localStorage.removeItem('impersonating');
            localStorage.removeItem('impersonation_token');
            localStorage.removeItem('impersonation_tenant');

            console.log('✅ User signed out, auth and localStorage cleared');
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

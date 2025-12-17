import { auth } from './b2c-config';
import {
    signInWithPopup,
    getRedirectResult,
    signInWithCustomToken,
    OAuthProvider,
    signOut as firebaseSignOut
} from 'firebase/auth';

class B2CAuthService {
    constructor() {
        this.auth = auth;
    }

    /**
     * Sign in with OIDC provider using popup flow
     */
    async signInWithOIDC(providerId = 'oidc.generic', loginHint = null) {
        const provider = new OAuthProvider(providerId);
        const customParams = {};
        if (loginHint) {
            customParams.login_hint = loginHint;
        }
        customParams.screen_hint = 'login';
        provider.setCustomParameters(customParams);
        const result = await signInWithPopup(this.auth, provider);
        return result;
    }

    /**
     * Get the current user's ID token
     */
    async getIdToken(forceRefresh = false) {
        const user = this.auth.currentUser;
        if (!user) {
            console.error('❌ [B2C] No current user when getting ID token');
            return null;
        }
        try {
            const token = await user.getIdToken(forceRefresh);
            return token;
        } catch (error) {
            console.error('❌ [B2C] Error getting ID token:', error);
            return null;
        }
    }

    getCurrentUser() {
        return this.auth.currentUser;
    }

    async signOut() {
        try {
            await firebaseSignOut(this.auth);
            console.log('✅ [B2C] User signed out');
        } catch (error) {
            console.error('Sign out error:', error);
            throw error;
        }
    }

    onAuthStateChanged(callback) {
        return this.auth.onAuthStateChanged(callback);
    }
}

export default new B2CAuthService();

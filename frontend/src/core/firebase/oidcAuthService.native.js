/**
 * Mobile OIDC Authentication Service
 * Uses react-native-app-auth for system browser-based OAuth/OIDC
 * 
 * This provides production-grade OAuth for mobile that mirrors
 * the web's signInWithPopup flow but using the native browser.
 */
import { authorize } from 'react-native-app-auth';

// Helper to generate a random nonce string
const generateNonce = (length = 32) => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
};

class OIDCAuthService {
    /**
     * Perform OAuth/OIDC login using system browser
     * 
     * @param {object} config - OIDC configuration
     * @param {string} config.issuer - IdP issuer URL (e.g., 'https://accounts.google.com')
     * @param {string} config.clientId - OAuth client ID
     * @param {string[]} config.scopes - Requested scopes
     * @param {string} config.email - Optional email hint
     * @returns {Promise<object>} - { idToken, accessToken, refreshToken, nonce }
     */
    async signInWithOIDC({ issuer, clientId, scopes, email }) {
        const nonce = generateNonce();

        const config = {
            issuer,
            clientId,
            // Use simple scheme-based redirect compatible with AndroidManifest config
            redirectUrl: 'com.saas.b2b://oauth/callback',
            scopes: scopes || ['openid', 'profile', 'email'],
            // Pass additional parameters for better UX
            additionalParameters: email ? {
                login_hint: email,
                screen_hint: 'login',  // Suggest login, not signup
                nonce: nonce, // Pass nonce to IdP (Auth0)
            } : {
                nonce: nonce,
            },
            // Also explicitly set nonce if supported by the library version directly
            nonce: nonce,
        };

        console.log('🔐 Starting OAuth flow with config:', {
            issuer,
            clientId,
            redirectUrl: config.redirectUrl,
            scopes: config.scopes,
            nonce: nonce,
        });

        // DEBUG: Log the expected redirect URL
        console.warn('EXPECTED REDIRECT URL:', config.redirectUrl);

        try {
            // Opens system browser, handles OAuth flow, returns tokens
            const result = await authorize(config);

            console.log('✅ OAuth successful:', {
                hasIdToken: !!result.idToken,
                hasAccessToken: !!result.accessToken,
                hasRefreshToken: !!result.refreshToken,
            });

            return {
                idToken: result.idToken,
                accessToken: result.accessToken,
                refreshToken: result.refreshToken,
                tokenType: result.tokenType,
                nonce: nonce, // Return the nonce we sent
            };
        } catch (error) {
            console.error('❌ OAuth error:', error);
            throw new Error(`OAuth failed: ${error.message}`);
        }
    }
}

export default new OIDCAuthService();

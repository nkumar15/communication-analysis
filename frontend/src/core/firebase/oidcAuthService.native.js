/**
 * Mobile OIDC Authentication Service
 * Uses react-native-app-auth for system browser-based OAuth/OIDC
 * 
 * This provides production-grade OAuth for mobile that mirrors
 * the web's signInWithPopup flow but using the native browser.
 */
import { authorize } from 'react-native-app-auth';

class OIDCAuthService {
    /**
     * Perform OAuth/OIDC login using system browser
     * 
     * @param {object} config - OIDC configuration
     * @param {string} config.issuer - IdP issuer URL (e.g., 'https://accounts.google.com')
     * @param {string} config.clientId - OAuth client ID
     * @param {string[]} config.scopes - Requested scopes
     * @param {string} config.email - Optional email hint
     * @returns {Promise<object>} - { idToken, accessToken, refreshToken }
     */
    async signInWithOIDC({ issuer, clientId, scopes, email }) {
        const config = {
            issuer,
            clientId,
            // Use simple scheme-based redirect compatible with AndroidManifest config
            redirectUrl: 'com.saas.b2b://oauth/callback',
            scopes: scopes || ['openid', 'profile', 'email'],
            // Pass additional parameters for better UX
            additionalParameters: email ? {
                login_hint: email,
                screen_hint: 'login'  // Suggest login, not signup
            } : {},
        };

        console.log('🔐 Starting OAuth flow with config:', {
            issuer,
            clientId,
            redirectUrl: config.redirectUrl,
            scopes: config.scopes,
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
            };
        } catch (error) {
            console.error('❌ OAuth error:', error);
            throw new Error(`OAuth failed: ${error.message}`);
        }
    }
}

export default new OIDCAuthService();

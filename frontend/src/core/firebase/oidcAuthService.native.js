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

// Trivial SHA256 implementation for React Native (avoiding polyfills)
// Source: https://geraintluff.github.io/sha256/
const sha256 = function sha256(ascii) {
    function rightRotate(value, amount) {
        return (value >>> amount) | (value << (32 - amount));
    }

    var mathPow = Math.pow;
    var maxWord = mathPow(2, 32);
    var result = ''

    var words = [];
    var asciiBitLength = ascii.length * 8;

    //* caching results is optional - remove/add slash from front of this line to toggle
    //0x80000000 | 0
    var hash = sha256.h = sha256.h || [];
    // Round constants: first 32 bits of the fractional parts of the cube roots of the first 64 primes
    var k = sha256.k = sha256.k || [];
    var primeCounter = k.length;

    var isComposite = {};
    for (var candidate = 2; primeCounter < 64; candidate++) {
        if (!isComposite[candidate]) {
            for (i = 0; i < 313; i += candidate) {
                isComposite[i] = candidate;
            }
            hash[primeCounter] = (mathPow(candidate, .5) * maxWord) | 0;
            k[primeCounter++] = (mathPow(candidate, 1 / 3) * maxWord) | 0;
        }
    }

    ascii += '\x80' // Append Ƈ' bit (plus zero padding)
    while (ascii.length % 64 - 56) ascii += '\x00' // More zero padding
    for (var i = 0; i < ascii.length; i++) {
        var j = ascii.charCodeAt(i);
        if (j >> 8) return; // ASCII check: only accept characters in range 0-255
        words[i >> 2] |= j << ((3 - i) % 4) * 8;
    }
    words[words.length] = ((asciiBitLength / maxWord) | 0);
    words[words.length] = (asciiBitLength)

    for (var j = 0; j < words.length;) {
        var w = words.slice(j, j += 16);
        var oldHash = hash;
        // This is now the "working hash", often labelled as variables a...g
        // (we have to truncate as we go, otherwise 'var typeof' prints 'number')
        hash = hash.slice(0, 8);

        for (var i = 0; i < 64; i++) {
            var i2 = i + j;
            // Expand the message into 64 words
            // Used below if 
            var w15 = w[i - 15], w2 = w[i - 2];

            // Iterate
            var a = hash[0], e = hash[4];
            var temp1 = hash[7] + (rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25)) // S1
                + ((e & hash[5]) ^ ((~e) & hash[6])) // ch
                + k[i]
                // Expand the message schedule if needed
                + (w[i] = (i < 16) ? w[i] : (
                    w[i - 16]
                    + (rightRotate(w15, 7) ^ rightRotate(w15, 18) ^ (w15 >>> 3)) // s0
                    + w[i - 7]
                    + (rightRotate(w2, 17) ^ rightRotate(w2, 19) ^ (w2 >>> 10)) // s1
                ) | 0
                );
            // This is only used once, so *could* be moved below, but it only saves 4 bytes and makes things unreadable
            var temp2 = (rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22)) // S0
                + ((a & hash[1]) ^ (a & hash[2]) ^ (hash[1] & hash[2])); // maj

            hash = [(temp1 + temp2) | 0].concat(hash);
            hash[4] = (hash[4] + temp1) | 0;
        }

        for (var i = 0; i < 8; i++) {
            hash[i] = (hash[i] + oldHash[i]) | 0;
        }
    }

    for (var i = 0; i < 8; i++) {
        for (var j = 3; j + 1; j--) {
            var b = (hash[i] >> (j * 8)) & 255;
            result += ((b < 16) ? 0 : '') + b.toString(16);
        }
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
        // 1. Generate Raw Nonce (e.g., "sVukkth...")
        const rawNonce = generateNonce();

        // 2. Hash it (GCIP expects ID Token to have hash of request nonce)
        const hashedNonce = sha256(rawNonce);

        console.log('🔒 Nonce debug:', { raw: rawNonce, hashed: hashedNonce });

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
                nonce: hashedNonce, // Pass HASHED nonce to IdP (Auth0)
            } : {
                nonce: hashedNonce,
            },
            // Also explicitly set nonce if supported by the library version directly
            // Note: react-native-app-auth usually puts this in state/nonce params
            nonce: hashedNonce,
        };

        console.log('🔐 Starting OAuth flow with config:', {
            issuer,
            clientId,
            redirectUrl: config.redirectUrl,
            scopes: config.scopes,
            nonceSentToAuth0: hashedNonce,
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
                tokenType: result.tokenType,
                nonce: rawNonce, // Return the RAW nonce (for GCIP verifiction against ID Token's hash)
            };
        } catch (error) {
            console.error('❌ OAuth error:', error);
            throw new Error(`OAuth failed: ${error.message}`);
        }
    }
}

export default new OIDCAuthService();

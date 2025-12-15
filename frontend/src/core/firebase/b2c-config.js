
import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, connectAuthEmulator } from 'firebase/auth';

/**
 * B2C Firebase Configuration
 * 
 * Uses separate project credentials (FIREBASE_B2C_*) than B2B.
 * In development, connects to the same emulator but theoretically uses different project.
 */
const firebaseConfig = {
    apiKey: process.env.FIREBASE_B2C_API_KEY || "demo-b2c-api-key",
    authDomain: process.env.FIREBASE_B2C_AUTH_DOMAIN || "demo-b2c.firebaseapp.com",
    projectId: process.env.FIREBASE_B2C_PROJECT_ID || "demo-b2c",
    storageBucket: process.env.FIREBASE_B2C_STORAGE_BUCKET,
    messagingSenderId: process.env.FIREBASE_B2C_MESSAGING_SENDER_ID,
    appId: process.env.FIREBASE_B2C_APP_ID
};

console.log('[B2C] Initializing Firebase with project:', firebaseConfig.projectId);

const app = initializeApp(firebaseConfig, 'b2c-app');
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

// Connect to emulator in development
// Connect to emulator in development ONLY if explicitly enabled
if (process.env.REACT_APP_USE_EMULATOR === 'true') {
    console.log('[B2C] Connecting to Auth Emulator');
    // Use same emulator port as B2B (9099)
    connectAuthEmulator(auth, 'http://localhost:9099', { disableWarnings: true });
}

export { auth, googleProvider };
export default app;

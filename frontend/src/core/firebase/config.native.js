/**
 * Firebase Config for React Native (Web SDK)
 * 
 * Uses Firebase Web SDK for multi-tenant operations since
 * @react-native-firebase/auth has issues with tenantId setter.
 */
import { initializeApp, getApps } from 'firebase/app';
import { initializeAuth, getAuth, getReactNativePersistence } from 'firebase/auth';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Firebase configuration - these should match your google-services.json
// and Firebase console settings
const firebaseConfig = {
    apiKey: 'AIzaSyCtYXGa5VpSIvmR26hrdj4FqVXJAqxNdKk',
    authDomain: 'enterprisesso-babb5.firebaseapp.com',
    projectId: 'enterprisesso-babb5',
    storageBucket: 'enterprisesso-babb5.firebasestorage.app',
    messagingSenderId: '571096413866',
    appId: '1:571096413866:android:c759d8cd379cfe2001b9e3'
};

// Initialize Firebase app (singleton)
let app;
let webAuth;

function getFirebaseApp() {
    if (!app) {
        const apps = getApps();
        if (apps.length === 0) {
            app = initializeApp(firebaseConfig, 'webAuth');
        } else {
            app = apps.find(a => a.name === 'webAuth') || initializeApp(firebaseConfig, 'webAuth');
        }
    }
    return app;
}

function getWebAuth() {
    if (!webAuth) {
        const firebaseApp = getFirebaseApp();
        try {
            webAuth = initializeAuth(firebaseApp, {
                persistence: getReactNativePersistence(AsyncStorage)
            });
        } catch (e) {
            // Auth already initialized
            webAuth = getAuth(firebaseApp);
        }
    }
    return webAuth;
}

export { getFirebaseApp, getWebAuth, firebaseConfig };

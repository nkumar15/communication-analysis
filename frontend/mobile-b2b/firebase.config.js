/**
 * Firebase configuration for React Native
 * Uses react-native-config to load from .env file
 */
import Config from 'react-native-config';

export const firebaseConfig = {
    apiKey: Config.REACT_APP_FIREBASE_API_KEY,
    projectId: Config.REACT_APP_FIREBASE_PROJECT_ID,
    authDomain: Config.REACT_APP_FIREBASE_AUTH_DOMAIN,
    storageBucket: Config.REACT_APP_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: Config.REACT_APP_FIREBASE_MESSAGING_SENDER_ID,
    appId: Config.REACT_APP_FIREBASE_APP_ID,
};

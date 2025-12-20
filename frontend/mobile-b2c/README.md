# Enterprise SSO - B2C Mobile App

Native mobile application for B2C users, built with React Native and Firebase.

## Setup

1. **Install Dependencies**:
   ```bash
   npm install
   # or
   yarn install
   ```

2. **Environment Configuration**:
   Copy `.env.example` to `.env` and update the values:
   ```bash
   cp .env.example .env
   ```
   *Note: Ensure `REACT_APP_API_URL` points to your backend (e.g., `http://10.0.2.2:8080` for Android Emulator accessing localhost).*

3. **Firebase Setup**:
   - Ensure `google-services.json` (Android) and `GoogleService-Info.plist` (iOS) are placed in their respective project directories (`android/app/` and `ios/`).
   - These files should correspond to your B2C Firebase Project.
   - *Note: For development with Emulators, ensure the config matches the emulator project ID.*

## Running the App

### Android
```bash
npm run android
```

### iOS
```bash
cd ios && pod install && cd ..
npm run ios
```

## Architecture

- **Authentication**: Direct Email/Password login via Firebase Auth.
- **Verification**: Enforces email verification before accessing the app.
- **Backend Sync**: Syncs user profile with the B2C Backend API upon successful login.
- **Navigation**: State-based navigation between Login/Signup/Dashboard.

## Directory Structure

- `App.tsx`: Main entry point & Navigation logic.
- `LoginScreen.tsx`: Login UI & logic.
- `SignupScreen.tsx`: Registration UI & logic.
- `DashboardScreen.tsx`: User workspace overview.

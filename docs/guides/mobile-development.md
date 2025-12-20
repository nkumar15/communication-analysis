# Mobile Development Guide

Guide for developing the B2B and B2C mobile applications.

## Directory Structure

```
frontend/
├── mobile-b2b/         # B2B mobile app (React Native)
├── mobile-b2c/         # B2C mobile app (scaffold)
└── mobile-shared/      # Shared code package
```

## Quick Start (B2B)

```bash
cd frontend/mobile-b2b

# Install dependencies
npm install

# Start Metro bundler (in separate terminal)
npx react-native start
# Or with cache clear:
npx react-native start --reset-cache

# iOS (in another terminal)
npx pod-install ios
npx react-native run-ios

# Android (in another terminal)
npx react-native run-android
```

## Firebase Configuration

Each mobile app needs its own Firebase config:

| App | Config File | Firebase Tenant |
|-----|-------------|-----------------|
| B2B | `firebase.config.js` | Per-customer tenant |
| B2C | TBD | B2C tenant |

## Shared Code (mobile-shared)

The `mobile-shared` package contains code used by both apps:
- Authentication helpers
- UI components
- Theme/design tokens

### Using in Apps

```javascript
// In mobile-b2b or mobile-b2c
import { useAuth, Button } from '@enterprisesso/mobile-shared';
```

## Testing

```bash
# Run tests
npm test

# Check React Native setup
npx react-native doctor
```

## Building for Release

See [Deployment Guide](deployment.md) for production builds.

# Secrets Directory

This directory is for **local development only** and contains sensitive credentials that should **NEVER** be committed to git.

## 🔐 Required Files for Local Development

### 1. Firebase Service Account Credentials

**File**: `firebase-credentials.json`

**How to obtain**:
1. Go to [Firebase Console](https://console.firebase.google.com)
2. Select your project
3. Navigate to: **Project Settings** → **Service Accounts**
4. Click **"Generate New Private Key"**
5. Save the downloaded JSON file as `firebase-credentials.json` in this directory

**File structure example**:
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com",
  ...
}
```

## 📁 Directory Structure

After setup, your secrets directory should look like:

```
secrets/
├── README.md (this file)
├── .gitkeep
└── firebase-credentials.json (YOU create this)
```

## ⚠️ Security Best Practices

1. **Never commit this directory's contents** (except README.md and .gitkeep)
   - The root `.gitignore` already excludes `secrets/` contents
   
2. **File permissions**: Restrict access to credentials
   ```bash
   chmod 600 secrets/firebase-credentials.json
   ```

3. **Different credentials per environment**:
   - **Local dev**: Use dev/staging Firebase project
   - **Production**: Use separate Firebase project with production credentials
   - **Never** use production credentials locally

4. **Rotation**: Rotate service account keys regularly (every 90 days recommended)

5. **Access control**: Only authorized team members should have access to production credentials

## 🐳 Docker Compose Integration

The `docker-compose.yml` mounts credentials from this directory:

```yaml
volumes:
  - ./secrets/firebase-credentials.json:/app/firebase-credentials.json:ro
```

The `:ro` flag mounts it as **read-only** for additional security.

## 🚀 First-Time Setup

If you're setting up this project for the first time:

1. **Copy the example environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Download Firebase credentials** (see instructions above)

3. **Place credentials in secrets directory**:
   ```bash
   # Make sure you're in the project root
   mv ~/Downloads/your-project-firebase-adminsdk-*.json secrets/firebase-credentials.json
   ```

4. **Secure the file**:
   ```bash
   chmod 600 secrets/firebase-credentials.json
   ```

5. **Update `.env`** with your configuration values

6. **Start the application**:
   ```bash
   docker-compose up -d
   ```

## 📝 Notes

- This directory is excluded from git via `.gitignore`
- Only `.gitkeep` and `README.md` are tracked in version control
- All other files in this directory are ignored and will NOT be committed
- If you accidentally commit credentials, **immediately rotate them** in Firebase Console

## 🆘 Troubleshooting

**Backend fails to start with "credentials not found"**:
- Verify `secrets/firebase-credentials.json` exists
- Check file permissions: `ls -la secrets/`
- Ensure docker-compose volume mount is correct

**"Permission denied" errors**:
```bash
chmod 600 secrets/firebase-credentials.json
```

**Accidentally committed credentials**:
1. Rotate the compromised key immediately in Firebase Console
2. Remove from git history:
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch secrets/firebase-credentials.json" \
     --prune-empty --tag-name-filter cat -- --all
   ```
3. Force push (⚠️ coordinate with team first!)

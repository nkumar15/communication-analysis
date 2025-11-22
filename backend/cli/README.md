# Tenant CLI Tool

Command-line tool for provisioning enterprise SSO tenants.

## Prerequisites

1. Set environment variables in `backend/.env`:
```bash
RESEND_API_KEY=re_your_key_here  # From resend.com
FRONTEND_URL=http://localhost:3000  # Or your production URL
```

2. Ensure Firebase credentials are in place:
```bash
secrets/firebase-credentials.json
```

## Usage

### Create a New Tenant

```bash
# From the backend directory
cd backend

# Run the CLI
python -m cli.tenant_cli create \
  --company "Acme Corporation" \
  --domain "acme.com" \
  --admin-email "admin@acme.com" \
  --oidc-provider "auth0" \
  --oidc-client-id "your_client_id" \
  --oidc-client-secret "your_client_secret" \
  --oidc-issuer "https://acme.auth0.com"
```

### Parameters

- `--company`: Company/tenant display name
- `--domain`: Email domain for tenant resolution (e.g., `acme.com`)
- `--admin-email`: Admin user email address
- `--oidc-provider`: OIDC provider type (`auth0`, `okta`, `google`, `azure`)
- `--oidc-client-id`: OIDC application client ID
- `--oidc-client-secret`: OIDC application client secret
- `--oidc-issuer`: OIDC issuer URL

### List Tenants

```bash
python -m cli.tenant_cli list-tenants --domain acme.com
```

## What It Does

The `create` command performs the following steps:

1. **Firebase Tenant Creation** - Creates isolated Firebase tenant
2. **OIDC Configuration** - Configures SSO provider for the tenant
3. **Activation Token** - Generates 48-hour activation token
4. **Database Record** - Creates tenant and admin user records
5. **Email Notification** - Sends activation email to admin

## Output Example

```
🚀 Creating tenant for Acme Corporation...

✅ Firebase Admin SDK initialized

📍 Step 1: Creating Firebase tenant...
✅ Firebase tenant created: acme-corp-xyz123

📍 Step 2: Configuring OIDC provider...
✅ OIDC provider ID: oidc.auth0

📍 Step 3: Generating activation token...
✅ Activation token generated (expires in 48 hours)

📍 Step 4: Creating tenant in database...
✅ Tenant created: ID 1

📍 Step 5: Creating admin user...
✅ Admin user created: admin@acme.com

📍 Step 6: Sending activation email...
📧 Activation email sent to admin@acme.com

======================================================================
✅ TENANT PROVISIONED SUCCESSFULLY
======================================================================
Company:          Acme Corporation
Domain:           acme.com
Admin Email:      admin@acme.com
Firebase Tenant:  acme-corp-xyz123
OIDC Provider:    oidc.auth0
Activation URL:   http://localhost:3000/activate/abc123...
Expires:          2025-11-24 22:00 UTC
======================================================================

✅ Next: Admin will receive activation email
```

## Error Handling

The CLI provides clear error messages:

- Missing environment variables
- Invalid domain format
- Database connection issues
- Firebase API errors
- Email sending failures

## Security Notes

- Activation tokens are cryptographically secure (32 bytes)
- Tokens expire after 48 hours
- Admin credentials are never stored - SSO only
- OIDC secrets are stored securely in Firebase

## Testing

For testing without sending real emails, omit the `RESEND_API_KEY` environment variable. The CLI will print the activation URL instead of sending an email.

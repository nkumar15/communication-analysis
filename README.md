# Multitenant SSO Application

Enterprise-grade multi-tenant SaaS application with SSO using OIDC and Firebase Identity Platform.

## Architecture

This application implements a secure multi-tenant SSO system where:
- **Tenant resolution** happens via email domain lookup
- **Firebase Identity Platform** manages multi-tenant OIDC authentication
- **OIDC providers** configured per-tenant in Firebase Console
- **Frontend** drives authentication using Firebase SDK
- **Backend** validates JWT tokens and manages app data
- **Stateless** JWT-based authentication (no sessions)

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Tenant and user data storage (asyncpg)
- **Firebase Admin SDK** - Token validation and user management
- **Docker** - Containerization

### Frontend
- **React 18** - UI framework (no CRA/Vite, using webpack directly)
- **React Router** - Client-side routing
- **Firebase SDK** - Authentication integration

## Project Structure

```
sso/
├── backend/
│   ├── app/
│   │   ├── routers/         # API endpoints
│   │   ├── services/        # Business logic
│   │   ├── middleware/      # Authentication middleware
│   │   ├── migrations/      # Database migrations
│   │   ├── config.py        # Configuration
│   │   ├── database.py      # Database connection
│   │   ├── models.py        # Data models
│   │   └── main.py          # FastAPI app
│   ├── .env.example         # Backend env template
│   ├── .gitignore
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # API service
│   │   ├── styles/          # CSS styles
│   │   ├── App.js
│   │   └── index.js
│   ├── public/
│   ├── .env.example         # Frontend env template
│   ├── .gitignore
│   ├── webpack.config.js
│   └── package.json
├── secrets/
│   ├── .gitkeep             # Track empty directory
│   ├── README.md            # Secrets setup guide
│   └── firebase-credentials.json  # ⚠️ YOU create (see secrets/README.md)
├── .env.example             # Environment template
├── .gitignore               # Ignore secrets and sensitive files
└── docker-compose.yml
```

## 🔒 Security Best Practices

> [!IMPORTANT]
> This project uses proper secrets management. **Never commit credentials to git!**

### Secrets Management

- **All credentials** stored in `/secrets` directory (git-ignored except README)
- **Environment variables** separated by component:
  - **Root `.env`** - Docker Compose shared config (database credentials)
  - **`backend/.env`** - Backend application config (secrets, Firebase, URLs)
  - **`frontend/.env`** - Frontend config (Firebase web config)
- **Firebase credentials** mounted read-only in Docker containers
- **No hardcoded secrets** in source code

### Protected Files (via .gitignore)

- `secrets/*` - All credential files
- `.env`, `backend/.env`, `frontend/.env` - Environment variables
- `*credentials*.json` - Any credential files
- `*firebase-adminsdk*.json` - Firebase service account keys

### First-Time Setup Checklist

1. ✅ Copy environment templates:
   - `cp .env.example .env`
   - `cp backend/.env.example backend/.env`
   - `cp frontend/.env.example frontend/.env`
2. ✅ Download Firebase credentials to `secrets/firebase-credentials.json`
3. ✅ Set file permissions: `chmod 600 secrets/firebase-credentials.json`
4. ✅ Fill in configuration values in all `.env` files
5. ✅ Never commit `.env` files or anything in `secrets/` (except `README.md`)

See [secrets/README.md](./secrets/README.md) for detailed setup instructions.

---

## 🚀 Quick Start (Using Makefile)

The fastest way to get started is using the provided Makefile:

```bash
# 1. Initial setup (creates .env files from templates)
make setup

# 2. Edit environment files with your configuration
nano .env                  # Docker Compose config (database credentials)
nano backend/.env          # Backend config (SECRET_KEY, FIREBASE_PROJECT_ID)
nano frontend/.env         # Frontend config (Firebase web config)

# 3. Download Firebase credentials to secrets/
# See secrets/README.md for instructions

# 4. Start all services
make up

# 5. Run database migrations
make migrate

# 6. In a new terminal, start frontend
make frontend-start
```

**Access your application**:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Common Commands**:
```bash
make help           # Show all available commands
make dev            # Start full dev environment (backend + frontend)
make logs           # View backend logs
make restart        # Restart all services
make down           # Stop all services
make status         # Show service status and URLs
```

---

## 📘 Detailed Setup Instructions

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Firebase project with Identity Platform enabled

### 1. Clone and Configure

```bash
# Copy environment templates
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Generate a secure secret key for backend
openssl rand -hex 32

# Edit root .env (Docker Compose shared config):
nano .env
# - POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD (database credentials)

# Edit backend .env (backend application config):
nano backend/.env
# - SECRET_KEY (use the generated key above)
# - FIREBASE_PROJECT_ID (your Firebase project ID)
# - FRONTEND_URL, BACKEND_URL
# - DATABASE_URL (will be overridden by docker-compose)
```

### 2. Firebase Setup

#### Download Firebase Credentials
1. Go to [Firebase Console](https://console.firebase.google.com)
2. Select your project
3. Go to Project Settings → Service Accounts
4. Click "Generate New Private Key"
5. **Important**: Save the file as `secrets/firebase-credentials.json` (NOT in project root)
6. Secure the file:
   ```bash
   chmod 600 secrets/firebase-credentials.json
   ```

#### Update Frontend Environment
Edit `frontend/.env` with your Firebase web app configuration:

```bash
# Get these from Firebase Console → Project Settings → Your apps
REACT_APP_FIREBASE_API_KEY=your-api-key
REACT_APP_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
REACT_APP_FIREBASE_PROJECT_ID=your-project-id
REACT_APP_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
REACT_APP_FIREBASE_APP_ID=your-app-id
REACT_APP_API_BASE_URL=http://localhost:8000
```

### 3. Configure Firebase Identity Platform

**Important**: With the Firebase-centric architecture, you configure OIDC providers in Firebase Console, not the database.

#### Create Tenant in Firebase Console

1. **Enable Multi-Tenancy**
   - Go to Firebase Console → Authentication → Settings
   - Enable "Multi-tenancy"

2. **Create Tenant**
   - Go to "Tenants" tab → Click "+ Add tenant"
   - Name: "Your Company"
   - Copy the **Tenant ID** (e.g., `yourcompany-abc123`)

3. **Configure OIDC Provider**
   - Select your tenant → "Sign-in method"
   - Add "SAML" or "OpenID Connect" provider
   - Configure your identity provider (Auth0, Okta, Google Workspace, Azure AD, etc.)
   - Example configuration:
     - Provider name: `oidc.yourprovider`
     - Client ID: (from your IdP)
     - Client Secret: (from your IdP)
     - Issuer URL: (from your IdP)

#### Update Database Migration

Edit `backend/app/migrations/001_initial.sql` with your tenant information:

```sql
INSERT INTO tenants (name, domain, firebase_tenant_id) VALUES (
    'Your Company',
    'yourcompany.com',  -- Email domain for tenant resolution
    'yourcompany-abc123'  -- Tenant ID from Firebase Console
);
```

**Example:**
```sql
INSERT INTO tenants (name, domain, firebase_tenant_id) VALUES (
    'Demo Corp',
    'democorp.com',
    'democorp-99oyw'
);
```

### 4. Start the Application

#### Using Makefile (Recommended)

```bash
# Start backend services
make up

# Run migrations
make migrate

# View logs
make logs

# Start frontend (in new terminal)
make frontend-start
```

#### Using Docker Compose Directly

```bash
# Start all services (PostgreSQL, Backend)
docker-compose up -d --build

# Run database migrations
docker-compose exec backend python app/migrations/run_migrations.py

# View logs
docker-compose logs -f backend
```

### 5. Install and Run Frontend

#### Using Makefile (Recommended)

```bash
# Install dependencies
make frontend-install

# Start dev server
make frontend-start
```

#### Using npm Directly

```bash
cd frontend

# If using nvm (recommended), use the correct Node.js version
nvm use

# Copy frontend environment template
cp .env.example .env

# Edit .env and add your Firebase configuration
# Get values from Firebase Console → Project Settings → Your apps
nano .env

# Install dependencies
npm install

# Start development server
npm start
```

The frontend will open at **http://localhost:3000**

**Note**: If you don't have nvm installed, make sure you're using Node.js 18+. You can check with:
```bash
node --version  # Should be v18.x or higher
```

## Usage

### Testing the Authentication Flow

1. **Open** http://localhost:3000
2. **Enter** an email with a domain matching your configured tenant (e.g., `user@yourcompany.com`)
3. **Click** Continue - you'll be redirected to your OIDC provider
4. **Authenticate** with your identity provider
5. **Welcome!** You'll be redirected back to the dashboard

### API Endpoints

- `POST /api/auth/resolve-tenant` - Resolve tenant from email (returns firebase_tenant_id)
- `GET /api/auth/me` - Get current user info (requires JWT token)
- `POST /api/auth/sync-user` - Sync user to database after Firebase auth

**Note**: Login/logout handled by Firebase SDK on frontend.

### API Documentation

Visit **http://localhost:8000/docs** for interactive API documentation.

## Authentication Flow

The application uses Firebase Identity Platform with multi-tenant support:

```
1. User enters email → Frontend
2. Frontend calls /api/auth/resolve-tenant → Backend
3. Backend looks up tenant by domain → PostgreSQL
4. Backend returns {tenant_id, firebase_tenant_id}
5. Frontend sets Firebase tenant context
6. Frontend initiates OIDC sign-in via Firebase SDK
7. Firebase redirects User → Tenant's configured IdP
8. User authenticates → IdP
9. IdP redirects with code → Firebase
10. Firebase exchanges code for tokens (handles PKCE)
11. Firebase redirects back → Frontend
12. Frontend receives Firebase ID token (JWT)
13. Frontend syncs user → Backend (with JWT in Authorization header)
14. Backend validates JWT with Firebase Admin SDK
15. Backend creates/updates user → PostgreSQL
16. Frontend fetches user info → Backend /api/auth/me (with JWT)
17. Dashboard displays welcome message
```

**Key Points:**
- Firebase SDK handles the entire OIDC flow (PKCE, state, redirects)
- JWT tokens used instead of session cookies
- Backend is stateless, validates tokens via Firebase Admin SDK
- No Redis needed

## Security Features

- **JWT tokens** - Firebase ID tokens for stateless authentication
- **Bearer tokens** - Standard Authorization header pattern
- **PKCE** - Handled automatically by Firebase SDK
- **State validation** - Managed by Firebase
- **Token validation** - Firebase Admin SDK verifies tokens
- **Multi-tenant isolation** - Data segmentation by tenant
- **Automatic token refresh** - Firebase SDK handles renewal

## Database Schema

### Tenants Table
```sql
- id (serial primary key)
- name (varchar)
- domain (varchar unique) -- for email domain resolution
- firebase_tenant_id (varchar unique) -- Firebase tenant ID
- is_active (boolean)
- created_at, updated_at (timestamp)
```

### Users Table
```sql
- id (serial primary key)
- tenant_id (foreign key)
- email (varchar)
- name (varchar)
- firebase_uid (varchar) -- Firebase user ID
- is_active (boolean)
- last_login (timestamp)
- created_at, updated_at (timestamp)
```

## Development Workflow

### Available Make Commands

Run `make help` to see all available commands. Here are the most commonly used:

#### Setup & Installation
```bash
make setup              # Initial project setup (creates .env files)
make frontend-install   # Install frontend npm dependencies
```

####  Docker Services
```bash
make up                 # Start all services (Postgres + Backend)
make down               # Stop all services  
make restart            # Restart all services
make build              # Rebuild Docker images
make logs               # View backend logs (follow mode)
make logs-all           # View all service logs
make ps                 # List running services
```

#### Database Management
```bash
make migrate            # Run database migrations
make db-shell           # Open PostgreSQL shell
make db-reset           # Reset database (WARNING: deletes all data)
```

#### Frontend Development
```bash
make frontend-start     # Start frontend dev server (http://localhost:3000)
make frontend-build     # Build frontend for production
```

#### Full Development Environment
```bash
make dev                # Start backend + frontend together
```

#### Utilities
```bash
make shell              # Open shell in backend container
make clean              # Clean up containers, volumes, build artifacts
make clean-all          # Complete cleanup including node_modules
make test-env           # Validate environment configuration
make status             # Show status  of all services and URLs
```

### Common Development Tasks

#### Starting Development
```bash
# First time setup
make setup
# Edit .env files with your configuration
make up
make migrate
make frontend-start
```

#### Daily Development
```bash
# Start backend
make up

# In another terminal, start frontend
make frontend-start

# View logs if needed
make logs
```

#### Restarting After Changes
```bash
# Backend code changes (auto-reload enabled)
# No restart needed!

# Backend dependency changes
make restart

# Frontend changes (auto-reload enabled)
# No restart needed!

# Frontend dependency changes
make frontend-install
# Then restart frontend dev server
```

#### Debugging
```bash
# View backend logs
make logs

# Open backend shell
make shell

# Open database shell
make db-shell

# Check service status
make status
```

#### Cleanup
```bash
# Stop services
make down

# Clean build artifacts
make clean

# Complete cleanup
make clean-all
```

### Environment Variables

The project uses three separate `.env` files:

**Root `.env`** - Docker Compose shared configuration:
```bash
POSTGRES_DB=sso_db
POSTGRES_USER=sso_user  
POSTGRES_PASSWORD=your-secure-password
```

**`backend/.env`** - Backend application configuration:
```bash
SECRET_KEY=your-secret-key-here
FIREBASE_PROJECT_ID=your-firebase-project
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
DATABASE_URL=postgresql://sso_user:password@postgres:5432/sso_db
```

**`frontend/.env`** - Frontend configuration:
```bash
REACT_APP_FIREBASE_API_KEY=your-api-key
REACT_APP_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
REACT_APP_FIREBASE_PROJECT_ID=your-project-id
# ... other Firebase config
REACT_APP_API_BASE_URL=http://localhost:8000
```

## Development

### Backend Development

```bash
# Rebuild backend after dependency changes
docker-compose up -d --build backend

# Restart backend after code changes
docker-compose restart backend

# View backend logs
docker-compose logs -f backend

# Access PostgreSQL
docker-compose exec postgres psql -U sso_user -d sso_db
```

### Frontend Development

```bash
cd frontend

# Development mode (hot reload)
npm start

# Production build
npm run build
```

## Adding New Tenants

To add a new tenant:

1. **Create tenant in Firebase Console**
   - Authentication → Tenants → Add tenant
   - Configure OIDC provider for the tenant
   - Copy the tenant ID

2. **Insert into database:**

```sql
INSERT INTO tenants (name, domain, firebase_tenant_id) VALUES (
    'New Company',
    'newcompany.com',  -- Email domain
    'newcompany-xyz123'  -- Firebase tenant ID from Console
);
```

## Troubleshooting

### Backend won't start
- Check `.env` file exists and has correct values
- Verify `firebase-credentials.json` exists in project root
- Check logs: `docker-compose logs backend`

### Authentication fails
- Verify OIDC configuration in database matches your IdP
- Check callback URL is registered with IdP: `http://localhost:8000/api/auth/callback`
- Verify redirect URIs in IdP configuration

### Session not persisting
- Check Redis is running: `docker-compose ps redis`
- Verify cookies are enabled in browser
- Check CORS settings in backend

### Frontend can't reach backend
- Verify backend is running: `docker-compose ps backend`
- Check API_BASE_URL in `frontend/src/services/api.js`
- Ensure CORS is configured correctly

## Production Deployment

For production deployment:

1. **Environment Variables**
   - Set `SESSION_COOKIE_SECURE=true` (requires HTTPS)
   - Use strong `SECRET_KEY`
   - Configure proper `ALLOWED_ORIGINS`

2. **Database**
   - Use managed PostgreSQL (RDS, Cloud SQL, etc.)
   - Enable SSL connections
   - Set up backups

3. **Redis**
   - Use managed Redis (ElastiCache, MemoryStore, etc.)
   - Enable persistence
   - Configure high availability

4. **Firebase**
   - Use production Firebase project
   - Secure service account credentials
   - Enable multi-tenant features in Identity Platform

5. **HTTPS**
   - Use reverse proxy (nginx, Caddy)
   - Enable SSL/TLS certificates
   - Set secure cookie flags

## License

MIT

## Support

For issues and questions, please check the troubleshooting section above or review the API documentation at `/docs`.

# Development Roadmap

## ✅ Completed Features (Phases 0-5)

All tenant onboarding phases complete! See [COMPLETED_PHASES.md](./COMPLETED_PHASES.md) for detailed checklist.

**Major Features:**
- ✅ Multi-tenant architecture with SQLAlchemy ORM
- ✅ Automated tenant provisioning CLI
- ✅ Firebase GCIP multi-tenancy integration
- ✅ OIDC provider auto-configuration
- ✅ Email-based activation workflow
- ✅ Self-service tenant activation UI
- ✅ Role-based invitation system
- ✅ Complete documentation

**Current State:**
- Backend: FastAPI + PostgreSQL + SQLAlchemy
- Frontend: React + Firebase SDK
- Auth: Firebase GCIP with OIDC
- Email: Resend API with console fallback
- Testing: Full E2E activation flow verified

---

## 🚧 Known Issues / Technical Debt

*(Add items as you discover them)*

Example:
- [ ] Add database connection pooling configuration
- [ ] Implement API rate limiting
- [ ] Add comprehensive error logging

---

## 📋 Planned Features

### High Priority
- [ ] Admin dashboard for tenant management
- [ ] User invitation flow (non-admin users)
- [ ] Audit logging for security events
- [ ] Multi-factor authentication (MFA)

### Medium Priority
- [ ] Advanced user roles (manager, viewer, etc.)
- [ ] Organization settings page
- [ ] API key management for integrations
- [ ] Usage analytics

### Low Priority / Future
- [ ] Bulk user import
- [ ] Custom branding per tenant
- [ ] SSO with SAML (in addition to OIDC)
- [ ] Mobile app support

---

## 🎯 Next Development Session

**Start your next session with:**
```
"Review docs/ROADMAP.md and docs/development-guide.md. 
I want to add [describe feature]. Check current architecture first."
```

**Before implementing:**
1. Check if similar functionality exists
2. Review database schema in migrations/
3. Look at existing services in backend/app/services/
4. Check frontend components in frontend/src/components/

---

## 📖 Documentation Structure

All documentation is in your repository:

```
docs/
├── COMPLETED_PHASES.md    # Detailed task checklist
├── ROADMAP.md             # This file - planning & features
├── development-guide.md   # Complete dev & testing guide
├── testing-workflow.md    # Testing procedures
└── e2e-activation-test.md # Activation flow testing
```

**Always keep ROADMAP.md updated** as you add features!

---

## 🔍 Architecture Reference

**Database:**
- Migrations: `backend/app/migrations/`
- Models: `backend/app/db_models.py`
- Services: `backend/app/services/`

**API:**
- Routes: `backend/app/routers/`
- Auth middleware: `backend/app/middleware/auth.py`

**Frontend:**
- Components: `frontend/src/components/`
- Services: `frontend/src/services/`
- Firebase: `frontend/src/services/firebaseAuthService.js`

**CLI:**
- Tenant provisioning: `backend/cli/tenant_cli.py`
- Email service: `backend/cli/email_service.py`

---

## 💡 Development Tips

1. **Use the CLI for testing:**
   ```bash
   make reset-db  # Interactive reset + tenant creation
   ```

2. **Check existing patterns:**
   - Service layer for business logic
   - Pydantic models for validation
   - SQLAlchemy ORM for database
   - Dependency injection in FastAPI

3. **Testing workflow:**
   - Backend: Check logs with `make logs`
   - Database: Use `make db-shell` for SQL queries
   - Frontend: Browser dev tools + React DevTools

4. **Documentation:**
   - Update ROADMAP.md when adding features
   - Add to development-guide.md if architectural
   - Keep README.md high-level

---

**Last Updated:** 2025-11-23  
**Current Version:** Phase 5 Complete

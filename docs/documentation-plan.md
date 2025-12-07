# Documentation Plan

This document serves as the **Source of Truth** for the project's documentation structure. All documentation changes must align with this plan to prevent clutter and confusion.

## 🎯 Goal
To provide a clear, role-based navigation path for developers and administrators, ensuring information is easy to find without duplication.

## 🗺️ Documentation Map


### 1. The Entry Point
**File:** `README.md`
- **Audience:** Everyone (New Developers, Evaluators)
- **Purpose:** High-level overview, "What is this?", Key Features, Architecture Summary, and **Links to detailed guides**.
- **Content:**
    - Project Description
    - Key Features
    - Tech Stack (Brief)
    - **Quick Start (Minimal)** - Just enough to get `make up` running.
    - **Navigation** - Links to Development, Platform Admin, and Tenant Admin guides.

### 2. The Developer Track
**File:** `docs/guides/development.md`
- **Audience:** Contributors, Engineers
- **Purpose:** The "Daily Driver" for working on the codebase.
- **Content:**
    - **Setup:** Detailed environment setup (Docker, Node, Python).
    - **Running:** How to start Backend/Frontend.
    - **Testing:** Unit, Integration, E2E workflows (Platform & Tenant).
    - **Debugging:** Common issues, logs, database access.
    - **CLI Tools:** How to use the tenant CLI.
    - **Architecture:** Deep dive into code structure.

### 3. The Platform Admin Track (SaaS Owner)
**File:** `docs/guides/platform-admin.md`
- **Audience:** SaaS Operators, DevOps, Super Admins
- **Purpose:** Managing the SaaS platform itself.
- **Content:**
    - **Setup:** Seeding the platform tenant.
    - **Authentication:** Platform login flow.
    - **Dashboard:** Using the Super Admin Console.
    - **Tenant Management:** creating/suspending tenants.
    - **Monitoring:** Audit logs, system stats.

### 4. The Tenant Admin Track (Customer)
**File:** `docs/guides/tenant-admin.md`
- **Audience:** Customer Administrators (The users of the SaaS)
- **Purpose:** How to use the application.
- **Content:**
    - **Onboarding:** Activation flow.
    - **User Management:** Inviting users, roles.
    - **SSO Setup:** Configuring their IdP.

### 5. The Product/Specification Track
**File:** `docs/specifications/README.md`
- **Audience:** Product Managers, Developers, QA
- **Purpose:** Detailed functional requirements and acceptance criteria.
- **Content:**
    - **Specs:** Broken down by feature (e.g., Onboarding, RBAC).
    - **Source of Truth:** Defines "How it should work" vs "How it is built".

## 🧹 Cleanup Actions
- [x] Rename `docs/guides/admin-guide.md` -> `docs/guides/tenant-admin.md`
- [x] Merge `docs/guides/admin-setup.md` into `docs/guides/tenant-admin.md`
- [x] Simplify `README.md` to remove duplicate "How to" content.
- [x] Ensure `docs/guides/development.md` is the **single source** for testing instructions.
- [x] **Rename & Clarify RBAC:** `guides/rbac.md` -> `guides/rbac-concepts.md` & `architecture/rbac.md` -> `architecture/rbac-implementation.md`.
- [x] **Consolidate Architecture Flows:** Flatten `docs/architecture/flows/` -> `docs/architecture/`.
- [x] **Move Deployment:** `DEPLOYMENT.md` -> `docs/guides/deployment.md`.
- [x] **Move Contributing:** `docs/guides/contributing.md` -> `CONTRIBUTING.md`.

## 📏 Rules
1. **Don't Duplicate:** If it's in `development.md`, link to it from `README.md`. Don't copy-paste.
2. **Role-Based:** Ask "Who is reading this?" before creating a file.
3. **Clean Root:** Only `README.md`, `LICENSE`, `CONTRIBUTING.md` in root. Move everything else to `docs/`.

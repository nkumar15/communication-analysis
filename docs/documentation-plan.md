# Documentation Plan

This document serves as the **Source of Truth** for the project's documentation structure. All documentation changes must align with this plan to prevent clutter and confusion.

## 🎯 Goal
To provide a clear, role-based and product-based navigation path for developers and administrators, ensuring information is easy to find without duplication.

## 🗺️ Documentation Map

### 1. The Entry Point
**File:** `README.md`
- **Audience:** Everyone (New Developers, Evaluators)
- **Purpose:** High-level overview, "What is this?", Key Features, Product Matrix.
- **Content:**
    - Project Description
    - Key Features
    - **Product Matrix** - B2B / B2C / Platform availability
    - **Quick Start (Minimal)** - Just enough to get `make up` running.
    - **Navigation** - Links to guides and product docs.

### 2. The Developer Track
**File:** `docs/guides/development.md`
- **Audience:** Contributors, Engineers
- **Purpose:** The "Daily Driver" for working on the codebase.
- **Content:**
    - Setup, Running, Testing, Debugging, CLI Tools, Architecture

### 3. The Platform Admin Track (SaaS Owner)
**File:** `docs/guides/platform-admin.md`
- **Audience:** SaaS Operators, DevOps, Super Admins
- **Purpose:** Managing the SaaS platform itself.

### 4. The Tenant Admin Track (Customer)
**File:** `docs/guides/b2b-tenant-admin.md`
- **Audience:** Customer Administrators (B2B SaaS users)
- **Purpose:** How B2B tenants use the application.

### 5. The Product/Specification Track
**Directory:** `docs/specifications/`
- **Audience:** Product Managers, Developers, QA
- **Purpose:** Detailed functional requirements and acceptance criteria.
- **Structure:**
    - `specifications/shared/` - Cross-product specs
    - `specifications/b2b/` - B2B-specific specs
    - `specifications/b2c/` - B2C-specific specs

### 6. The Product Track
**Directory:** `docs/products/`
- **Audience:** Product Managers, New Team Members
- **Purpose:** Per-product overview ("What does this product do?")
- **Content:**
    - `products/b2b/README.md` - Enterprise multi-tenant features
    - `products/b2c/README.md` - Personal workspace features
    - `products/platform/README.md` - SaaS administration

### 7. The Architecture Track
**Directory:** `docs/architecture/`
- **Audience:** Engineers, Architects
- **Purpose:** Technical design and system documentation.
- **Structure:**
    - `architecture/shared/` - Cross-product architecture
    - `architecture/b2b/` - B2B-specific architecture
    - `architecture/b2c/` - B2C-specific architecture

## 🧹 Cleanup Actions
- [x] Create `docs/products/` with B2B, B2C, Platform READMEs
- [x] Restructure `docs/architecture/` into shared/b2b/b2c
- [x] Restructure `docs/specifications/` into shared/b2b/b2c
- [x] Add product prefixes to guides (`b2b-tenant-admin.md`, `b2b-rbac-concepts.md`)
- [x] Rename `testing/e2e-activation.md` → `testing/b2b-e2e-activation.md`
- [x] Add `docs/guides/mobile-development.md`

## 📏 Rules
1. **Don't Duplicate:** If it's in `development.md`, link to it from `README.md`. Don't copy-paste.
2. **Role-Based:** Ask "Who is reading this?" before creating a guide.
3. **Product-Based:** Architecture and specs are organized by product (shared/b2b/b2c).
4. **Clean Root:** Only `README.md`, `LICENSE`, `CONTRIBUTING.md` in root.
5. **Prefixes:** Use product prefixes for product-specific files in flat directories.


---
description: Steps to run the full B2B Bank Surveillance test suite with clean DB state.
---

## 1. Start Environment
// turbo
- Start all backend services: `make up`

## 2. Run Bank Surveillance Tests (Full Release Mode)
This command performs a full reset (Drop -> Migrate -> Test) to ensure a clean state. It does NOT use external seeding; tests are self-sufficient.

// turbo
- **Run Full Suite**:
  `make test-b2b-bank-full`

## 3. Run Specific Test Case
Use this to target a single file or test case within the bank surveillance module.

- **Run Specific File**:
  `docker-compose run --rm -e USE_CASE=bank_surveillance e2e-tests pytest tests/e2e_api/b2b/use_cases/bank_surveillance/test_rbac_authorization.py -v`
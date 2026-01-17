"""
Bank Surveillance Use Case Tests

Domain-specific tests for banking surveillance features.
These tests require USE_CASE=bank_surveillance to be set during seeding.

Test Organization:
- test_surveillance_rbac.py: RBAC tests specific to banking roles
- test_surveillance_workflows.py: End-to-end banking workflows
- conftest.py: Banking-specific fixtures

These tests build on top of core platform functionality and test
domain-specific features like:
- Surveillance-specific roles (surveillance_chief, operations_maker, etc.)
- Geographic boundaries and data classification
- Hierarchical team structures
- Banking compliance workflows
"""

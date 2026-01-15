---
name: pytest-tester
description: A skill for creating and running tests using the pytest framework for functional testing of  applications

# My Skill

Detailed instructions for the agent go here

## When to use this skill

- Pre-Implementation(TDD): Use this to define the expected behavior of a function before the actual code is written.
- Validation: Use this to verify that a logic block handles various input types (strings, ints, nulls) correctly.
- Regression Testing: Use this when a bug is found; write a test that fails due to the bug, then fix the code until the test passes.
- Integration Checks: Use this to ensure that different modules of the application work together without side effects.

## How to use it

1. Test Organization
- File Naming: Always prefix test files with test_ (e.g., test_auth.py).
- Class Grouping: Use classes to group tests for the same feature, naming them TestFeatureName.
- Function Naming: Use the pattern test_[function_name]_[scenario]_[expected_outcome] (e.g., test_divide_by_zero_raises_exception).

2. AAA Pattern
Every test must follow this structure for clarity:

- Arrange: Initialize objects, mock dependencies, and prepare input data.
- Act: Execute the specific function or method being tested.
- Assert: Verify the outcome using standard assert statements.

3. Pytest Best Practices
- Use Fixtures: Move setup code (like database connections or API clients) into @pytest.fixture functions to keep tests DRY (Don't Repeat Yourself).
- Parametrization: Instead of writing multiple tests for different inputs, use @pytest.mark.parametrize to run the same logic with a list of values.
- Clean Assertions: Provide descriptive error messages in assertions where logic is complex, e.g., assert result == expected, f"Expected {expected} but got {result}".
- Handle Exceptions: Use with pytest.raises(ErrorType): to explicitly test for expected failures.

4. Mocking and Patching
- When code interacts with external APIs, databases, or the file system, use unittest.mock.patch or the pytest-mock plugin to simulate those interactions. This ensures tests remain fast and deterministic.
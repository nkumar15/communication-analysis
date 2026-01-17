# Task Management Tests

Tests for the task management use case (projects, tasks, comments).

## Use Case Requirements
- USE_CASE=task_management
- No plugins required

## Resources Tested
- projects
- tasks
- comments

## Running
```bash
make test-b2b-task
# or
docker-compose run --rm e2e-tests env USE_CASE=task_management pytest tests/e2e_api/b2b/task_management -v
```

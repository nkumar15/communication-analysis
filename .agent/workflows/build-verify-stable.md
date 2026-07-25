---
description: Build and verify all Docker Compose services, fixing issues until stable.
---

1. Stop existing containers to ensure a clean slate.
   `docker compose down`
   
// turbo
2. Build the Docker images to catch any build-time errors.
   Note: Build processes can be long. Do not timeout if the build is progressing.
   `docker compose build`
   
// turbo
3. Start the services in detached mode.
   `docker compose up -d`
   
4. Verify the status of the containers. Check for 'Exited' or 'Unhealthy' states.
   `docker compose ps -a`

5. If any containers are failing, inspect their logs to identify the issue.
   `docker compose logs <service-name>`
   
6. Fix any identified issues in the code or configuration.

7. Repeat steps 2-6 until all services are running and healthy.

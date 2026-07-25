import random
import uuid
from locust import HttpUser, task, between
from utils import create_mock_firebase_token, encode_mock_jwt

class AuthenticatedUser(HttpUser):
    """Base user that handles mock authentication"""
    abstract = True

    def on_start(self):
        # Use a real user that exists in the DB (from seeding)
        # This ensures b2b_auth.py finds the tenant and user
        self.email = "owner@test-4a2093ce.com"
        self.uid = "firebase-ffa0c62269c54e41a23f5a64d42139ed"
        self.firebase_tenant_id = "tenant-23035e8d"
        
        # Mint token
        token_payload = create_mock_firebase_token(
            uid=self.uid, 
            email=self.email, 
            firebase_tenant_id=self.firebase_tenant_id
        )
        self.token = encode_mock_jwt(token_payload)
        
        # Set auth header for all subsequent requests
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})

class DashboardVisitor(AuthenticatedUser):
    """
    Simulates a standard user checking stats.
    High volume, safe read-only operations.
    """
    weight = 10
    wait_time = between(1, 3)

    @task(3)
    def check_session(self):
        self.client.get("/api/b2b/auth/me", name="Check Session")

    @task(2)
    def view_dashboard_stats(self):
        self.client.get("/api/b2b/dashboard/stats", name="Dashboard Stats")

    @task(1)
    def view_teams_stats(self):
        self.client.get("/api/b2b/teams/stats", name="Teams Stats")

class OrgAdmin(AuthenticatedUser):
    """
    Simulates an admin managing users/roles.
    Medium volume.
    """
    weight = 3
    wait_time = between(2, 5)

    @task(2)
    def list_users(self):
        self.client.get("/api/b2b/users/list", name="List Users")

    @task(1)
    def list_roles(self):
        self.client.get("/api/b2b/roles", name="List Roles")
        
    @task(1)
    def check_billing(self):
        # Allow 404/403 as we haven't seeded specific billing data
        with self.client.get("/api/b2b/billing/subscription", name="Check Subscription", catch_response=True) as response:
            if response.status_code in [404, 403]:
                response.success()

class TeamManager(AuthenticatedUser):
    """
    Simulates creating resources.
    Low volume, write operations.
    """
    weight = 1
    wait_time = between(5, 10)

    @task
    def create_team(self):
        # Create a new team occasionally
        team_name = f"Team {uuid.uuid4().hex[:6]}"
        with self.client.post("/api/b2b/teams/", json={"name": team_name, "description": "Load test team"}, name="Create Team", catch_response=True) as response:
            # 400 is acceptable if name conflict (unlikely with uuid)
            if response.status_code == 400:
                response.success()

from locust import HttpUser, task, between
import uuid
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from load.utils import create_mock_firebase_token, encode_mock_jwt

class StandardUser(HttpUser):
    wait_time = between(1, 5)  # Simulate human think time (1-5 seconds)
    weight = 10
    
    def on_start(self):
        # Use real B2C user (retrieved from DB)
        self.email = "test.billing.10ce2cfb3c2348a595e25f9f71d2b135@example.com"
        self.uid = "fb_10ce2cfb3c2348a595e25f9f71d2b135"
        self.firebase_tenant_id = None # B2C doesn't use tenant ID in token usually, or uses defaults
        
        # Mint token
        token_payload = create_mock_firebase_token(
            uid=self.uid,
            email=self.email,
            firebase_tenant_id=self.firebase_tenant_id
        )
        self.token = encode_mock_jwt(token_payload)
        
        # Set auth header
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    @task(5)
    def check_session(self):
        """High frequency: Verification/Auth check"""
        self.client.get("/api/b2c/auth/me")
        
    @task(3)
    def check_workspaces(self):
        """Medium frequency: Checking workspaces"""
        response = self.client.get("/api/b2c/workspaces")
        if response.status_code == 200:
            data = response.json()
            workspaces = data.get("workspaces", [])
            if workspaces:
                # Pick random or first one to check details
                ws_id = workspaces[0]["id"]
                self.client.get(f"/api/b2c/workspaces/{ws_id}")



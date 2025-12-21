
import json
import base64
import time
from datetime import datetime, timedelta

def get_utc_now():
    return datetime.utcnow()

def create_mock_firebase_token(
    uid: str,
    email: str,
    email_verified: bool = True,
    firebase_tenant_id: str = "test-tenant",
    name: str = None
):
    """Create a mock Firebase JWT token payload"""
    return {
        "uid": uid,
        "email": email,
        "email_verified": email_verified,
        "name": name or email.split("@")[0],
        "firebase": {
            "tenant": firebase_tenant_id,
            "sign_in_provider": "oidc.auth0"
        },
        "iss": "https://securetoken.google.com/test-project",
        "aud": "test-project",
        "auth_time": int(get_utc_now().timestamp()),
        "iat": int(get_utc_now().timestamp()),
        "exp": int((get_utc_now() + timedelta(hours=1)).timestamp()),
    }

def encode_mock_jwt(payload):
    """Create a fake JWT string for testing"""
    header = base64.b64encode(json.dumps({"alg": "mock", "typ": "JWT"}).encode()).decode()
    payload_encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    signature = "mock_signature"
    return f"{header}.{payload_encoded}.{signature}"

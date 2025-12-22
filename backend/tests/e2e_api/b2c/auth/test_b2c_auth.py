"""E2E Tests for B2C Authentication"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from uuid import uuid4

from tests.conftest import create_b2c_user, create_b2c_workspace, create_b2c_mock_token, encode_mock_jwt


@pytest.mark.asyncio
async def test_signup_creates_user_and_workspace(api_client: AsyncClient, db_session):
    """Test signup creates user + personal workspace"""
    
    email = f"newuser-{uuid4().hex[:8]}@b2c.test"
    firebase_uid = f"firebase-{uuid4().hex[:12]}"
    mock_token_data = create_b2c_mock_token(firebase_uid, email, email_verified=True)
    
    # Mock Firebase token verification
    with patch('infrastructure.auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=mock_token_data)):
        response = await api_client.post(
            "/api/b2c/auth/signup",
            json={
                "id_token": "mock_firebase_token",
                "display_name": "Test User"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify user created
    assert "user" in data
    assert data["user"]["email"] == email
    assert data["user"]["display_name"] == "Test User"
    assert "id" in data["user"]
    assert "personal_workspace_id" in data["user"]
    
    # Verify workspace created
    assert "workspace" in data
    assert data["workspace"]["type"] == "personal"
    assert "Test User's Workspace" in data["workspace"]["name"]
    
    # Verify IDs match
    assert data["user"]["personal_workspace_id"] == data["workspace"]["id"]


@pytest.mark.asyncio
async def test_signup_requires_verified_email(api_client: AsyncClient, db_session):
    """Test signup rejects unverified emails"""
    
    email = f"unverified-{uuid4().hex[:8]}@b2c.test"
    firebase_uid = f"firebase-{uuid4().hex[:12]}"
    mock_token_data = create_b2c_mock_token(firebase_uid, email, email_verified=False)
    
    with patch('infrastructure.auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=mock_token_data)):
        response = await api_client.post(
            "/api/b2c/auth/signup",
            json={"id_token": "mock_token"}
        )
    
    assert response.status_code == 403
    assert "verified" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_signup_prevents_duplicate_users(api_client: AsyncClient, db_session):
    """Test signup rejects duplicate firebase_uid or email"""
    
    # Create existing user
    existing_email = f"existing-{uuid4().hex[:8]}@b2c.test"
    existing_uid = f"firebase-{uuid4().hex[:12]}"
    await create_b2c_user(db_session, existing_email, existing_uid)
    await db_session.commit()
    
    # Try to signup with same email
    mock_token_data = create_b2c_mock_token(existing_uid, existing_email, email_verified=True)
    
    with patch('infrastructure.auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=mock_token_data)):
        response = await api_client.post(
            "/api/b2c/auth/signup",
            json={"id_token": "mock_token"}
        )
    
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_existing_user(api_client: AsyncClient, db_session):
    """Test login for existing user returns workspaces"""
    
    # Create user + workspace
    email = f"loginuser-{uuid4().hex[:8]}@b2c.test"
    firebase_uid = f"firebase-{uuid4().hex[:12]}"
    user = await create_b2c_user(db_session, email, firebase_uid, "Login User")
    workspace = await create_b2c_workspace(db_session, user.id, "Login's Workspace", 'personal')
    user.default_workspace_id = workspace.id
    await db_session.commit()
    
    # Login
    mock_token_data = create_b2c_mock_token(firebase_uid, email, email_verified=True)
    
    with patch('infrastructure.auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=mock_token_data)):
        response = await api_client.post(
            "/api/b2c/auth/login",
            json={"id_token": "mock_token"}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["user"]["email"] == email
    assert len(data["workspaces"]) == 1
    assert data["workspaces"][0]["type"] == "personal"


@pytest.mark.asyncio
async def test_login_creates_user_on_first_time(api_client: AsyncClient, db_session):
    """Test login auto-creates user on first Google login"""
    
    email = f"firsttime-{uuid4().hex[:8]}@b2c.test"
    firebase_uid = f"firebase-{uuid4().hex[:12]}"
    mock_token_data = create_b2c_mock_token(firebase_uid, email, email_verified=True)
    
    with patch('infrastructure.auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=mock_token_data)):
        response = await api_client.post(
            "/api/b2c/auth/login",
            json={"id_token": "mock_token"}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # User created
    assert data["user"]["email"] == email
    
    # Workspace created
    assert len(data["workspaces"]) == 1
    assert data["workspaces"][0]["type"] == "personal"


@pytest.mark.asyncio
async def test_get_me_requires_auth(api_client: AsyncClient):
    """Test /me requires authentication"""
    
    response = await api_client.get("/api/b2c/auth/me")
    assert response.status_code == 401  # HTTPBearer returns 401 when missing auth


@pytest.mark.asyncio
async def test_get_me_returns_user_info(api_client: AsyncClient, db_session):
    """Test /me returns user info with workspaces"""
    
    # Create user + workspace
    email = f"meuser-{uuid4().hex[:8]}@b2c.test"
    firebase_uid = f"firebase-{uuid4().hex[:12]}"
    user = await create_b2c_user(db_session, email, firebase_uid, "Me User")
    workspace = await create_b2c_workspace(db_session, user.id, "Me's Workspace", 'personal')
    user.default_workspace_id = workspace.id
    await db_session.commit()
    
    # Create token
    mock_token_data = create_b2c_mock_token(firebase_uid, email)
    id_token = encode_mock_jwt(mock_token_data)
    
    # Mock Firebase verification in middleware
    with patch('modules.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=mock_token_data)):
        response = await api_client.get(
            "/api/b2c/auth/me",
            headers={"Authorization": f"Bearer {id_token}"}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["email"] == email
    assert data["display_name"] == "Me User"
    assert len(data["workspaces"]) == 1
    assert data["workspaces"][0]["name"] == "Me's Workspace"


@pytest.mark.asyncio
async def test_get_me_rejects_deleted_user(api_client: AsyncClient, db_session):
    """Test /me rejects deleted users"""
    
    from datetime import datetime, timezone
    
    # Create deleted user
    email = f"deleted-{uuid4().hex[:8]}@b2c.test"
    firebase_uid = f"firebase-{uuid4().hex[:12]}"
    user = await create_b2c_user(db_session, email, firebase_uid)
    user.deleted_at = datetime.now(timezone.utc)
    await db_session.commit()
    
    # Verify persistence
    from sqlalchemy import select, text
    from modules.b2c.models.user import B2CUser
    # Set context again because commit() clears LOCAL variables
    await db_session.execute(text(f"SET LOCAL app.current_user_id = '{user.id}'"))
    chk = await db_session.execute(select(B2CUser).where(B2CUser.id == user.id))
    u = chk.scalar_one()
    print(f"DEBUG IN TEST: user.deleted_at = {u.deleted_at}")
    print(f"DEBUG IN TEST: user.deleted_at type = {type(u.deleted_at)}")
    
    # Try to access /me
    mock_token_data = create_b2c_mock_token(firebase_uid, email)
    id_token = encode_mock_jwt(mock_token_data)
    
    with patch('modules.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=mock_token_data)):
        response = await api_client.get(
            "/api/b2c/auth/me",
            headers={"Authorization": f"Bearer {id_token}"}
        )
        print(f"DEBUG RESPONSE: {response.status_code} {response.json()}")
    
    assert response.status_code == 404  # User not found after deletion
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_rls_context_set_for_b2c_user(api_client: AsyncClient, db_session):
    """Test RLS context is set for B2C users"""
    
    email = f"rlsuser-{uuid4().hex[:8]}@b2c.test"
    firebase_uid = f"firebase-{uuid4().hex[:12]}"
    user = await create_b2c_user(db_session, email, firebase_uid)
    workspace = await create_b2c_workspace(db_session, user.id, "RLS Workspace", 'personal')
    await db_session.commit()
    
    # Call /me which sets RLS context
    mock_token_data = create_b2c_mock_token(firebase_uid, email)
    id_token = encode_mock_jwt(mock_token_data)
    
    with patch('modules.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=mock_token_data)):
        response = await api_client.get(
            "/api/b2c/auth/me",
            headers={"Authorization": f"Bearer {id_token}"}
        )
    
    assert response.status_code == 200
    # If RLS wasn't set, we'd get errors or empty results

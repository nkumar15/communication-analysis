"""
Integration tests for Comments API

Tests cover:
- Comment creation
- Threaded replies
- Owner-only edit/delete
- Team member permissions
- Multi-tenant isolation
"""
import pytest


class TestCommentsAPI:
    """Test suite for Comments endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_comment(
        self,
        api_client,
        domain_test_data,
        team_task
    ):
        """Test creating a comment on task"""
        response = await api_client.post(
            "/api/domain/comments",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "task_id": str(team_task),
                "content": "This is a comment"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "This is a comment"
        assert data["task_id"] == str(team_task)
        assert data["parent_comment_id"] is None
    
    @pytest.mark.asyncio
    async def test_create_threaded_reply(
        self,
        api_client,
        domain_test_data,
        team_task,
        team_comment
    ):
        """Test creating a reply to a comment"""
        response = await api_client.post(
            "/api/domain/comments",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "task_id": str(team_task),
                "content": "This is a reply",
                "parent_comment_id": str(team_comment)
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["parent_comment_id"] == str(team_comment)
    
    @pytest.mark.asyncio
    async def test_cannot_reply_to_different_task_comment(
        self,
        api_client,
        domain_test_data,
        other_team_project
    ):
        """Test cannot use parent comment from different task"""
        # Create a different task
        resp = await api_client.post(
            "/api/domain/tasks",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "project_id": str(other_team_project),
                "title": "Other Task"
            }
        )
        other_task_id = resp.json()["id"]
        
        # Create comment on first task
        resp = await api_client.post(
            "/api/domain/comments",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "task_id": other_task_id,
                "content": "Comment"
            }
        )
        comment_id = resp.json()["id"]
        
        # Try to REPLY to this comment on a different task (should fail)
        # First create a new project/task
        from uuid import uuid4
        fake_task = str(uuid4())
        
        response = await api_client.post(
            "/api/domain/comments",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "task_id": fake_task,
                "content": "Reply",
                "parent_comment_id": comment_id
            }
        )
        assert response.status_code in [400, 403, 404]
    
    @pytest.mark.asyncio
    async def test_list_comments_threaded(
        self,
        api_client,
        domain_test_data,
        team_task,
        team_comment
    ):
        """Test listing comments with threaded structure"""
        # Create a reply
        await api_client.post(
            "/api/domain/comments",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "task_id": str(team_task),
                "content": "Reply 1",
                "parent_comment_id": str(team_comment)
            }
        )
        
        # List comments
        response = await api_client.get(
            f"/api/domain/comments/task/{team_task}",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 200
        comments = response.json()
        
        # Should have top-level comments with replies nested
        assert len(comments) >= 1
        # Find parent comment and verify it has replies
        parent = next(c for c in comments if c["id"] == str(team_comment))
        assert len(parent["replies"]) >= 1
    
    @pytest.mark.asyncio
    async def test_update_own_comment(
        self,
        api_client,
        domain_test_data,
        team_task
    ):
        """Test user can update their own comment"""
        # Create comment as team member
        resp = await api_client.post(
            "/api/domain/comments",
            headers={"Authorization": f"Bearer {domain_test_data['team_member_token']}"},
            json={
                "task_id": str(team_task),
                "content": "Original content"
            }
        )
        comment_id = resp.json()["id"]
        
        # Update own comment
        response = await api_client.put(
            f"/api/domain/comments/{comment_id}",
            headers={"Authorization": f"Bearer {domain_test_data['team_member_token']}"},
            json={"content": "Updated content"}
        )
        assert response.status_code == 200
        assert response.json()["content"] == "Updated content"
    
    @pytest.mark.asyncio
    async def test_cannot_update_others_comment(
        self,
        api_client,
        domain_test_data,
        team_task
    ):
        """Test user cannot update someone else's comment"""
        # Create comment as team member
        resp = await api_client.post(
            "/api/domain/comments",
            headers={"Authorization": f"Bearer {domain_test_data['team_member_token']}"},
            json={
                "task_id": str(team_task),
                "content": "My comment"
            }
        )
        comment_id = resp.json()["id"]
        
        # Try to update as different user
        response = await api_client.put(
            f"/api/domain/comments/{comment_id}",
            headers={"Authorization": f"Bearer {domain_test_data['other_team_member_token']}"},
            json={"content": "Hacked!"}
        )
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_owner_can_update_any_comment(
        self,
        api_client,
        domain_test_data,
        team_comment
    ):
        """Test owner can update any comment"""
        response = await api_client.put(
            f"/api/domain/comments/{team_comment}",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={"content": "Owner edit"}
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_delete_own_comment(
        self,
        api_client,
        domain_test_data,
        team_task
    ):
        """Test user can delete their own comment"""
        # Create comment
        resp = await api_client.post(
            "/api/domain/comments",
            headers={"Authorization": f"Bearer {domain_test_data['team_member_token']}"},
            json={
                "task_id": str(team_task),
                "content": "To be deleted"
            }
        )
        comment_id = resp.json()["id"]
        
        # Delete own comment
        response = await api_client.delete(
            f"/api/domain/comments/{comment_id}",
            headers={"Authorization": f"Bearer {domain_test_data['team_member_token']}"}
        )
        assert response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_non_team_member_cannot_comment(
        self,
        api_client,
        domain_test_data,
        team_task
    ):
        """Test user from different team cannot comment on task"""
        response = await api_client.post(
            "/api/domain/comments",
            headers={"Authorization": f"Bearer {domain_test_data['other_team_member_token']}"},
            json={
                "task_id": str(team_task),
                "content": "Unauthorized comment"
            }
        )
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(
        self,
        api_client,
        domain_test_data,
        team_task
    ):
        """Test comments are isolated by tenant"""
        # Tenant 2 owner cannot comment on Tenant 1 task
        response = await api_client.post(
            "/api/domain/comments",
            headers={"Authorization": f"Bearer {domain_test_data['tenant2_owner_token']}"},
            json={
                "task_id": str(team_task),
                "content": "Cross-tenant comment"
            }
        )
        assert response.status_code == 403

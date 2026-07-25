"""
Integration tests for Tasks API

Tests cover:
- CRUD operations  
- Project relationship
- Status transitions
- Team member assignment
- Multi-tenant isolation
"""
import pytest
from uuid import uuid4


@pytest.mark.skip(reason="Requires domain-specific fixtures not currently in foundation scope")
class TestTasksAPI:
    """Test suite for Tasks endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_task(self, api_client, domain_test_data, team_project):
        """Test creating a task"""
        response = await api_client.post(
            "/api/domain/tasks",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "project_id": str(team_project),
                "title": "New Task",
                "description": "Task description"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Task"
        assert data["status"] == "todo"
    
    @pytest.mark.asyncio
    async def test_create_task_with_assignment(
        self,
        api_client,
        domain_test_data,
        team_project
    ):
        """Test creating task with team member assignment"""
        response = await api_client.post(
            "/api/domain/tasks",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "project_id": str(team_project),
                "title": "Assigned Task",
                "assigned_to": str(domain_test_data['team_member'].id)
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["assigned_to"] == str(domain_test_data['team_member'].id)
    
    @pytest.mark.asyncio
    async def test_cannot_assign_non_team_member(
        self,
        api_client,
        domain_test_data,
        team_project
    ):
        """Test cannot assign task to non-team member"""
        response = await api_client.post(
            "/api/domain/tasks",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "project_id": str(team_project),
                "title": "Task",
                "assigned_to": str(domain_test_data['other_team_member'].id)
            }
        )
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_list_tasks_by_project(
        self,
        api_client,
        domain_test_data,
        team_project,
        team_task
    ):
        """Test filtering tasks by project"""
        response = await api_client.get(
            f"/api/domain/tasks?project_id={team_project}",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) >= 1
        assert all(t["project_id"] == str(team_project) for t in tasks)
    
    @pytest.mark.asyncio
    async def test_list_tasks_by_status(
        self,
        api_client,
        domain_test_data,
        team_task
    ):
        """Test filtering tasks by status"""
        response = await api_client.get(
            "/api/domain/tasks?status=todo",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 200
        tasks = response.json()
        assert all(t["status"] == "todo" for t in tasks)
    
    @pytest.mark.asyncio
    async def test_get_task(self, api_client, domain_test_data, team_task):
        """Test getting specific task"""
        response = await api_client.get(
            f"/api/domain/tasks/{team_task}",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(team_task)
    
    @pytest.mark.asyncio
    async def test_update_task(self, api_client, domain_test_data, team_task):
        """Test updating task details"""
        response = await api_client.put(
            f"/api/domain/tasks/{team_task}",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={"title": "Updated Title"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
    
    @pytest.mark.asyncio
    async def test_update_task_status_via_patch(
        self,
        api_client,
        domain_test_data,
        team_task
    ):
        """Test status transition via PATCH endpoint"""
        # todo -> in_progress
        response = await api_client.patch(
            f"/api/domain/tasks/{team_task}/status?status=in_progress",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"
        
        # in_progress -> done
        response = await api_client.patch(
            f"/api/domain/tasks/{team_task}/status?status=done",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "done"
    
    @pytest.mark.asyncio
    async def test_delete_task(self, api_client, domain_test_data, team_task):
        """Test deleting a task"""
        response = await api_client.delete(
            f"/api/domain/tasks/{team_task}",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_non_team_member_cannot_access_task(
        self,
        api_client,
        domain_test_data,
        team_task
    ):
        """Test user from different team cannot access task"""
        response = await api_client.get(
            f"/api/domain/tasks/{team_task}",
            headers={"Authorization": f"Bearer {domain_test_data['other_team_member_token']}"}
        )
        assert response.status_code == 403

    
    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(
        self,
        api_client,
        domain_test_data,
        team_task
    ):
        """Test tasks are isolated by tenant"""
        response = await api_client.get(
            f"/api/domain/tasks/{team_task}",
            headers={"Authorization": f"Bearer {domain_test_data['tenant2_owner_token']}"}
        )
        assert response.status_code == 403


@pytest.mark.skip(reason="Requires domain-specific fixtures not currently in foundation scope")
class TestTasksViewerRestrictions:
    """Test that Viewer role cannot perform write operations"""
    
    @pytest.mark.asyncio
    async def test_viewer_cannot_create_task(
        self, api_client, domain_test_data, team_project
    ):
        """Viewer should get 403 when trying to create a task"""
        response = await api_client.post(
            "/api/domain/tasks",
            headers={"Authorization": f"Bearer {domain_test_data['viewer_token']}"},
            json={
                "project_id": str(team_project),
                "title": "Viewer Task"
            }
        )
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_viewer_cannot_update_task(
        self, api_client, domain_test_data, team_task
    ):
        """Viewer should get 403 when trying to update a task"""
        response = await api_client.put(
            f"/api/domain/tasks/{team_task}",
            headers={"Authorization": f"Bearer {domain_test_data['viewer_token']}"},
            json={"title": "Hacked Title"}
        )
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_viewer_cannot_delete_task(
        self, api_client, domain_test_data, team_task
    ):
        """Viewer should get 403 when trying to delete a task"""
        response = await api_client.delete(
            f"/api/domain/tasks/{team_task}",
            headers={"Authorization": f"Bearer {domain_test_data['viewer_token']}"}
        )
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_viewer_cannot_change_task_status(
        self, api_client, domain_test_data, team_task
    ):
        """Viewer should get 403 when trying to change task status"""
        response = await api_client.patch(
            f"/api/domain/tasks/{team_task}/status?status=in_progress",
            headers={"Authorization": f"Bearer {domain_test_data['viewer_token']}"}
        )
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_viewer_can_read_task(
        self, api_client, domain_test_data, team_task
    ):
        """Viewer should be able to read tasks in their team's projects"""
        response = await api_client.get(
            f"/api/domain/tasks/{team_task}",
            headers={"Authorization": f"Bearer {domain_test_data['viewer_token']}"}
        )
        assert response.status_code == 200


@pytest.mark.skip(reason="Requires domain-specific fixtures not currently in foundation scope")
class TestTasksStatusTransitions:
    """Test valid and invalid status transitions"""
    
    @pytest.mark.asyncio
    async def test_invalid_status_value(
        self, api_client, domain_test_data, team_task
    ):
        """Test that invalid status value is rejected"""
        response = await api_client.patch(
            f"/api/domain/tasks/{team_task}/status?status=invalid_status",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 422


@pytest.mark.skip(reason="Requires domain-specific fixtures not currently in foundation scope")
class TestTasksValidation:
    """Test input validation for Tasks API"""
    
    @pytest.mark.asyncio
    async def test_create_task_empty_title(
        self, api_client, domain_test_data, team_project
    ):
        """Test that empty task title is rejected"""
        response = await api_client.post(
            "/api/domain/tasks",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "project_id": str(team_project),
                "title": ""
            }
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_task_missing_project_id(
        self, api_client, domain_test_data
    ):
        """Test that missing project_id is rejected"""
        response = await api_client.post(
            "/api/domain/tasks",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "title": "Task Without Project"
            }
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_task_invalid_project_id(
        self, api_client, domain_test_data
    ):
        """Test that invalid project_id format is rejected"""
        response = await api_client.post(
            "/api/domain/tasks",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "project_id": "not-a-uuid",
                "title": "Task"
            }
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_task_nonexistent_project(
        self, api_client, domain_test_data
    ):
        """Test task creation with non-existent project fails"""
        response = await api_client.post(
            "/api/domain/tasks",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "project_id": str(uuid4()),
                "title": "Task"
            }
        )
        assert response.status_code in [403, 404]

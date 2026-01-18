/**
 * API Client for Projects
 */
import firebaseAuthService from '../firebase/authService';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const getAuthHeaders = async () => {
    const token = await firebaseAuthService.getIdToken();
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
};

export const projectsApi = {
    async list() {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/task_management/projects`, { headers });
        if (!response.ok) throw new Error('Failed to fetch projects');
        return response.json();
    },

    async get(projectId) {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/task_management/projects/${projectId}`, { headers });
        if (!response.ok) throw new Error('Failed to fetch project');
        return response.json();
    },

    async create(data) {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/task_management/projects`, {
            method: 'POST',
            headers,
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Failed to create project');
        return response.json();
    },

    async update(projectId, data) {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/task_management/projects/${projectId}`, {
            method: 'PUT',
            headers,
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Failed to update project');
        return response.json();
    },

    async delete(projectId) {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/task_management/projects/${projectId}`, {
            method: 'DELETE',
            headers
        });
        if (!response.ok) throw new Error('Failed to delete project');
    }
};

export const tasksApi = {
    async list(filters = {}) {
        const headers = await getAuthHeaders();
        const params = new URLSearchParams();
        if (filters.project_id) params.append('project_id', filters.project_id);
        if (filters.status) params.append('status', filters.status);

        const url = `${API_BASE_URL}/api/b2b/domain/task_management/tasks${params.toString() ? '?' + params.toString() : ''}`;
        const response = await fetch(url, { headers });
        if (!response.ok) throw new Error('Failed to fetch tasks');
        return response.json();
    },

    async get(taskId) {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/task_management/tasks/${taskId}`, { headers });
        if (!response.ok) throw new Error('Failed to fetch task');
        return response.json();
    },

    async create(data) {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/task_management/tasks`, {
            method: 'POST',
            headers,
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Failed to create task');
        return response.json();
    },

    async update(taskId, data) {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/task_management/tasks/${taskId}`, {
            method: 'PUT',
            headers,
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Failed to update task');
        return response.json();
    },

    async updateStatus(taskId, status) {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/task_management/tasks/${taskId}/status?status=${status}`, {
            method: 'PATCH',
            headers
        });
        if (!response.ok) throw new Error('Failed to update task status');
        return response.json();
    },

    async delete(taskId) {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/task_management/tasks/${taskId}`, {
            method: 'DELETE',
            headers
        });
        if (!response.ok) throw new Error('Failed to delete task');
    }
};

export const commentsApi = {
    async listForTask(taskId) {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/task_management/comments/task/${taskId}`, { headers });
        if (!response.ok) throw new Error('Failed to fetch comments');
        return response.json();
    },

    async create(data) {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/task_management/comments`, {
            method: 'POST',
            headers,
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Failed to create comment');
        return response.json();
    },

    async update(commentId, data) {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/task_management/comments/${commentId}`, {
            method: 'PUT',
            headers,
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Failed to update comment');
        return response.json();
    },

    async delete(commentId) {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/task_management/comments/${commentId}`, {
            method: 'DELETE',
            headers
        });
        if (!response.ok) throw new Error('Failed to delete comment');
    }
};


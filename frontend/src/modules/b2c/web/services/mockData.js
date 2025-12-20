// Mock data for B2C development
// This will be replaced with real API calls later

export const mockWorkspaces = [
    {
        id: 'ws-1',
        name: 'Personal Workspace',
        description: 'My personal projects and tasks',
        type: 'personal',
        role: 'owner',
        member_count: 1,
        project_count: 3,
        created_at: '2024-01-15T10:00:00Z'
    },
    {
        id: 'ws-2',
        name: 'Team Alpha',
        description: 'Collaborative workspace for Team Alpha projects',
        type: 'team',
        role: 'admin',
        member_count: 5,
        project_count: 7,
        created_at: '2024-02-20T14:30:00Z'
    },
    {
        id: 'ws-3',
        name: 'Marketing Projects',
        description: 'Marketing campaigns and content planning',
        type: 'team',
        role: 'member',
        member_count: 8,
        project_count: 4,
        created_at: '2024-03-10T09:15:00Z'
    }
];

export const mockProjects = {
    'ws-1': [
        {
            id: 'proj-1',
            name: 'Website Redesign',
            description: 'Redesign company website with modern UI',
            status: 'in_progress',
            progress: 65,
            due_date: '2024-12-31',
            task_count: 12,
            completed_tasks: 8
        },
        {
            id: 'proj-2',
            name: 'Mobile App',
            description: 'Build iOS and Android applications',
            status: 'planning',
            progress: 15,
            due_date: '2025-03-15',
            task_count: 24,
            completed_tasks: 3
        }
    ],
    'ws-2': [
        {
            id: 'proj-3',
            name: 'Q4 Campaign',
            description: 'Launch major marketing campaign for Q4',
            status: 'in_progress',
            progress: 45,
            due_date: '2024-12-15',
            task_count: 18,
            completed_tasks: 8
        }
    ]
};

export const mockTasks = {
    'proj-1': [
        {
            id: 'task-1',
            title: 'Design homepage mockup',
            description: 'Create modern homepage design in Figma',
            status: 'completed',
            priority: 'high',
            assignee: 'John Doe',
            due_date: '2024-11-20'
        },
        {
            id: 'task-2',
            title: 'Set up React project',
            description: 'Initialize React app with TypeScript',
            status: 'completed',
            priority: 'high',
            assignee: 'Jane Smith',
            due_date: '2024-11-22'
        },
        {
            id: 'task-3',
            title: 'Implement navigation',
            description: 'Build responsive navigation component',
            status: 'in_progress',
            priority: 'medium',
            assignee: 'John Doe',
            due_date: '2024-12-05'
        }
    ]
};

// Mock API delay to simulate network
const delay = (ms = 300) => new Promise(resolve => setTimeout(resolve, ms));

// Mock API client
export const mockApi = {
    // Workspaces
    async getWorkspaces() {
        await delay();
        return mockWorkspaces;
    },

    async getWorkspace(id) {
        await delay();
        const workspace = mockWorkspaces.find(w => w.id === id);
        if (!workspace) throw new Error('Workspace not found');
        return {
            ...workspace,
            projects: mockProjects[id] || []
        };
    },

    async createWorkspace(data) {
        await delay();
        const newWorkspace = {
            id: `ws-${Date.now()}`,
            ...data,
            member_count: 1,
            project_count: 0,
            created_at: new Date().toISOString()
        };
        mockWorkspaces.push(newWorkspace);
        return newWorkspace;
    },

    async updateWorkspace(id, data) {
        await delay();
        const index = mockWorkspaces.findIndex(w => w.id === id);
        if (index === -1) throw new Error('Workspace not found');
        mockWorkspaces[index] = { ...mockWorkspaces[index], ...data };
        return mockWorkspaces[index];
    },

    async deleteWorkspace(id) {
        await delay();
        const index = mockWorkspaces.findIndex(w => w.id === id);
        if (index === -1) throw new Error('Workspace not found');
        mockWorkspaces.splice(index, 1);
        return { success: true };
    },

    // Projects
    async getProjects(workspaceId) {
        await delay();
        return mockProjects[workspaceId] || [];
    },

    async createProject(workspaceId, data) {
        await delay();
        const newProject = {
            id: `proj-${Date.now()}`,
            ...data,
            status: 'planning',
            progress: 0,
            task_count: 0,
            completed_tasks: 0
        };
        if (!mockProjects[workspaceId]) {
            mockProjects[workspaceId] = [];
        }
        mockProjects[workspaceId].push(newProject);
        return newProject;
    },

    // Tasks
    async getTasks(projectId) {
        await delay();
        return mockTasks[projectId] || [];
    },

    async createTask(projectId, data) {
        await delay();
        const newTask = {
            id: `task-${Date.now()}`,
            ...data,
            status: 'todo'
        };
        if (!mockTasks[projectId]) {
            mockTasks[projectId] = [];
        }
        mockTasks[projectId].push(newTask);
        return newTask;
    }
};

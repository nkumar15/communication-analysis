// Mock data for Bank Surveillance demo pages

export const MOCK_KPIS = {
    totalCommunications: 15420,
    flaggedItems: 127,
    openInvestigations: 8,
    complianceScore: 94.2,
    alertsToday: 12
};

export const MOCK_COMMUNICATIONS = [
    {
        id: 'COM-001',
        type: 'email',
        from: 'trader.amer@worldwidebank.com',
        to: 'broker.ext@hedgefund.com',
        subject: 'Q4 Position Discussion',
        date: '2024-01-10T09:23:00Z',
        sensitivity: 'CONFIDENTIAL',
        status: 'flagged',
        region: 'AMER'
    },
    {
        id: 'COM-002',
        type: 'chat',
        from: 'analyst.apac@worldwidebank.com',
        to: 'manager.apac@worldwidebank.com',
        subject: 'Market Alert - APAC Session',
        date: '2024-01-10T08:15:00Z',
        sensitivity: 'INTERNAL',
        status: 'reviewed',
        region: 'APAC'
    },
    {
        id: 'COM-003',
        type: 'email',
        from: 'compliance.emea@worldwidebank.com',
        to: 'legal@worldwidebank.com',
        subject: 'FCA Reporting Requirements',
        date: '2024-01-09T14:30:00Z',
        sensitivity: 'RESTRICTED',
        status: 'pending',
        region: 'EMEA'
    },
    {
        id: 'COM-004',
        type: 'voice',
        from: 'desk.amer@worldwidebank.com',
        to: 'client.ext@investment.com',
        subject: 'Voice Recording - Trade Execution',
        date: '2024-01-09T11:45:00Z',
        sensitivity: 'CONFIDENTIAL',
        status: 'flagged',
        region: 'AMER'
    },
    {
        id: 'COM-005',
        type: 'email',
        from: 'research.apac@worldwidebank.com',
        to: 'team.apac@worldwidebank.com',
        subject: 'Weekly Market Summary',
        date: '2024-01-08T16:00:00Z',
        sensitivity: 'INTERNAL',
        status: 'cleared',
        region: 'APAC'
    }
];

export const MOCK_INVESTIGATIONS = [
    {
        id: 'INV-2024-001',
        title: 'Potential Front-Running - AMER Desk',
        status: 'open',
        priority: 'high',
        assignee: 'Sarah Johnson',
        region: 'AMER',
        createdAt: '2024-01-08',
        communicationsCount: 23
    },
    {
        id: 'INV-2024-002',
        title: 'Information Barrier Breach Review',
        status: 'under_review',
        priority: 'critical',
        assignee: 'James Chen',
        region: 'APAC',
        createdAt: '2024-01-05',
        communicationsCount: 47
    },
    {
        id: 'INV-2023-089',
        title: 'Gifts & Entertainment Policy Violation',
        status: 'closed',
        priority: 'medium',
        assignee: 'Maria Garcia',
        region: 'EMEA',
        createdAt: '2023-12-15',
        communicationsCount: 8
    },
    {
        id: 'INV-2024-003',
        title: 'Unusual Trading Pattern Analysis',
        status: 'open',
        priority: 'medium',
        assignee: 'David Kim',
        region: 'APAC',
        createdAt: '2024-01-09',
        communicationsCount: 15
    }
];

export const STATUS_COLORS = {
    flagged: '#EF4444',
    pending: '#F59E0B',
    reviewed: '#3B82F6',
    cleared: '#10B981',
    open: '#F59E0B',
    under_review: '#3B82F6',
    closed: '#6B7280'
};

export const PRIORITY_COLORS = {
    critical: '#DC2626',
    high: '#F59E0B',
    medium: '#3B82F6',
    low: '#10B981'
};

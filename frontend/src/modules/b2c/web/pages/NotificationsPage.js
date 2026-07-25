import React from 'react';
import B2CLayout from '../layouts/B2CLayout';
import EmptyState from '../components/EmptyState';

const NotificationsPage = () => {
    return (
        <B2CLayout>
            <div style={{ maxWidth: '800px', margin: '0 auto' }}>
                <h1 style={{
                    fontSize: '32px',
                    fontWeight: '700',
                    color: '#111827',
                    marginBottom: '8px'
                }}>
                    Notifications
                </h1>
                <p style={{
                    fontSize: '16px',
                    color: '#6B7280',
                    marginBottom: '32px'
                }}>
                    Stay updated with your workspace activity
                </p>

                <EmptyState
                    icon="🔔"
                    title="No notifications yet"
                    description="You'll see notifications here when there's activity in your workspaces"
                />
            </div>
        </B2CLayout>
    );
};

export default NotificationsPage;

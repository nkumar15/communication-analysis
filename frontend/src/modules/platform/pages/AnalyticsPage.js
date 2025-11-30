import React from 'react';

function AnalyticsPage() {
    return (
        <div>
            <div className="platform-page-header">
                <h1 className="platform-page-title">Platform Analytics</h1>
            </div>

            <div className="platform-card">
                <div style={{ textAlign: 'center', padding: '3rem 0' }}>
                    <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📈</div>
                    <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '0.5rem', color: '#1f2937' }}>Analytics Coming Soon</h2>
                    <p style={{ color: '#6b7280' }}>Detailed platform usage statistics and growth metrics will be available here.</p>
                </div>
            </div>
        </div>
    );
}

export default AnalyticsPage;

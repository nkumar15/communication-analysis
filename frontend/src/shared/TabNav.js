import React from 'react';

const TabNav = ({ tabs, activeTab, onTabChange }) => {
    return (
        <div style={{
            borderBottom: '2px solid #E5E7EB',
            marginBottom: '24px'
        }}>
            <div style={{
                display: 'flex',
                gap: '32px'
            }}>
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => onTabChange(tab.id)}
                        style={{
                            padding: '12px 4px',
                            backgroundColor: 'transparent',
                            border: 'none',
                            borderBottom: activeTab === tab.id ? '2px solid #4F46E5' : '2px solid transparent',
                            color: activeTab === tab.id ? '#4F46E5' : '#6B7280',
                            fontWeight: activeTab === tab.id ? '600' : '500',
                            fontSize: '15px',
                            cursor: 'pointer',
                            marginBottom: '-2px',
                            transition: 'all 0.2s'
                        }}
                    >
                        {tab.label}
                        {tab.count !== undefined && (
                            <span style={{
                                marginLeft: '8px',
                                padding: '2px 8px',
                                borderRadius: '10px',
                                backgroundColor: activeTab === tab.id ? '#EEF2FF' : '#F3F4F6',
                                fontSize: '13px',
                                fontWeight: '600'
                            }}>
                                {tab.count}
                            </span>
                        )}
                    </button>
                ))}
            </div>
        </div>
    );
};

export default TabNav;

import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Image, ActivityIndicator } from 'react-native';

/**
 * Mobile Dashboard Screen
 * 
 * Displays:
 * 1. Profile Widget (User Info + Logout)
 * 2. Skeletal Stats (Placeholder)
 * 3. Quick Actions
 */
export default function DashboardScreen({ userData, onLogout }) {
    const [loggingOut, setLoggingOut] = useState(false);

    const handleLogout = async () => {
        setLoggingOut(true);
        // Simulate short delay for UX smoothness
        setTimeout(() => {
            onLogout();
        }, 500);
    };

    // Fallbacks if userData is incomplete
    const userName = userData?.name || 'User';
    const userEmail = userData?.email || 'user@example.com';
    const userRole = userData?.role_display_name || 'Member';
    const tenantName = userData?.tenant_name || 'Organization';

    // Generate initials for avatar fallback
    const initials = userName
        .split(' ')
        .map(n => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);

    return (
        <View style={styles.container}>
            {/* Header / Profile Widget */}
            <View style={styles.header}>
                <View style={styles.profileRow}>
                    {/* Avatar */}
                    <View style={styles.avatar}>
                        <Text style={styles.avatarText}>{initials}</Text>
                    </View>

                    {/* User Info */}
                    <View style={styles.userInfo}>
                        <Text style={styles.userName}>{userName}</Text>
                        <Text style={styles.userEmail}>{userEmail}</Text>
                        <Text style={styles.userRole}>{userRole} • {tenantName}</Text>
                    </View>

                    {/* Logout Action */}
                    <TouchableOpacity
                        style={styles.logoutBtn}
                        onPress={handleLogout}
                        disabled={loggingOut}
                    >
                        {loggingOut ? (
                            <ActivityIndicator size="small" color="#6B7280" />
                        ) : (
                            <Text style={styles.logoutText}>Logout</Text>
                        )}
                    </TouchableOpacity>
                </View>
            </View>

            <ScrollView style={styles.content} contentContainerStyle={styles.scrollContent}>

                <Text style={styles.sectionTitle}>Overview</Text>

                {/* Skeletal Stats Grid */}
                <View style={styles.statsGrid}>
                    <StatCard
                        label="Active Users"
                        value="1,234"
                        trend="+12%"
                        trendColor="#10B981"
                    />
                    <StatCard
                        label="New Signups"
                        value="56"
                        trend="+5%"
                        trendColor="#10B981"
                    />
                    <StatCard
                        label="Pending Invites"
                        value="8"
                        trend="Action needed"
                        trendColor="#F59E0B"
                        warning
                    />
                    <StatCard
                        label="Total Revenue"
                        value="$45k"
                        trend="+3%"
                        trendColor="#10B981"
                    />
                </View>

                <Text style={styles.sectionTitle}>Quick Actions</Text>

                <View style={styles.actionsRow}>
                    <ActionButton label="Invite User" icon="✉️" color="#4F46E5" />
                    <ActionButton label="Settings" icon="⚙️" color="#6B7280" />
                </View>

            </ScrollView>
        </View>
    );
}

// Sub-components (could receive their own files later)

const StatCard = ({ label, value, trend, trendColor, warning }) => (
    <View style={styles.statCard}>
        <Text style={styles.statLabel}>{label}</Text>
        <Text style={styles.statValue}>{value}</Text>
        {trend && (
            <Text style={[styles.statTrend, { color: trendColor }]}>
                {trend}
            </Text>
        )}
    </View>
);

const ActionButton = ({ label, icon, color }) => (
    <TouchableOpacity style={[styles.actionBtn, { borderColor: color }]}>
        <Text style={styles.actionIcon}>{icon}</Text>
        <Text style={[styles.actionLabel, { color: color }]}>{label}</Text>
    </TouchableOpacity>
);


const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F9FAFB', // Background
    },
    header: {
        paddingTop: 60,
        paddingBottom: 20,
        paddingHorizontal: 24,
        backgroundColor: 'white',
        borderBottomWidth: 1,
        borderBottomColor: '#E5E7EB',
    },
    profileRow: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    avatar: {
        width: 48,
        height: 48,
        borderRadius: 24,
        backgroundColor: '#E0E7FF',
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 16,
    },
    avatarText: {
        color: '#4F46E5',
        fontSize: 18,
        fontWeight: 'bold',
    },
    userInfo: {
        flex: 1,
    },
    userName: {
        fontSize: 16,
        fontWeight: 'bold',
        color: '#111827',
    },
    userEmail: {
        fontSize: 14,
        color: '#6B7280',
    },
    userRole: {
        fontSize: 12,
        color: '#9CA3AF',
        marginTop: 2,
    },
    logoutBtn: {
        padding: 8,
    },
    logoutText: {
        color: '#EF4444', // Error Red for destructive action
        fontSize: 14,
        fontWeight: '600',
    },
    content: {
        flex: 1,
    },
    scrollContent: {
        padding: 24,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#111827',
        marginBottom: 16,
        marginTop: 8,
    },
    statsGrid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 16,
        marginBottom: 32,
    },
    statCard: {
        width: '47%', // roughly half minus gap
        backgroundColor: 'white',
        padding: 16,
        borderRadius: 12,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 2,
        elevation: 2,
    },
    statLabel: {
        fontSize: 12,
        color: '#6B7280',
        marginBottom: 8,
    },
    statValue: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#111827',
        marginBottom: 4,
    },
    statTrend: {
        fontSize: 12,
        fontWeight: '500',
    },
    actionsRow: {
        flexDirection: 'row',
        gap: 16,
    },
    actionBtn: {
        flex: 1,
        backgroundColor: 'white',
        padding: 16,
        borderRadius: 12,
        alignItems: 'center',
        borderWidth: 1,
        borderStyle: 'dashed',
    },
    actionIcon: {
        fontSize: 24,
        marginBottom: 8,
    },
    actionLabel: {
        fontSize: 14,
        fontWeight: '600',
    }
});

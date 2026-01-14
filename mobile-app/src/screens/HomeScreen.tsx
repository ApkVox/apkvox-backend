import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { View, StyleSheet, FlatList, TouchableOpacity } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { useTranslation } from 'react-i18next';
import { useFocusEffect } from '@react-navigation/native'; // Refresh on focus

import { colors, spacing, borderRadius, shadows } from '../constants/theme';
import { getPredictions } from '../services/api';
import { Prediction } from '../types';

import DateStrip from '../components/DateStrip';
import MatchCard from '../components/MatchCard';

interface HomeScreenProps {
    onGameSelect: (prediction: Prediction) => void;
    onSettingsPress: () => void;
}

// Helper to get today's date key using Colombia timezone
const getTodayKey = () => {
    return new Date().toLocaleDateString('en-CA', {
        timeZone: 'America/Bogota',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
};

// Helper for date extraction from ISO string
const getDateKeyFromISO = (isoString: string | null) => {
    if (!isoString) return null;
    try {
        const date = new Date(isoString);
        if (isNaN(date.getTime())) return null;

        // Convert to Colombia timezone
        return date.toLocaleDateString('en-CA', {
            timeZone: 'America/Bogota',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    } catch {
        return null;
    }
};

export const HomeScreen: React.FC<HomeScreenProps> = ({ onGameSelect, onSettingsPress }) => {
    const { t, i18n } = useTranslation();
    const [allPredictions, setAllPredictions] = useState<Prediction[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedDate, setSelectedDate] = useState<string>(getTodayKey());
    const [refreshing, setRefreshing] = useState(false);

    const fetchData = useCallback(async () => {
        try {
            const data = await getPredictions();
            // Sort by time
            const sorted = [...data].sort((a, b) => {
                if (!a.start_time_utc) return 1;
                if (!b.start_time_utc) return -1;
                return new Date(a.start_time_utc).getTime() - new Date(b.start_time_utc).getTime();
            });
            setAllPredictions(sorted);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [i18n.language]); // Add i18n.language dependency to force updates if needed

    // useFocusEffect ensures data is refreshed every time we look at this screen
    // This fixes the bug where data was stale after returning from details
    useFocusEffect(
        useCallback(() => {
            fetchData();
        }, [fetchData])
    );

    const filteredPredictions = useMemo(() => {
        return allPredictions.filter(p => {
            const date = getDateKeyFromISO(p.start_time_utc);
            if (!date) return true; // Show if no date logic
            return date === selectedDate;
        });
    }, [allPredictions, selectedDate]);

    // ... existing handleRefresh and render ...

    const handleRefresh = () => {
        setRefreshing(true);
        fetchData();
    };

    const renderItem = ({ item }: { item: Prediction }) => (
        <MatchCard prediction={item} onPress={() => onGameSelect(item)} />
    );

    return (
        <View style={styles.container}>
            {/* Top Bar */}
            <View style={styles.topBar}>
                <View style={styles.titleRow}>
                    <View style={styles.iconBox}>
                        <Text style={styles.iconText}>📊</Text>
                    </View>
                    <Text style={styles.pageTitle}>{t('upcoming_games')}</Text>
                </View>

                {/* Notification Bell (Visual only) */}
                <TouchableOpacity style={styles.notifButton}>
                    <Text style={styles.notifIcon}>🔔</Text>
                </TouchableOpacity>
            </View>

            {/* Date Strip */}
            <DateStrip selectedDate={selectedDate} onSelectDate={setSelectedDate} />

            {/* Content */}
            {loading && !refreshing && allPredictions.length === 0 ? (
                <View style={styles.centerContainer}>
                    <ActivityIndicator color={colors.primary} size="large" />
                </View>
            ) : (
                <FlatList
                    data={filteredPredictions}
                    renderItem={renderItem}
                    keyExtractor={(item, index) => `${item.home_team}-${item.away_team}-${index}`}
                    contentContainerStyle={styles.listContent}
                    refreshing={refreshing}
                    onRefresh={handleRefresh}
                    ListEmptyComponent={
                        <View style={styles.emptyContainer}>
                            <Text style={styles.emptyText}>{t('no_games')}</Text>
                            <Text style={styles.emptySubtext}>{t('refresh')}</Text>
                        </View>
                    }
                />
            )}

            {/* Bottom Nav (Visual Only) */}
            <View style={styles.bottomNav}>
                <NavItem icon="🏠" label={t('home')} active />
                <NavItem icon="📜" label={t('history')} />
                <NavItem icon="📈" label={t('insights')} />
                <TouchableOpacity onPress={onSettingsPress}>
                    <NavItem icon="⚙️" label={t('settings')} />
                </TouchableOpacity>
            </View>
        </View>
    );
};

// ... existing styles and NavItem ...

const NavItem = ({ icon, label, active }: { icon: string, label: string, active?: boolean }) => (
    <View style={styles.navItem}>
        <Text style={[styles.navIcon, active && { color: colors.primary }]}>{icon}</Text>
        <Text style={[styles.navLabel, active && { color: colors.primary }]}>{label}</Text>
    </View>
);

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.background,
    },
    topBar: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: spacing.lg,
        paddingVertical: spacing.md,
        backgroundColor: 'rgba(255,255,255,0.8)',
    },
    titleRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: spacing.sm,
    },
    iconBox: {
        width: 36,
        height: 36,
        backgroundColor: colors.card,
        borderRadius: borderRadius.md,
        justifyContent: 'center',
        alignItems: 'center',
        borderWidth: 1,
        borderColor: colors.border,
    },
    iconText: {
        fontSize: 18,
    },
    pageTitle: {
        fontSize: 20,
        fontWeight: '800',
        color: colors.textMain,
        letterSpacing: -0.5,
    },
    notifButton: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: colors.card,
        justifyContent: 'center',
        alignItems: 'center',
        borderWidth: 1,
        borderColor: colors.border,
        ...shadows.subtle,
    },
    notifIcon: {
        fontSize: 18,
    },
    centerContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    listContent: {
        paddingTop: spacing.md,
        paddingBottom: 100, // Space for bottom nav
    },
    emptyContainer: {
        padding: spacing.xl,
        alignItems: 'center',
    },
    emptyText: {
        fontSize: 16,
        color: colors.textSecondary,
        fontWeight: '600',
    },
    emptySubtext: {
        fontSize: 12,
        color: colors.textLight,
        marginTop: 4,
    },

    // Bottom Nav
    bottomNav: {
        position: 'absolute',
        bottom: 24,
        left: 24,
        right: 24,
        height: 64,
        backgroundColor: colors.card,
        borderRadius: 32,
        flexDirection: 'row',
        justifyContent: 'space-around',
        alignItems: 'center',
        borderWidth: 1,
        borderColor: colors.border,
        ...shadows.button,
    },
    navItem: {
        alignItems: 'center',
        gap: 2,
    },
    navIcon: {
        fontSize: 22,
        color: colors.textLight,
    },
    navLabel: {
        fontSize: 10,
        fontWeight: '700',
        color: colors.textLight,
    },
});

export default HomeScreen;

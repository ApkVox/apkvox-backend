/**
 * SettingsScreen Component
 * 
 * Allows users to configure app preferences:
 * - Language (ES/EN)
 * - Odds Format (American/Decimal)
 * - Notifications
 */

import React from 'react';
import { View, StyleSheet, TouchableOpacity, ScrollView, Switch, Alert } from 'react-native';
import { Text } from 'react-native-paper';
import { useTranslation } from 'react-i18next';
import { usePreferences } from '../context/PreferencesContext';
import { colors, spacing, borderRadius, shadows, typography } from '../constants/theme';

interface SettingsScreenProps {
    onBack: () => void;
}

export const SettingsScreen: React.FC<SettingsScreenProps> = ({ onBack }) => {
    const { t, i18n } = useTranslation();
    const {
        oddsFormat,
        toggleOddsFormat,
        notifications,
        toggleNotifications,
        setLanguage
    } = usePreferences();

    const handleClearCache = () => {
        Alert.alert(
            t('clear_cache'),
            t('cache_cleared_msg') || 'Cache has been cleared successfully.',
            [{ text: 'OK' }]
        );
    };

    return (
        <View style={styles.container}>
            {/* Header */}
            <View style={styles.header}>
                <TouchableOpacity onPress={onBack} style={styles.backButton}>
                    <Text style={styles.backIcon}>‹</Text>
                </TouchableOpacity>
                <Text style={styles.headerTitle}>{t('settings_title')}</Text>
                <View style={styles.placeholderButton} />
            </View>

            <ScrollView contentContainerStyle={styles.content}>

                {/* General Section */}
                <Text style={styles.sectionTitle}>{t('general')}</Text>
                <View style={styles.section}>
                    <View style={styles.row}>
                        <View style={styles.rowInfo}>
                            <Text style={styles.rowLabel}>{t('language_select')}</Text>
                            <Text style={styles.rowValue}>
                                {i18n.language === 'es' ? 'Español' : 'English'}
                            </Text>
                        </View>
                        <View style={styles.toggleContainer}>
                            <TouchableOpacity
                                style={[styles.langOption, i18n.language === 'es' && styles.langOptionActive]}
                                onPress={() => setLanguage('es')}
                            >
                                <Text style={styles.langEmoji}>🇪🇸</Text>
                            </TouchableOpacity>
                            <TouchableOpacity
                                style={[styles.langOption, i18n.language === 'en' && styles.langOptionActive]}
                                onPress={() => setLanguage('en')}
                            >
                                <Text style={styles.langEmoji}>🇺🇸</Text>
                            </TouchableOpacity>
                        </View>
                    </View>
                </View>

                {/* Betting Preferences */}
                <Text style={styles.sectionTitle}>{t('betting_preferences')}</Text>
                <View style={styles.section}>
                    <View style={styles.row}>
                        <View style={styles.rowInfo}>
                            <Text style={styles.rowLabel}>{t('odds_format')}</Text>
                            <Text style={styles.rowValue}>
                                {oddsFormat === 'AMERICAN' ? t('american') : t('decimal')}
                            </Text>
                        </View>
                        <Switch
                            value={oddsFormat === 'DECIMAL'}
                            onValueChange={toggleOddsFormat}
                            trackColor={{ false: colors.border, true: colors.primaryLight }}
                            thumbColor={oddsFormat === 'DECIMAL' ? colors.primary : '#f4f3f4'}
                        />
                    </View>
                </View>

                {/* System */}
                <Text style={styles.sectionTitle}>{t('system')}</Text>
                <View style={styles.section}>
                    <View style={styles.row}>
                        <View style={styles.rowInfo}>
                            <Text style={styles.rowLabel}>{t('notifications')}</Text>
                        </View>
                        <Switch
                            value={notifications}
                            onValueChange={toggleNotifications}
                            trackColor={{ false: colors.border, true: colors.primaryLight }}
                            thumbColor={notifications ? colors.primary : '#f4f3f4'}
                        />
                    </View>
                    <View style={styles.divider} />
                    <TouchableOpacity style={styles.row} onPress={handleClearCache}>
                        <Text style={[styles.rowLabel, { color: colors.accentRed }]}>{t('clear_cache')}</Text>
                    </TouchableOpacity>
                </View>

                {/* Version */}
                <View style={styles.footer}>
                    <Text style={styles.versionText}>{t('app_version')} 1.0.0</Text>
                </View>

            </ScrollView>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.background,
    },
    content: {
        padding: spacing.lg,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: spacing.lg,
        paddingVertical: spacing.md,
        backgroundColor: 'rgba(255,255,255,0.8)',
        borderBottomWidth: 1,
        borderBottomColor: colors.border,
    },
    backButton: {
        width: 40,
        height: 40,
        borderRadius: 20,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: colors.card,
    },
    backIcon: {
        fontSize: 24,
        fontWeight: 'bold',
        marginTop: -2,
    },
    placeholderButton: {
        width: 40,
    },
    headerTitle: {
        fontSize: 16,
        fontWeight: '800',
        color: colors.textMain,
    },
    sectionTitle: {
        fontSize: 12,
        fontWeight: '700',
        color: colors.textLight,
        textTransform: 'uppercase',
        letterSpacing: 1,
        marginBottom: spacing.sm,
        marginTop: spacing.lg,
        marginLeft: spacing.xs,
    },
    section: {
        backgroundColor: colors.card,
        borderRadius: borderRadius.xl,
        padding: spacing.md,
        ...shadows.subtle,
    },
    row: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: spacing.sm,
    },
    rowInfo: {
        flex: 1,
    },
    rowLabel: {
        fontSize: 14,
        fontWeight: '600',
        color: colors.textMain,
    },
    rowValue: {
        fontSize: 12,
        color: colors.textSecondary,
        marginTop: 2,
    },
    divider: {
        height: 1,
        backgroundColor: colors.divider,
        marginVertical: spacing.sm,
    },
    toggleContainer: {
        flexDirection: 'row',
        gap: spacing.sm,
    },
    langOption: {
        padding: 8,
        borderRadius: 20,
        backgroundColor: colors.background,
        borderWidth: 1,
        borderColor: 'transparent',
    },
    langOptionActive: {
        borderColor: colors.primary,
        backgroundColor: colors.primaryLight,
    },
    langEmoji: {
        fontSize: 20,
    },
    footer: {
        alignItems: 'center',
        marginTop: spacing.xl,
        marginBottom: spacing.xxxl,
    },
    versionText: {
        fontSize: 12,
        color: colors.textLight,
    },
});

export default SettingsScreen;

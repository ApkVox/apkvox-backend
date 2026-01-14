import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text } from 'react-native-paper';
import { colors, borderRadius, spacing, shadows } from '../constants/theme';
import { useTranslation } from 'react-i18next';

interface AIAuditProps {
    status: 'SCHEDULED' | 'LIVE' | 'FINAL';
    predictedWinner: string;
    actualWinner?: string | null;
}

export const AIAudit: React.FC<AIAuditProps> = ({ status, predictedWinner, actualWinner }) => {
    const { t } = useTranslation();

    if (status !== 'FINAL') return null;

    const isCorrect = actualWinner === predictedWinner;
    const badgeColor = isCorrect ? colors.accentGreen : colors.accentRed;
    const badgeText = isCorrect ? t('prediction_correct') : t('prediction_incorrect');

    return (
        <View style={[styles.container, { borderColor: badgeColor }]}>
            <View style={[styles.badge, { backgroundColor: badgeColor }]}>
                <Text style={styles.badgeText}>{badgeText}</Text>
            </View>
            <View style={styles.content}>
                <Text style={styles.title}>{t('ai_audit_title')}</Text>
                <Text style={styles.subtitle}>
                    {isCorrect
                        ? "La IA predijo correctamente el ganador."
                        : "El resultado fue diferente a la predicción."}
                </Text>
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: colors.card,
        borderRadius: borderRadius.lg,
        padding: spacing.md,
        marginVertical: spacing.md,
        borderLeftWidth: 4,
        ...shadows.subtle,
    },
    badge: {
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.xs,
        borderRadius: borderRadius.pill,
        marginRight: spacing.md,
    },
    badgeText: {
        color: '#fff',
        fontWeight: 'bold',
        fontSize: 12,
    },
    content: {
        flex: 1,
    },
    title: {
        fontSize: 14,
        fontWeight: 'bold',
        color: colors.textMain,
    },
    subtitle: {
        fontSize: 12,
        color: colors.textSecondary,
        marginTop: 2,
    },
});

export default AIAudit;

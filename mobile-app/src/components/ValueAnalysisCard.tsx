import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text } from 'react-native-paper';
import { LinearGradient } from 'expo-linear-gradient';
import { useTranslation } from 'react-i18next';
import { colors, spacing, borderRadius, shadows } from '../constants/theme';
import { getTeamShortName } from '../utils/teamLogos';

interface ValueAnalysisCardProps {
    homeTeam: string;
    awayTeam: string;
    homeProb: number;     // AI Probability (0-100)
    awayProb: number;
    homeOdds: number;     // American Odds (e.g., -150, +130)
    awayOdds: number;
    predictedWinner: string;
}

// Helper: American Odds to Implied Probability
const getImpliedProb = (odds: number): number => {
    if (odds === 0) return 0;
    if (odds < 0) {
        return (-odds / (-odds + 100)) * 100;
    } else {
        return (100 / (odds + 100)) * 100;
    }
};

const ValueAnalysisCard: React.FC<ValueAnalysisCardProps> = ({
    homeTeam, awayTeam, homeProb, awayProb, homeOdds, awayOdds, predictedWinner
}) => {
    const { t } = useTranslation();

    // Determine which side is the prediction targeting (usually the winner)
    const isHomeWinner = predictedWinner === homeTeam;
    const targetTeam = isHomeWinner ? homeTeam : awayTeam;
    const targetProb = isHomeWinner ? homeProb : awayProb;
    const targetOdds = isHomeWinner ? homeOdds : awayOdds;

    const impliedProb = getImpliedProb(targetOdds);

    // Value Calculation: Edge = AI Prob - Implied Prob
    const edge = targetProb - impliedProb;
    const isValue = edge > 2.0; // 2% edge is decent

    return (
        <View style={styles.container}>
            <Text style={styles.title}>{t('vegas_vs_ai')}</Text>

            <View style={styles.content}>
                {/* Team Info */}
                <View style={styles.teamInfo}>
                    <Text style={styles.teamName}>{getTeamShortName(targetTeam)}</Text>
                    <Text style={styles.betType}>{t('moneyline')}</Text>
                </View>

                {/* Comparison Bars */}
                <View style={styles.comparison}>
                    {/* Vegas */}
                    <View style={styles.row}>
                        <Text style={styles.label}>{t('vegas_implied')}</Text>
                        <View style={styles.barBg}>
                            <View style={[styles.barFill, { width: `${impliedProb}%`, backgroundColor: colors.textSecondary }]} />
                        </View>
                        <Text style={styles.val}>{impliedProb.toFixed(1)}%</Text>
                    </View>

                    {/* AI */}
                    <View style={styles.row}>
                        <Text style={styles.label}>{t('ai_model')}</Text>
                        <View style={styles.barBg}>
                            <View style={[styles.barFill, { width: `${targetProb}%`, backgroundColor: colors.primary }]} />
                        </View>
                        <Text style={[styles.val, { color: colors.primary }]}>{targetProb.toFixed(1)}%</Text>
                    </View>
                </View>

                {/* Value Badge */}
                {isValue ? (
                    <LinearGradient
                        colors={['#4CAF50', '#2E7D32']}
                        start={{ x: 0, y: 0 }}
                        end={{ x: 1, y: 0 }}
                        style={styles.valueBadge}
                    >
                        <Text style={styles.valueText}>
                            ✅ {t('value_bet', { edge: edge.toFixed(1) })}
                        </Text>
                    </LinearGradient>
                ) : (
                    <View style={styles.noValueBadge}>
                        <Text style={styles.noValueText}>{t('fair_value')}</Text>
                    </View>
                )}
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        backgroundColor: colors.card,
        borderRadius: borderRadius.lg,
        padding: spacing.md,
        marginBottom: spacing.lg,
        ...shadows.card,
    },
    title: {
        fontSize: 12,
        fontWeight: '800',
        color: colors.textLight,
        marginBottom: spacing.md,
        textTransform: 'uppercase',
    },
    content: {
        gap: spacing.md,
    },
    teamInfo: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-end',
        borderBottomWidth: 1,
        borderBottomColor: colors.border,
        paddingBottom: 8,
    },
    teamName: {
        fontSize: 18,
        fontWeight: '800',
        color: colors.textMain,
    },
    betType: {
        fontSize: 12,
        color: colors.textSecondary,
        fontWeight: '600',
    },
    comparison: {
        gap: 12,
    },
    row: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    label: {
        width: 80,
        fontSize: 11,
        fontWeight: '600',
        color: colors.textSecondary,
    },
    barBg: {
        flex: 1,
        height: 8,
        backgroundColor: colors.border,
        borderRadius: 4,
        overflow: 'hidden',
    },
    barFill: {
        height: '100%',
        borderRadius: 4,
    },
    val: {
        width: 45,
        textAlign: 'right',
        fontSize: 12,
        fontWeight: '700',
        color: colors.textMain,
    },
    valueBadge: {
        paddingVertical: 8,
        paddingHorizontal: 12,
        borderRadius: 8,
        alignItems: 'center',
        marginTop: 4,
    },
    valueText: {
        color: '#fff',
        fontWeight: '800',
        fontSize: 12,
    },
    noValueBadge: {
        paddingVertical: 8,
        borderRadius: 8,
        alignItems: 'center',
        backgroundColor: colors.background,
        marginTop: 4,
    },
    noValueText: {
        color: colors.textLight,
        fontWeight: '600',
        fontSize: 12,
    },
});

export default ValueAnalysisCard;

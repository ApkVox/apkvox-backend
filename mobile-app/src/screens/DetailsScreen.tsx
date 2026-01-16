/**
 * DetailsScreen Component
 * 
 * Analysis & Verification Dashboard (Premium Overhaul).
 * Focuses on match stats, AI confidence, and result verification.
 */

import React from 'react';
import { View, StyleSheet, ScrollView, TouchableOpacity, Share, Alert, Image } from 'react-native';
import { Text } from 'react-native-paper';
import { useTranslation } from 'react-i18next';
import { LinearGradient } from 'expo-linear-gradient';

import { Prediction } from '../types';
import { getTeamShortName, getTeamFullName } from '../utils/teamLogos';
import { formatOdds } from '../utils/odds';
import { usePreferences } from '../context/PreferencesContext';
import { colors, spacing, borderRadius, shadows } from '../constants/theme';

import ConfidenceRing from '../components/ConfidenceRing';
import AIAudit from '../components/AIAudit';
import GradientHeader from '../components/GradientHeader';
import ValueAnalysisCard from '../components/ValueAnalysisCard';

interface DetailsScreenProps {
    prediction: Prediction;
    onBack: () => void;
}

export const DetailsScreen: React.FC<DetailsScreenProps> = ({ prediction, onBack }) => {
    const { t } = useTranslation();
    const { oddsFormat } = usePreferences();

    const homeOddsDisplay = formatOdds(prediction.home_odds, oddsFormat);
    const awayOddsDisplay = formatOdds(prediction.away_odds, oddsFormat);

    // Bet Quality Logic
    const getBetQuality = (conf: number) => {
        if (conf >= 65) return { label: t('excellent_bet'), color: '#4CAF50', bg: '#E8F5E9' };
        if (conf >= 55) return { label: t('good_bet'), color: '#FFC107', bg: '#FFF8E1' };
        return { label: t('risky_bet'), color: '#FF5252', bg: '#FFEBEE' };
    };

    const quality = getBetQuality(prediction.winner_confidence);

    // Status Logic
    const status = prediction.status || 'SCHEDULED';
    const isFinal = status === 'FINAL';

    const handleShare = async () => {
        try {
            const message = `${t('share_message')} ${getTeamFullName(prediction.predicted_winner)} (${Math.round(prediction.winner_confidence)}%). 🏀`;
            await Share.share({
                message: message,
            });
        } catch (error) {
            Alert.alert(t('error'), t('share_failed'));
        }
    };

    // Determine actual winner for audit logic if final
    const derivedActualWinner = prediction.actual_winner ||
        (isFinal && prediction.home_score !== undefined && prediction.away_score !== undefined
            ? (prediction.home_score > prediction.away_score ? prediction.home_team : prediction.away_team)
            : undefined);

    return (
        <View style={styles.container}>
            {/* 1. Premium Gradient Header */}
            <GradientHeader prediction={prediction} onBack={onBack} />

            <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>

                {/* 2. AI Audit (Verification) - Only if Final */}
                {isFinal && (
                    <View style={styles.auditContainer}>
                        <AIAudit
                            status={status}
                            predictedWinner={prediction.predicted_winner}
                            actualWinner={derivedActualWinner}
                        />
                    </View>
                )}

                {/* 3. Main Prediction Hero Card */}
                <View style={styles.heroCard}>
                    <Text style={styles.cardHeader}>{t('win_probability')}</Text>

                    <View style={styles.heroContent}>
                        {/* Ring */}
                        <View style={styles.ringWrapper}>
                            <ConfidenceRing
                                percentage={prediction.winner_confidence}
                                size={100}
                                strokeWidth={8}
                                showLabel={false}
                                isHighValue={prediction.winner_confidence >= 65}
                            />
                            <View style={styles.confBadge}>
                                <Text style={styles.confValue}>{Math.round(prediction.winner_confidence)}%</Text>
                                <Text style={styles.confLabel}>{t('confidence')}</Text>
                            </View>
                        </View>

                        {/* Winner Info */}
                        <View style={styles.heroInfo}>
                            <View style={[styles.qualityBadge, { backgroundColor: quality.bg }]}>
                                <Text style={[styles.qualityText, { color: quality.color }]}>{quality.label}</Text>
                            </View>
                            <Text style={styles.heroLabel}>{t('ai_picks')}</Text>
                            <Text style={styles.heroTeam}>{getTeamShortName(prediction.predicted_winner)}</Text>
                            <Text style={styles.heroSub}>{t('to_win')}</Text>
                        </View>
                    </View>

                    {/* Probability Bars */}
                    <View style={styles.probBars}>
                        {/* Home */}
                        <View style={styles.barRow}>
                            <Text style={styles.barLabel}>{getTeamShortName(prediction.home_team)}</Text>
                            <View style={styles.track}>
                                <View style={[styles.fill, { width: `${prediction.home_win_probability}%`, backgroundColor: prediction.predicted_winner === prediction.home_team ? colors.primary : '#E0E0E0' }]} />
                            </View>
                            <Text style={styles.barVal}>{Math.round(prediction.home_win_probability)}%</Text>
                        </View>
                        {/* Away */}
                        <View style={styles.barRow}>
                            <Text style={styles.barLabel}>{getTeamShortName(prediction.away_team)}</Text>
                            <View style={styles.track}>
                                <View style={[styles.fill, { width: `${prediction.away_win_probability}%`, backgroundColor: prediction.predicted_winner === prediction.away_team ? colors.primary : '#E0E0E0' }]} />
                            </View>
                            <Text style={styles.barVal}>{Math.round(prediction.away_win_probability)}%</Text>
                        </View>
                    </View>
                </View>

                {/* 4. Value Analysis Card */}
                <ValueAnalysisCard
                    homeTeam={prediction.home_team}
                    awayTeam={prediction.away_team}
                    homeProb={prediction.home_win_probability}
                    awayProb={prediction.away_win_probability}
                    homeOdds={prediction.home_odds}
                    awayOdds={prediction.away_odds}
                    predictedWinner={prediction.predicted_winner}
                />

                {/* 5. Stats Grid (O/U and Odds) */}
                <View style={styles.statsRow}>
                    {/* O/U Card */}
                    <View style={styles.statBox}>
                        <Text style={styles.statBoxTitle}>{t('over_under')}</Text>
                        <Text style={styles.statBoxValue}>{prediction.under_over_prediction === 'OVER' ? t('over') : t('under')} {prediction.under_over_line}</Text>
                        <Text style={styles.statBoxSub}>{prediction.ou_confidence}% {t('confidence')}</Text>
                    </View>

                    {/* Best Odds Card */}
                    <View style={styles.statBox}>
                        <Text style={styles.statBoxTitle}>{t('best_odds')}</Text>
                        <View style={styles.oddsLine}>
                            <Text style={styles.oddsTeam}>{getTeamShortName(prediction.home_team)}</Text>
                            <Text style={styles.oddsNum}>{homeOddsDisplay}</Text>
                        </View>
                        <View style={styles.oddsLine}>
                            <Text style={styles.oddsTeam}>{getTeamShortName(prediction.away_team)}</Text>
                            <Text style={styles.oddsNum}>{awayOddsDisplay}</Text>
                        </View>
                    </View>
                </View>

                {/* 6. AI News Analysis Section */}
                {prediction.ai_impact && (
                    <View style={styles.aiNewsCard}>
                        <View style={styles.aiNewsHeader}>
                            <Text style={styles.aiNewsTitle}>{t('ai_news_title')}</Text>
                            <View style={[styles.aiScoreBadge, { backgroundColor: prediction.ai_impact.impact_score > 0 ? '#E8F5E9' : (prediction.ai_impact.impact_score < 0 ? '#FFEBEE' : '#F5F5F5') }]}>
                                <Text style={[styles.aiScoreText, { color: prediction.ai_impact.impact_score > 0 ? '#4CAF50' : (prediction.ai_impact.impact_score < 0 ? '#FF5252' : '#9E9E9E') }]}>
                                    {prediction.ai_impact.impact_score > 0 ? '📈 ' : (prediction.ai_impact.impact_score < 0 ? '📉 ' : '')}
                                    {Math.abs(prediction.ai_impact.impact_score).toFixed(1)}
                                </Text>
                            </View>
                        </View>

                        <Text style={styles.aiSummaryLabel}>{t('ai_summary')}</Text>
                        <Text style={styles.aiSummaryText}>{prediction.ai_impact.summary}</Text>

                        {prediction.ai_impact.key_factors && prediction.ai_impact.key_factors.length > 0 && (
                            <View style={styles.aiFactorsContainer}>
                                <Text style={styles.aiSummaryLabel}>{t('ai_factors')}</Text>
                                {prediction.ai_impact.key_factors.map((factor, index) => (
                                    <View key={index} style={styles.factorRow}>
                                        <Text style={styles.factorBullet}>•</Text>
                                        <Text style={styles.factorText}>{factor}</Text>
                                    </View>
                                ))}
                            </View>
                        )}

                        <View style={styles.aiConfidenceRow}>
                            <Text style={styles.aiConfLabel}>{t('confidence')}: {Math.round(prediction.ai_impact.confidence * 100)}%</Text>
                        </View>
                    </View>
                )}

                <LinearGradient
                    colors={[colors.primary + '15', colors.primary + '05']}
                    style={styles.insightBox}
                >
                    <Text style={styles.insightTitle}>{t('smart_insight')}</Text>
                    <Text style={styles.insightBody}>
                        {t('smart_insight_text', {
                            team: getTeamShortName(prediction.predicted_winner),
                            confidence: Math.round(prediction.winner_confidence),
                            prediction: prediction.under_over_prediction === 'OVER' ? t('over') : t('under'),
                            line: prediction.under_over_line
                        })}
                    </Text>
                </LinearGradient>

                {/* 7. Share Ticket Button */}
                <TouchableOpacity style={styles.ticketButton} onPress={handleShare}>
                    <LinearGradient
                        colors={[colors.primary, '#4a69bd']}
                        start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
                        style={styles.ticketGradient}
                    >
                        <Text style={styles.ticketIcon}>🎟️</Text>
                        <Text style={styles.ticketText}>{t('share_prediction')}</Text>
                    </LinearGradient>
                </TouchableOpacity>

                <View style={{ height: 40 }} />
            </ScrollView>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F5F7FA', // Slightly gray background for contrast
    },
    scrollContent: {
        padding: spacing.lg,
    },
    auditContainer: {
        marginBottom: spacing.lg,
    },

    // Hero Card
    heroCard: {
        backgroundColor: '#fff', // Pure white
        borderRadius: borderRadius.xl,
        padding: spacing.lg,
        marginBottom: spacing.lg,
        ...shadows.card,
    },
    cardHeader: {
        fontSize: 12,
        fontWeight: '800',
        color: colors.textLight,
        marginBottom: spacing.lg,
        textTransform: 'uppercase',
        letterSpacing: 0.5,
    },
    heroContent: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: spacing.xl,
    },
    ringWrapper: {
        position: 'relative',
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: spacing.xl,
    },
    confBadge: {
        position: 'absolute',
    },
    confValue: {
        fontSize: 20,
        fontWeight: '900',
        color: colors.textMain,
    },
    heroInfo: {
        flex: 1,
        justifyContent: 'center',
    },
    heroLabel: {
        fontSize: 12,
        color: colors.primary,
        fontWeight: '700',
        letterSpacing: 1,
        marginBottom: 4,
    },
    heroTeam: {
        fontSize: 28,
        fontWeight: '800',
        color: colors.textMain,
        lineHeight: 32,
        marginBottom: 4,
    },
    heroSub: {
        fontSize: 14,
        color: colors.textSecondary,
        fontWeight: '500',
    },
    confLabel: {
        fontSize: 10,
        color: colors.textSecondary,
        fontWeight: '600',
        marginTop: -2,
    },
    qualityBadge: {
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 4,
        alignSelf: 'flex-start',
        marginBottom: 8,
    },
    qualityText: {
        fontSize: 10,
        fontWeight: '800',
        textTransform: 'uppercase',
    },

    // Bars
    probBars: {
        gap: 12,
    },
    barRow: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    barLabel: {
        width: 70,
        fontSize: 12,
        fontWeight: '700',
        color: colors.textSecondary,
    },
    track: {
        flex: 1,
        height: 6,
        backgroundColor: colors.border,
        borderRadius: 3,
        marginHorizontal: 8,
        overflow: 'hidden',
    },
    fill: {
        height: '100%',
        borderRadius: 3,
    },
    barVal: {
        width: 30,
        fontSize: 12,
        fontWeight: '700',
        color: colors.textMain,
        textAlign: 'right',
    },

    // Stats Row
    statsRow: {
        flexDirection: 'row',
        gap: spacing.md,
        marginBottom: spacing.lg,
    },
    statBox: {
        flex: 1,
        backgroundColor: '#fff',
        padding: spacing.md,
        borderRadius: borderRadius.lg,
        ...shadows.subtle,
    },
    statBoxTitle: {
        fontSize: 11,
        fontWeight: '700',
        color: colors.textLight,
        textTransform: 'uppercase',
        marginBottom: 8,
    },
    statBoxValue: {
        fontSize: 20,
        fontWeight: '800',
        color: colors.textMain,
        marginBottom: 4,
    },
    statBoxSub: {
        fontSize: 12,
        color: colors.textSecondary,
        fontWeight: '600',
    },
    oddsLine: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginBottom: 6,
    },
    oddsTeam: {
        fontSize: 13,
        fontWeight: '600',
        color: colors.textSecondary,
    },
    oddsNum: {
        fontSize: 13,
        fontWeight: '700',
        color: colors.textMain,
    },

    // Insight
    insightBox: {
        padding: spacing.lg,
        borderRadius: borderRadius.lg,
        borderWidth: 1,
        borderColor: colors.primary + '20',
        marginBottom: spacing.xl,
    },
    insightTitle: {
        fontSize: 14,
        fontWeight: '800',
        color: colors.primary,
        marginBottom: 8,
    },
    insightBody: {
        fontSize: 14,
        color: colors.textMain,
        lineHeight: 22,
    },

    // Ticket Button
    ticketButton: {
        ...shadows.button,
    },
    ticketGradient: {
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        paddingVertical: 16,
        borderRadius: borderRadius.pill,
        gap: 8,
    },
    ticketIcon: {
        fontSize: 20,
    },
    ticketText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '800',
        letterSpacing: 0.5,
        textTransform: 'uppercase',
    },

    // AI News Card Styles
    aiNewsCard: {
        backgroundColor: '#fff',
        borderRadius: borderRadius.xl,
        padding: spacing.lg,
        marginBottom: spacing.lg,
        borderLeftWidth: 4,
        borderLeftColor: colors.primary,
        ...shadows.card,
    },
    aiNewsHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: spacing.md,
    },
    aiNewsTitle: {
        fontSize: 14,
        fontWeight: '800',
        color: colors.textMain,
        textTransform: 'uppercase',
        letterSpacing: 0.5,
    },
    aiScoreBadge: {
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 8,
    },
    aiScoreText: {
        fontSize: 12,
        fontWeight: '900',
    },
    aiSummaryLabel: {
        fontSize: 11,
        fontWeight: '800',
        color: colors.textLight,
        textTransform: 'uppercase',
        marginBottom: 4,
        marginTop: 8,
    },
    aiSummaryText: {
        fontSize: 14,
        color: colors.textMain,
        lineHeight: 20,
    },
    aiFactorsContainer: {
        marginTop: spacing.md,
        paddingTop: spacing.sm,
        borderTopWidth: 1,
        borderTopColor: '#F0F0F0',
    },
    factorRow: {
        flexDirection: 'row',
        marginBottom: 4,
        paddingLeft: 4,
    },
    factorBullet: {
        fontSize: 14,
        color: colors.primary,
        marginRight: 8,
    },
    factorText: {
        flex: 1,
        fontSize: 13,
        color: colors.textSecondary,
        fontWeight: '500',
    },
    aiConfidenceRow: {
        marginTop: spacing.md,
        alignItems: 'flex-end',
    },
    aiConfLabel: {
        fontSize: 10,
        color: colors.textLight,
        fontWeight: '700',
        fontStyle: 'italic',
    },
});

export default DetailsScreen;

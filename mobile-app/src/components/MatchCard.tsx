/**
 * MatchCard Component - External UI Design Integration
 * 
 * Premium card design matching the external Interface-bet repository.
 * Features: Large team logos, centered VS, SVG confidence ring, value badges.
 * Now supports: Live Scores, Final Results, and Status Indicators.
 */

import React from 'react';
import { View, StyleSheet, Image, TouchableOpacity } from 'react-native';
import { Text } from 'react-native-paper';
import { useTranslation } from 'react-i18next';
import { usePreferences } from '../context/PreferencesContext';

import { Prediction, calculateExpectedValue, formatGameTime } from '../types';
import { getTeamLogoUrl, getTeamShortName } from '../utils/teamLogos';
import { formatOdds } from '../utils/odds';
import { colors, spacing, borderRadius, typography, shadows } from '../constants/theme';
import ConfidenceRing from './ConfidenceRing';

interface MatchCardProps {
    prediction: Prediction;
    onPress?: () => void;
}

export const MatchCard: React.FC<MatchCardProps> = ({ prediction, onPress }) => {
    const { t } = useTranslation();
    const { oddsFormat } = usePreferences();

    // Calculate expected values
    const homeEV = calculateExpectedValue(
        prediction.home_win_probability,
        prediction.home_odds
    );
    const awayEV = calculateExpectedValue(
        prediction.away_win_probability,
        prediction.away_odds
    );

    const bestEV = Math.max(homeEV, awayEV);
    const isHighValue = bestEV > 0.1;
    const isHomeWinner = prediction.predicted_winner === prediction.home_team;
    const winnerShortName = getTeamShortName(prediction.predicted_winner);

    // Status Logic
    const status = prediction.status || 'SCHEDULED';
    const isLive = status === 'LIVE';
    const isFinal = status === 'FINAL';

    // Format time for display (only if Scheduled)
    const gameTimeDisplay = prediction.start_time_utc
        ? formatGameTime(prediction.start_time_utc).replace('Hoy, ', '').replace('Mañana, ', '')
        : '';

    // Format Odds
    const homeOddsDisplay = formatOdds(prediction.home_odds, oddsFormat);
    const awayOddsDisplay = formatOdds(prediction.away_odds, oddsFormat);

    // Determine correct prediction for Final games
    // Fallback logic if actual_winner is missing from backend
    const actualWinner = prediction.actual_winner || (
        isFinal && (prediction.home_score || 0) > (prediction.away_score || 0)
            ? prediction.home_team
            : prediction.away_team
    );

    // Use backend 'is_correct' field if available (Source of Truth)
    // Otherwise fallback to local calculation
    const isPredictionCorrect = prediction.is_correct !== undefined && prediction.is_correct !== null
        ? prediction.is_correct === 1
        : (isFinal ? actualWinner === prediction.predicted_winner : null);

    return (
        <TouchableOpacity
            style={styles.card}
            onPress={onPress}
            activeOpacity={0.98}
        >
            {/* Main Content Area */}
            <View style={styles.content}>
                {/* Header - League & Time/Status */}
                <View style={styles.header}>
                    <View style={styles.leagueContainer}>
                        <View style={styles.leagueIconBox}>
                            <Text style={styles.leagueIcon}>🏀</Text>
                        </View>
                        <Text style={styles.leagueText}>{t('nba_league')}</Text>
                    </View>

                    {/* Status Indicators */}
                    {isLive ? (
                        <View style={styles.liveBadge}>
                            <View style={styles.liveDot} />
                            <Text style={styles.liveText}>{t('match_live')}</Text>
                        </View>
                    ) : isFinal ? (
                        <View style={styles.finalBadge}>
                            <Text style={styles.finalText}>{t('match_final')}</Text>
                        </View>
                    ) : (
                        gameTimeDisplay && (
                            <View style={styles.timeBadge}>
                                <Text style={styles.timeIcon}>🕐</Text>
                                <Text style={styles.timeText}>{gameTimeDisplay}</Text>
                            </View>
                        )
                    )}
                </View>

                {/* Teams Section */}
                <View style={styles.teamsContainer}>
                    {/* Home Team */}
                    <View style={styles.teamColumn}>
                        <View style={styles.logoCircle}>
                            <Image
                                source={{ uri: getTeamLogoUrl(prediction.home_team) }}
                                style={styles.teamLogo}
                                resizeMode="contain"
                            />
                        </View>
                        <Text style={[
                            styles.teamName,
                            isHomeWinner && styles.teamNameWinner
                        ]} numberOfLines={1}>
                            {getTeamShortName(prediction.home_team)}
                        </Text>

                        {/* Show Score if Live/Final, else Odds */}
                        {(isLive || isFinal) ? (
                            <Text style={styles.scoreText}>{prediction.home_score || 0}</Text>
                        ) : (
                            prediction.home_odds !== 0 && (
                                <Text style={styles.oddsText}>{homeOddsDisplay}</Text>
                            )
                        )}
                    </View>

                    {/* VS Separator */}
                    <View style={styles.vsContainer}>
                        <Text style={styles.vsText}>{t('vs')}</Text>
                    </View>

                    {/* Away Team */}
                    <View style={styles.teamColumn}>
                        <View style={styles.logoCircle}>
                            <Image
                                source={{ uri: getTeamLogoUrl(prediction.away_team) }}
                                style={styles.teamLogo}
                                resizeMode="contain"
                            />
                        </View>
                        <Text style={[
                            styles.teamName,
                            !isHomeWinner && styles.teamNameWinner
                        ]} numberOfLines={1}>
                            {getTeamShortName(prediction.away_team)}
                        </Text>

                        {/* Show Score if Live/Final, else Odds */}
                        {(isLive || isFinal) ? (
                            <Text style={styles.scoreText}>{prediction.away_score || 0}</Text>
                        ) : (
                            prediction.away_odds !== 0 && (
                                <Text style={styles.oddsText}>{awayOddsDisplay}</Text>
                            )
                        )}
                    </View>
                </View>
            </View>

            {/* Prediction Footer */}
            <View style={styles.predictionFooter}>
                {/* Left - AI Prediction with confidence ring */}
                <View style={styles.predictionLeft}>
                    <ConfidenceRing
                        percentage={prediction.winner_confidence}
                        size={48}
                        strokeWidth={3}
                        isHighValue={isHighValue}
                    />
                    <View style={styles.predictionTextContainer}>
                        <Text style={styles.predictionLabel}>{t('prediction')}</Text>
                        <Text style={styles.predictionPick}>{t('pick')}: {winnerShortName}</Text>
                    </View>
                </View>

                {/* Right - Value Badge OR Result Badge */}
                {isFinal && isPredictionCorrect !== null ? (
                    <View style={[styles.resultBadge, { backgroundColor: isPredictionCorrect ? colors.accentGreen : colors.accentRed }]}>
                        <Text style={styles.resultText}>
                            {isPredictionCorrect ? t('prediction_correct') : t('prediction_incorrect')}
                        </Text>
                    </View>
                ) : isHighValue ? (
                    <View style={styles.highValueBadge}>
                        <Text style={styles.highValueText}>{t('high_value')}</Text>
                    </View>
                ) : (
                    <View style={styles.normalBadge}>
                        <Text style={styles.normalBadgeText}>{t('normal_stake')}</Text>
                    </View>
                )}
            </View>
        </TouchableOpacity>
    );
};

const styles = StyleSheet.create({
    card: {
        backgroundColor: colors.card,
        borderRadius: borderRadius.xl,
        marginHorizontal: spacing.lg,
        marginBottom: spacing.lg,
        overflow: 'hidden',
        borderWidth: 1,
        borderColor: colors.border,
        ...shadows.card,
    },
    content: {
        padding: spacing.xl,
    },

    // Header
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: spacing.xl,
    },
    leagueContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: spacing.sm,
    },
    leagueIconBox: {
        width: 32,
        height: 32,
        borderRadius: borderRadius.md,
        backgroundColor: colors.background,
        justifyContent: 'center',
        alignItems: 'center',
    },
    leagueIcon: {
        fontSize: 16,
    },
    leagueText: {
        fontSize: 10,
        fontWeight: '800',
        color: colors.textLight,
        letterSpacing: 1.5,
    },
    timeBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        backgroundColor: colors.accentOrangeBg,
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.xs + 2,
        borderRadius: borderRadius.pill,
    },
    timeIcon: {
        fontSize: 12,
    },
    timeText: {
        fontSize: 11,
        fontWeight: '800',
        color: colors.accentOrange,
        letterSpacing: -0.3,
    },

    // Status Badges
    liveBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: colors.accentRed + '20',
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.xs + 2,
        borderRadius: borderRadius.pill,
        borderWidth: 1,
        borderColor: colors.accentRed,
    },
    liveDot: {
        width: 6,
        height: 6,
        borderRadius: 3,
        backgroundColor: colors.accentRed,
        marginRight: 6,
    },
    liveText: {
        color: colors.accentRed,
        fontWeight: 'bold',
        fontSize: 10,
        textTransform: 'uppercase',
    },
    finalBadge: {
        backgroundColor: colors.textMain,
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.xs + 2,
        borderRadius: borderRadius.pill,
    },
    finalText: {
        color: '#fff',
        fontWeight: 'bold',
        fontSize: 10,
        textTransform: 'uppercase',
    },

    // Teams
    teamsContainer: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        position: 'relative',
    },
    teamColumn: {
        flex: 1,
        alignItems: 'center',
        gap: spacing.sm,
    },
    logoCircle: {
        width: 64,
        height: 64,
        borderRadius: 32,
        backgroundColor: colors.card,
        borderWidth: 1,
        borderColor: colors.border,
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 8,
        elevation: 2,
    },
    teamLogo: {
        width: 48,
        height: 48,
    },
    teamName: {
        fontSize: typography.lg,
        fontWeight: '800',
        color: colors.textMain,
        textAlign: 'center',
    },
    teamNameWinner: {
        color: colors.primary,
    },
    oddsText: {
        fontSize: typography.sm,
        fontWeight: '500',
        color: colors.textLight,
    },
    scoreText: {
        fontSize: 20,
        fontWeight: '900',
        color: colors.textMain,
    },
    vsContainer: {
        position: 'absolute',
        left: '50%',
        top: '50%',
        transform: [{ translateX: -12 }, { translateY: -10 }],
        zIndex: -1,
    },
    vsText: {
        fontSize: 20,
        fontWeight: '900',
        color: colors.border,
        fontStyle: 'italic',
    },

    // Prediction Footer
    predictionFooter: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        backgroundColor: colors.primaryLight,
        paddingHorizontal: spacing.lg,
        paddingVertical: spacing.lg,
    },
    predictionLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: spacing.md,
    },
    predictionTextContainer: {
        gap: 2,
    },
    predictionLabel: {
        fontSize: 9,
        fontWeight: '700',
        color: colors.textLight,
        letterSpacing: 1.2,
    },
    predictionPick: {
        fontSize: typography.md,
        fontWeight: '800',
        color: colors.textMain,
    },
    highValueBadge: {
        backgroundColor: colors.accentGreen,
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.sm,
        borderRadius: borderRadius.pill,
        shadowColor: colors.accentGreen,
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
        elevation: 4,
    },
    highValueText: {
        fontSize: 9,
        fontWeight: '800',
        color: colors.textWhite,
        letterSpacing: 0.5,
    },
    normalBadge: {
        backgroundColor: colors.card,
        borderWidth: 1,
        borderColor: colors.primary + '30',
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.sm,
        borderRadius: borderRadius.pill,
    },
    normalBadgeText: {
        fontSize: 9,
        fontWeight: '800',
        color: colors.primary,
        letterSpacing: 0.5,
    },
    resultBadge: {
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.sm,
        borderRadius: borderRadius.pill,
        shadowColor: colors.textMain,
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.2,
        shadowRadius: 4,
        elevation: 3,
    },
    resultText: {
        fontSize: 9,
        fontWeight: '900',
        color: colors.textWhite,
        letterSpacing: 0.5,
        textTransform: 'uppercase',
    }
});

export default MatchCard;

import React from 'react';
import { View, StyleSheet, TouchableOpacity, Image, Platform } from 'react-native';
import { Text } from 'react-native-paper';
import { LinearGradient } from 'expo-linear-gradient';
import { useTranslation } from 'react-i18next';
import { getTeamLogoUrl, getTeamShortName, getTeamColors } from '../utils/teamLogos';
import { formatGameTime } from '../types';
import { colors, spacing, shadows } from '../constants/theme';
import { Prediction } from '../types';

interface GradientHeaderProps {
    prediction: Prediction;
    onBack: () => void;
}

const GradientHeader: React.FC<GradientHeaderProps> = ({ prediction, onBack }) => {
    const { t } = useTranslation();

    // Get statuses
    const status = prediction.status || 'SCHEDULED';
    const isLive = status === 'LIVE';
    const isFinal = status === 'FINAL';

    // Get team colors for gradient
    // We use the home team's primary color -> away team's primary color for a VS effect
    // Or simpler: Home Primary -> Darker shade
    const homeColors = getTeamColors(prediction.home_team);
    // const awayColors = getTeamColors(prediction.away_team); // Optional: dual team gradient

    return (
        <View style={styles.container}>
            <LinearGradient
                colors={[homeColors[0], '#121212']} // Fade to black/dark
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.gradient}
            >
                {/* Custom Navigation Bar */}
                <View style={styles.navBar}>
                    <TouchableOpacity onPress={onBack} style={styles.backButton}>
                        <Text style={styles.backIcon}>‹</Text>
                    </TouchableOpacity>
                    <Text style={styles.headerTitle}>{t('matchup_details')}</Text>
                    <View style={styles.placeholder} />
                </View>

                {/* Scoreboard Content */}
                <View style={styles.content}>
                    {/* Home Team */}
                    <View style={styles.teamCol}>
                        <Image
                            source={{ uri: getTeamLogoUrl(prediction.home_team) }}
                            style={styles.logo}
                            resizeMode="contain"
                        />
                        <Text style={styles.teamName}>{getTeamShortName(prediction.home_team)}</Text>
                        {(isLive || isFinal) && (
                            <Text style={styles.score}>{prediction.home_score || 0}</Text>
                        )}
                    </View>

                    {/* Center Info */}
                    <View style={styles.centerCol}>
                        {isLive && (
                            <View style={styles.liveBadge}>
                                <View style={styles.liveDot} />
                                <Text style={styles.liveText}>LIVE</Text>
                            </View>
                        )}
                        {isFinal && (
                            <View style={styles.finalBadge}>
                                <Text style={styles.finalText}>FINAL</Text>
                            </View>
                        )}
                        {!isLive && !isFinal && (
                            <Text style={styles.vs}>VS</Text>
                        )}

                        {!isFinal && (
                            <Text style={styles.time}>
                                {isLive ? 'Q4' : formatGameTime(prediction.start_time_utc).split(',')[1]?.trim()}
                            </Text>
                        )}
                    </View>

                    {/* Away Team */}
                    <View style={styles.teamCol}>
                        <Image
                            source={{ uri: getTeamLogoUrl(prediction.away_team) }}
                            style={styles.logo}
                            resizeMode="contain"
                        />
                        <Text style={styles.teamName}>{getTeamShortName(prediction.away_team)}</Text>
                        {(isLive || isFinal) && (
                            <Text style={styles.score}>{prediction.away_score || 0}</Text>
                        )}
                    </View>
                </View>
            </LinearGradient>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        width: '100%',
        backgroundColor: colors.background,
        overflow: 'hidden',
        borderBottomLeftRadius: 30,
        borderBottomRightRadius: 30,
        ...shadows.card,
    },
    gradient: {
        width: '100%',
        paddingTop: Platform.OS === 'ios' ? 44 : 20, // SafeArea
        paddingBottom: spacing.xl,
    },
    navBar: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: spacing.md,
        marginBottom: spacing.md,
    },
    backButton: {
        width: 36,
        height: 36,
        borderRadius: 18,
        backgroundColor: 'rgba(0,0,0,0.3)',
        justifyContent: 'center',
        alignItems: 'center',
    },
    backIcon: {
        fontSize: 24,
        color: '#fff',
        marginTop: -4,
    },
    headerTitle: {
        color: 'rgba(255,255,255,0.9)',
        fontWeight: '700',
        fontSize: 14,
        textTransform: 'uppercase',
    },
    placeholder: { width: 36 },

    content: {
        flexDirection: 'row',
        justifyContent: 'space-around', // Changed to space-around for better centering
        alignItems: 'center', // Changed to center
        paddingHorizontal: spacing.lg,
    },
    teamCol: {
        alignItems: 'center',
        width: '30%',
    },
    logo: {
        width: 70, // Increased size
        height: 70,
        marginBottom: 8,
    },
    teamName: {
        color: '#fff',
        fontWeight: '700',
        fontSize: 14, // Increased size
        textAlign: 'center',
        marginBottom: 4,
    },
    score: {
        color: '#fff',
        fontSize: 32,
        fontWeight: '800',
        textShadowColor: 'rgba(0,0,0,0.5)',
        textShadowOffset: { width: 0, height: 2 },
        textShadowRadius: 4,
        marginTop: 4, // Added margin
    },
    centerCol: {
        width: '20%', // Explicit width
        alignItems: 'center',
        justifyContent: 'center', // Center vertically
    },
    vs: {
        color: 'rgba(255,255,255,0.4)',
        fontSize: 24,
        fontWeight: '900',
        fontStyle: 'italic',
    },
    time: {
        color: 'rgba(255,255,255,0.8)',
        fontSize: 12,
        fontWeight: '600',
        marginTop: 4,
    },
    liveBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 8,
        paddingVertical: 2,
        backgroundColor: '#E31837',
        borderRadius: 12,
        marginBottom: 4,
    },
    liveDot: {
        width: 6,
        height: 6,
        borderRadius: 3,
        backgroundColor: '#fff',
        marginRight: 4,
    },
    liveText: {
        color: '#fff',
        fontSize: 10,
        fontWeight: '800',
    },
    finalBadge: {
        paddingHorizontal: 8,
        paddingVertical: 2,
        backgroundColor: 'rgba(255,255,255,0.2)',
        borderRadius: 4,
        marginBottom: 4,
    },
    finalText: {
        color: '#fff',
        fontSize: 10,
        fontWeight: '800',
    },
});

export default GradientHeader;

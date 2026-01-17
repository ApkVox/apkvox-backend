import React, { useState } from 'react';
import {
    View,
    Text,
    StyleSheet,
    TextInput,
    TouchableOpacity,
    FlatList,
    ActivityIndicator,
    Alert,
    SafeAreaView,
    StatusBar
} from 'react-native';
import { colors, spacing, typography } from '../constants/theme';
import { optimizeStrategy, StrategyResponse, ProposedBet } from '../services/api';
// Use Expo vector icons
import { MaterialCommunityIcons as Icon } from '@expo/vector-icons';
const SniperScreen = ({ onBack }: { onBack: () => void }) => {
    // const navigation = useNavigation(); // Removed in favor of manual state nav
    const [bankroll, setBankroll] = useState('50000');
    const [loading, setLoading] = useState(false);
    const [strategyData, setStrategyData] = useState<StrategyResponse | null>(null);

    const handleOptimize = async () => {
        const amount = parseFloat(bankroll);
        if (isNaN(amount) || amount <= 0) {
            Alert.alert("Error", "Por favor ingresa un capital válido.");
            return;
        }

        setLoading(true);
        try {
            const data = await optimizeStrategy(amount);
            if (data) {
                setStrategyData(data);
            } else {
                Alert.alert("Info", "No se pudo obtener la estrategia. Revisa tu conexión.");
            }
        } catch (error) {
            console.error(error);
            Alert.alert("Error", "Ocurrió un error al generar la estrategía.");
        } finally {
            setLoading(false);
        }
    };

    const renderBetItem = ({ item }: { item: ProposedBet }) => (
        <View style={styles.betCard}>
            <View style={styles.betHeader}>
                <Text style={styles.matchText}>{item.match}</Text>
                <View style={styles.oddsBadge}>
                    <Text style={styles.oddsText}>x{item.odds.toFixed(2)}</Text>
                </View>
            </View>

            <View style={styles.betBody}>
                <View style={styles.selectionRow}>
                    <Icon name="target" size={20} color={colors.primary} />
                    <Text style={styles.selectionText}>{item.selection}</Text>
                </View>

                <View style={styles.stakeContainer}>
                    <Text style={styles.stakeLabel}>Kelly Stake:</Text>
                    <Text style={styles.stakeValue}>${item.stake_amount.toLocaleString()}</Text>
                </View>
            </View>

            <View style={styles.betFooter}>
                <Text style={styles.statusText}>Estado: {item.status}</Text>
            </View>
        </View>
    );

    return (
        <SafeAreaView style={styles.container}>
            <StatusBar barStyle="light-content" backgroundColor={colors.background} />

            {/* Header */}
            <View style={styles.header}>
                <TouchableOpacity onPress={onBack} style={styles.backButton}>
                    <Icon name="arrow-left" size={24} color={colors.textLight} />
                </TouchableOpacity>
                <Text style={styles.headerTitle}>Sniper Dashboard 🎯</Text>
                <View style={{ width: 24 }} />
            </View>

            <View style={styles.content}>
                {/* Bankroll Input Section */}
                <View style={styles.inputCard}>
                    <Text style={styles.label}>Capital Inicial ($)</Text>
                    <View style={styles.inputRow}>
                        <TextInput
                            style={styles.input}
                            value={bankroll}
                            onChangeText={setBankroll}
                            keyboardType="numeric"
                            placeholderTextColor={colors.textSecondary}
                        />
                        <TouchableOpacity
                            style={styles.optimizeButton}
                            onPress={handleOptimize}
                            disabled={loading}
                        >
                            {loading ? (
                                <ActivityIndicator color="#FFF" size="small" />
                            ) : (
                                <Text style={styles.buttonText}>ANALIZAR</Text>
                            )}
                        </TouchableOpacity>
                    </View>
                </View>

                {/* Results Section */}
                {strategyData ? (
                    <FlatList
                        data={strategyData.proposed_bets}
                        keyExtractor={(item) => item.prediction_id + item.selection}
                        renderItem={renderBetItem}
                        ListHeaderComponent={() => (
                            <View style={styles.sentinelCard}>
                                <View style={styles.sentinelHeader}>
                                    <Icon name="robot" size={24} color={colors.accentOrange} />
                                    <Text style={styles.sentinelTitle}>Sentinel AI Advisor</Text>
                                </View>
                                <Text style={styles.riskText}>
                                    "{strategyData.risk_analysis.message}"
                                </Text>
                                <View style={styles.riskBadge}>
                                    <Text style={styles.riskLabel}>Nivel de Riesgo: </Text>
                                    <Text style={[
                                        styles.riskValue,
                                        { color: strategyData.risk_analysis.exposure_rating === 'HIGH' ? colors.accentRed : colors.accentGreen }
                                    ]}>
                                        {strategyData.risk_analysis.exposure_rating}
                                    </Text>
                                </View>
                            </View>
                        )}
                        contentContainerStyle={{ paddingBottom: spacing.xl }}
                        showsVerticalScrollIndicator={false}
                        ListEmptyComponent={
                            <View style={styles.emptyState}>
                                <Text style={styles.emptyText}>
                                    No hay oportunidades "Sniper" hoy.
                                    El sistema recomienda no apostar.
                                </Text>
                            </View>
                        }
                    />
                ) : (
                    <View style={styles.placeholderContainer}>
                        <Icon name="chart-line-variant" size={64} color={colors.card} />
                        <Text style={styles.placeholderText}>
                            Ingresa tu capital y deja que el sistema optimize tus apuestas.
                        </Text>
                    </View>
                )}
            </View>
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.background,
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.md,
        backgroundColor: colors.card,
        borderBottomWidth: 1,
        borderBottomColor: colors.border,
    },
    backButton: {
        padding: spacing.xs,
    },
    headerTitle: {
        fontSize: typography.lg,
        fontWeight: 'bold',
        color: colors.textMain,
    },
    content: {
        flex: 1,
        padding: spacing.md,
    },
    inputCard: {
        backgroundColor: colors.card,
        padding: spacing.md,
        borderRadius: spacing.md,
        marginBottom: spacing.lg,
        borderWidth: 1,
        borderColor: colors.border,
    },
    label: {
        color: colors.textSecondary,
        fontSize: typography.sm,
        marginBottom: spacing.xs,
    },
    inputRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: spacing.md,
    },
    input: {
        flex: 1,
        height: 50,
        backgroundColor: colors.background,
        borderRadius: spacing.sm,
        paddingHorizontal: spacing.md,
        color: colors.textMain,
        fontSize: typography.lg,
        borderWidth: 1,
        borderColor: colors.border,
    },
    optimizeButton: {
        backgroundColor: colors.primary,
        height: 50,
        paddingHorizontal: spacing.lg,
        borderRadius: spacing.sm,
        justifyContent: 'center',
        alignItems: 'center',
    },
    buttonText: {
        color: '#FFFFFF',
        fontWeight: 'bold',
        fontSize: typography.sm,
    },
    // Sentinel Card
    sentinelCard: {
        backgroundColor: '#1A2333', // Darker verified blue
        borderRadius: spacing.md,
        padding: spacing.md,
        marginBottom: spacing.lg,
        borderWidth: 1,
        borderColor: colors.primary,
    },
    sentinelHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: spacing.sm,
        gap: spacing.sm,
    },
    sentinelTitle: {
        color: colors.accentOrange,
        fontWeight: 'bold',
        fontSize: typography.md,
    },
    riskText: {
        color: colors.textWhite,
        fontSize: typography.md,
        fontStyle: 'italic',
        marginBottom: spacing.md,
        lineHeight: 22,
    },
    riskBadge: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    riskLabel: {
        color: colors.textLight,
        fontSize: typography.sm,
    },
    riskValue: {
        fontWeight: 'bold',
        fontSize: typography.sm,
    },
    // Bet Card
    betCard: {
        backgroundColor: colors.card,
        borderRadius: spacing.md,
        padding: spacing.md,
        marginBottom: spacing.md,
        borderLeftWidth: 4,
        borderLeftColor: colors.accentGreen,
    },
    betHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: spacing.sm,
    },
    matchText: {
        color: colors.textSecondary,
        fontSize: typography.sm,
    },
    oddsBadge: {
        backgroundColor: colors.background,
        paddingHorizontal: spacing.sm,
        paddingVertical: 2,
        borderRadius: 4,
    },
    oddsText: {
        color: colors.accentOrange,
        fontWeight: 'bold',
        fontSize: typography.sm,
    },
    betBody: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: spacing.sm,
    },
    selectionRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: spacing.sm,
    },
    selectionText: {
        color: colors.textMain,
        fontSize: typography.lg,
        fontWeight: 'bold',
    },
    stakeContainer: {
        alignItems: 'flex-end',
    },
    stakeLabel: {
        color: colors.textSecondary,
        fontSize: 10,
    },
    stakeValue: {
        color: colors.accentGreen,
        fontSize: typography.lg,
        fontWeight: 'bold',
    },
    betFooter: {
        borderTopWidth: 1,
        borderTopColor: colors.border,
        paddingTop: spacing.xs,
        marginTop: spacing.xs,
    },
    statusText: {
        color: colors.textSecondary,
        fontSize: 10,
    },
    placeholderContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        padding: spacing.xl,
        opacity: 0.5,
    },
    placeholderText: {
        color: colors.textSecondary,
        textAlign: 'center',
        marginTop: spacing.md,
        fontSize: typography.md,
    },
    emptyState: {
        padding: spacing.xl,
        alignItems: 'center',
    },
    emptyText: {
        color: colors.textSecondary,
        textAlign: 'center',
    }
});

export default SniperScreen;

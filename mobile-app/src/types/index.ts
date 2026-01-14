/**
 * NotiaBet Type Definitions
 */

// Prediction response from backend API
export interface Prediction {
    home_team: string;
    away_team: string;
    predicted_winner: string;
    home_win_probability: number;
    away_win_probability: number;
    winner_confidence: number;
    under_over_prediction: "UNDER" | "OVER";
    under_over_line: number;
    ou_confidence: number;
    home_odds: number;
    away_odds: number;
    start_time_utc: string; // ISO 8601
    timestamp: string;      // generated_at
    status?: string;        // 'SCHEDULED', 'LIVE', 'FINAL'
    home_score?: number;
    away_score?: number;
    actual_winner?: string; // For AIAudit
    stadium?: string;       // Stadium / Location
}

// API Response wrapper
export interface PredictionsResponse {
    count: number;
    predictions: Prediction[];
    generated_at: string;
}

// Health check response
export interface HealthResponse {
    status: string;
    model: string;
    timestamp: string;
}

// Expected Value calculation helper
export function calculateExpectedValue(
    probability: number,
    odds: number
): number {
    if (odds === 0) return 0;

    // American odds to decimal
    let decimalOdds: number;
    if (odds > 0) {
        decimalOdds = (odds / 100) + 1;
    } else {
        decimalOdds = (100 / Math.abs(odds)) + 1;
    }

    // EV = (probability * potentialWin) - (1 - probability) * stake
    const ev = (probability / 100) * (decimalOdds - 1) - (1 - probability / 100);
    return Math.round(ev * 100) / 100;
}

/**
 * Format game time for Colombia timezone (America/Bogota)
 * Returns format like "Hoy, 7:30 PM" or "Mañana, 8:00 PM"
 */
export function formatGameTime(isoString: string | null): string {
    if (!isoString) return '';

    try {
        const gameDate = new Date(isoString);
        const now = new Date();

        // Format time in Colombia timezone
        const timeStr = gameDate.toLocaleTimeString('es-CO', {
            timeZone: 'America/Bogota',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });

        // Get dates in Colombia timezone for comparison
        const gameDateLocal = new Date(gameDate.toLocaleString('en-US', { timeZone: 'America/Bogota' }));
        const todayLocal = new Date(now.toLocaleString('en-US', { timeZone: 'America/Bogota' }));

        const gameDay = gameDateLocal.toDateString();
        const today = todayLocal.toDateString();

        // Tomorrow
        const tomorrow = new Date(todayLocal);
        tomorrow.setDate(tomorrow.getDate() + 1);
        const tomorrowStr = tomorrow.toDateString();

        if (gameDay === today) {
            return `Hoy, ${timeStr}`;
        } else if (gameDay === tomorrowStr) {
            return `Mañana, ${timeStr}`;
        } else {
            // Format date for other days
            const dateStr = gameDateLocal.toLocaleDateString('es-CO', {
                timeZone: 'America/Bogota',
                weekday: 'short',
                day: 'numeric',
                month: 'short'
            });
            return `${dateStr}, ${timeStr}`;
        }
    } catch (e) {
        return '';
    }
}

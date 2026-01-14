/**
 * Odds Conversion Utilities
 * 
 * Handles conversion between American (Moneyline) and Decimal odds.
 */

export type OddsFormat = 'AMERICAN' | 'DECIMAL';

/**
 * Converts American odds to Decimal format.
 * @param american American odds (e.g., +150, -200)
 * @returns Decimal odds formatted to 2 decimal places (e.g., 2.50)
 */
export const americanToDecimal = (american: number): number => {
    if (american > 0) {
        return (american / 100) + 1;
    } else {
        return (100 / Math.abs(american)) + 1;
    }
};

/**
 * Formats odds based on the selected format.
 * Assumes input is always American (from backend).
 * 
 * @param odds American odds value
 * @param format Target format ('AMERICAN' | 'DECIMAL')
 * @returns Formatted string (e.g., "+150" or "2.50")
 */
export const formatOdds = (odds: number, format: OddsFormat): string => {
    // If backend returns 0 or invalid, just return dash
    if (odds === 0) return '-';

    if (format === 'DECIMAL') {
        const decimal = americanToDecimal(odds);
        return decimal.toFixed(2);
    }

    // Default American
    return odds > 0 ? `+${odds}` : `${odds}`;
};

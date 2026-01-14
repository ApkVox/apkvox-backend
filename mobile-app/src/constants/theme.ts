/**
 * NotiaBet Theme Constants
 * 
 * Clean Blue Design System
 */

// Theme constants matching external UI
export const colors = {
    background: '#F5F7FA',      // bg-background-light
    card: '#FFFFFF',            // bg-white

    // Brand
    primary: '#2962FF',         // text-primary
    primaryLight: '#E3F2FD',    // bg-pick-blue
    primaryShadow: 'rgba(41, 98, 255, 0.25)',

    // Accents
    accentGreen: '#00C853',     // text-mint
    accentGreenBg: 'rgba(0, 200, 83, 0.15)',
    accentOrange: '#FF9800',    // accent-orange
    accentOrangeBg: 'rgba(255, 152, 0, 0.12)',
    accentRed: '#FF1744',       // text-crimson (for recent form L)

    // Text
    textMain: '#1A1A1A',        // text-dark-grey
    textSecondary: '#455A64',   // text-cool-grey
    textLight: '#90A4AE',       // text-cool-grey lighter
    textWhite: '#FFFFFF',

    // Utility
    border: '#E8EDF2',
    divider: '#F0F4F8',
    shadow: 'rgba(0, 0, 0, 0.08)',

    // Web specific mappings
    mint: '#00C853',
    crimson: '#FF1744',
    coolGrey: '#90A4AE',
    darkGrey: '#1A1A1A',
};

export const spacing = {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 20,
    xxl: 24,
    xxxl: 32,
};

export const borderRadius = {
    sm: 8,
    md: 12,
    lg: 16,
    xl: 20,
    xxl: 24,
    pill: 100,
};

export const typography = {
    // Font sizes
    xs: 10,
    sm: 12,
    md: 14,
    lg: 16,
    xl: 18,
    xxl: 22,
    xxxl: 28,

    // Font weights (as strings for React Native)
    regular: '400' as const,
    medium: '500' as const,
    semiBold: '600' as const,
    bold: '700' as const,
};

export const shadows = {
    card: {
        shadowColor: colors.shadow,
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 1,
        shadowRadius: 12,
        elevation: 4,
    },
    button: {
        shadowColor: colors.primaryShadow,
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 1,
        shadowRadius: 8,
        elevation: 5,
    },
    subtle: {
        shadowColor: colors.shadow,
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 1,
        shadowRadius: 4,
        elevation: 2,
    },
};

export default {
    colors,
    spacing,
    borderRadius,
    typography,
    shadows,
};

/**
 * DateStrip Component
 * 
 * Ported from HomeView/DateStrip.tsx of web repo.
 * Horizontal list of dates with pill styling.
 */

import React, { useMemo, useRef, useEffect } from 'react';
import { View, ScrollView, TouchableOpacity, StyleSheet, Text } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, borderRadius, typography, shadows } from '../constants/theme';

interface DateStripProps {
    selectedDate: string; // YYYY-MM-DD
    onSelectDate: (date: string) => void;
}

// Constants for scroll calculation
const DATE_ITEM_WIDTH = 60 + 24; // minWidth + paddingHorizontal * 2
const DATE_ITEM_GAP = 12; // spacing.md

// Helpers - Use Intl.DateTimeFormat for accurate timezone conversion
function formatDateKey(date: Date): string {
    // Use Intl.DateTimeFormat to get Colombia date correctly
    return date.toLocaleDateString('en-CA', {
        timeZone: 'America/Bogota',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

export const DateStrip: React.FC<DateStripProps> = ({ selectedDate, onSelectDate }) => {
    const { t, i18n } = useTranslation();
    const scrollViewRef = useRef<ScrollView>(null);

    // Generate dates (10 days total: 7 past, Today, 2 future)
    const dates = useMemo(() => {
        const today = new Date();
        const result = [];

        for (let i = -7; i <= 2; i++) {
            const date = new Date(today);
            date.setDate(date.getDate() + i);

            const dateKey = formatDateKey(date);
            const dayNumber = date.getDate();

            let dayName = '';
            if (i === 0) {
                dayName = t('today'); // "HOY"
            } else if (i === 1) {
                dayName = i18n.language === 'es' ? 'MAÑ' : 'TMW';
            } else if (i === -1) {
                dayName = i18n.language === 'es' ? 'AYER' : 'YDA';
            } else {
                // Get 3 letter day name
                try {
                    dayName = date.toLocaleDateString(i18n.language, { weekday: 'short' }).toUpperCase();
                    // Remove dots if any (e.g. "LUN.")
                    dayName = dayName.replace('.', '');
                } catch (e) {
                    dayName = '...';
                }
            }

            result.push({
                key: dateKey,
                dayName,
                dayNumber,
                active: dateKey === selectedDate,
                index: i + 7 // Convert to 0-based index (today = 7)
            });
        }
        return result;
    }, [selectedDate, t, i18n.language]);

    // Auto-scroll to selected date whenever it changes
    useEffect(() => {
        // Find the index of the selected date
        const selectedIndex = dates.findIndex(d => d.key === selectedDate);

        if (selectedIndex !== -1 && scrollViewRef.current) {
            // Calculate position to center the item
            // Center = (ItemPos) - (ScreenHalf) + (ItemHalf)
            // But simplified: Index * (Width + Gap) - Offset to center

            // Assume screen width approx 360-400, center is ~180-200.
            // Item width is ~84. 
            // We want the item's center to be at the screen's center.
            // ScrollX = (Index * TotalItemWidth) - (ScreenWidth/2) + (TotalItemWidth/2)
            // Since we don't know exact screen width here easily without Dimensions, 
            // we can approximate or use a simple centering logic that works "good enough".
            // The previous logic used a fixed offset of 100 which is roughly half screen.

            const itemWidth = DATE_ITEM_WIDTH + DATE_ITEM_GAP;
            const scrollX = (selectedIndex * itemWidth) - 130; // 130 is approx half of screen width minus half item width

            // Small delay to ensure the ScrollView is rendered/layout updated
            setTimeout(() => {
                scrollViewRef.current?.scrollTo({
                    x: Math.max(0, scrollX),
                    animated: true
                });
            }, 100);
        }
    }, [selectedDate, dates]);

    return (
        <View style={styles.container}>
            <ScrollView
                ref={scrollViewRef}
                horizontal
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.scrollContent}
            >
                {dates.map((item) => (
                    <TouchableOpacity
                        key={item.key}
                        style={[
                            styles.dateItem,
                            item.active ? styles.dateItemActive : styles.dateItemInactive
                        ]}
                        onPress={() => onSelectDate(item.key)}
                        activeOpacity={0.8}
                    >
                        <Text style={[
                            styles.dayName,
                            item.active ? styles.textActiveLight : styles.textInactive
                        ]}>
                            {item.dayName}
                        </Text>
                        <Text style={[
                            styles.dateNumber,
                            item.active ? styles.textActive : styles.textMain
                        ]}>
                            {item.dayNumber}
                        </Text>
                    </TouchableOpacity>
                ))}
            </ScrollView>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        paddingVertical: spacing.sm,
    },
    scrollContent: {
        paddingHorizontal: spacing.lg,
        gap: spacing.md,
    },
    dateItem: {
        height: 56, // h-14 equivalent for touch
        minWidth: 60,
        borderRadius: borderRadius.lg, // rounded-xl
        alignItems: 'center',
        justifyContent: 'center',
        paddingHorizontal: spacing.lg,
        borderWidth: 1,
    },
    dateItemActive: {
        backgroundColor: colors.primary,
        borderColor: 'transparent',
        shadowColor: colors.primary,
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.2,
        shadowRadius: 8,
        elevation: 4,
    },
    dateItemInactive: {
        backgroundColor: colors.card,
        borderColor: colors.border,
    },
    dayName: {
        fontSize: 10,
        fontWeight: '700',
        textTransform: 'uppercase',
        letterSpacing: 0.5,
        marginBottom: 2,
    },
    dateNumber: {
        fontSize: 15,
        fontWeight: '800',
    },
    textActive: {
        color: colors.textWhite,
    },
    textActiveLight: {
        color: 'rgba(255, 255, 255, 0.7)',
    },
    textMain: {
        color: colors.textMain, // dark-grey
    },
    textInactive: {
        color: colors.textSecondary, // cool-grey
    },
});

export default DateStrip;

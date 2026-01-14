/**
 * ConfidenceRing Component
 * 
 * Circular progress indicator for prediction confidence.
 * Design inspired by external UI repo.
 */

import React from 'react';
import { View, StyleSheet, Text } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import { colors, typography } from '../constants/theme';

interface ConfidenceRingProps {
    percentage: number;
    size?: number;
    strokeWidth?: number;
    isHighValue?: boolean;
    showLabel?: boolean;
}

export const ConfidenceRing: React.FC<ConfidenceRingProps> = ({
    percentage,
    size = 48,
    strokeWidth = 3,
    isHighValue = false,
    showLabel = true,
}) => {
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;
    const center = size / 2;

    const progressColor = isHighValue ? colors.accentGreen : colors.primary;

    return (
        <View style={[styles.container, { width: size, height: size }]}>
            <Svg width={size} height={size}>
                {/* Background track */}
                <Circle
                    cx={center}
                    cy={center}
                    r={radius}
                    stroke={colors.border}
                    strokeWidth={strokeWidth}
                    fill="transparent"
                />
                {/* Progress arc */}
                <Circle
                    cx={center}
                    cy={center}
                    r={radius}
                    stroke={progressColor}
                    strokeWidth={strokeWidth}
                    fill="transparent"
                    strokeDasharray={`${circumference}`}
                    strokeDashoffset={strokeDashoffset}
                    strokeLinecap="round"
                    transform={`rotate(-90 ${center} ${center})`}
                />
            </Svg>
            {showLabel && (
                <View style={styles.labelContainer}>
                    <Text style={[
                        styles.label,
                        { color: isHighValue ? colors.accentGreen : colors.primary }
                    ]}>
                        {Math.round(percentage)}%
                    </Text>
                </View>
            )}
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        position: 'relative',
        justifyContent: 'center',
        alignItems: 'center',
    },
    labelContainer: {
        position: 'absolute',
        justifyContent: 'center',
        alignItems: 'center',
    },
    label: {
        fontSize: 11,
        fontWeight: '800',
    },
});

export default ConfidenceRing;

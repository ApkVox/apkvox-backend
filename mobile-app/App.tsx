/**
 * App.tsx - Root Component
 * 
 * Implements the "UI Swap" logic.
 * Manages navigation between Home and Details screens (ported from web logic).
 */

import React, { useState } from 'react';
import { StyleSheet, StatusBar, View, ActivityIndicator } from 'react-native';
import { PaperProvider, MD3LightTheme } from 'react-native-paper';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { NavigationContainer } from '@react-navigation/native';

import './src/i18n'; // Initialize i18n
import { colors, spacing, typography, borderRadius } from './src/constants/theme';
import { Prediction } from './src/types';
import { PreferencesProvider } from './src/context/PreferencesContext'; // Context

import HomeScreen from './src/screens/HomeScreen';
import DetailsScreen from './src/screens/DetailsScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import SniperScreen from './src/screens/SniperScreen';

// Custom Theme based on our centralized theme.ts
const paperTheme = {
  ...MD3LightTheme,
  colors: {
    ...MD3LightTheme.colors,
    primary: colors.primary,
    secondary: colors.accentOrange,
    background: colors.background,
    surface: colors.card,
  },
};

export default function App() {
  // Navigation State
  const [currentView, setCurrentView] = useState<'HOME' | 'DETAILS' | 'SETTINGS' | 'SNIPER'>('HOME');
  const [selectedPrediction, setSelectedPrediction] = useState<Prediction | null>(null);

  const handleGameSelect = (prediction: Prediction) => {
    setSelectedPrediction(prediction);
    setCurrentView('DETAILS');
  };

  const handleSettingsPress = () => {
    setCurrentView('SETTINGS');
  };

  const handleSniperPress = () => {
    setCurrentView('SNIPER');
  };

  const handleBack = () => {
    setCurrentView('HOME');
    setSelectedPrediction(null);
  };

  return (
    <PreferencesProvider>
      <NavigationContainer>
        <SafeAreaProvider>
          <PaperProvider theme={paperTheme}>
            <StatusBar barStyle="dark-content" backgroundColor="transparent" translucent />

            <SafeAreaView style={styles.container} edges={['top', 'left', 'right']}>
              {currentView === 'HOME' && (
                <HomeScreen
                  onGameSelect={handleGameSelect}
                  onSettingsPress={handleSettingsPress}
                  onSniperPress={handleSniperPress}
                />
              )}

              {currentView === 'DETAILS' && selectedPrediction && (
                <DetailsScreen
                  prediction={selectedPrediction}
                  onBack={handleBack}
                />
              )}

              {currentView === 'SETTINGS' && (
                <SettingsScreen onBack={handleBack} />
              )}

              {currentView === 'SNIPER' && (
                <SniperScreen onBack={handleBack} />
              )}
            </SafeAreaView>
          </PaperProvider>
        </SafeAreaProvider>
      </NavigationContainer>
    </PreferencesProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
});

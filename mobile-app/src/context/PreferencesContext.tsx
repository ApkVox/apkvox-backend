import React, { createContext, useState, useContext, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useTranslation } from 'react-i18next';
import { OddsFormat } from '../utils/odds';

interface PreferencesContextType {
    oddsFormat: OddsFormat;
    notifications: boolean;
    toggleOddsFormat: () => void;
    toggleNotifications: () => void;
    setLanguage: (lang: 'en' | 'es') => void;
    isLoading: boolean;
}

const PreferencesContext = createContext<PreferencesContextType | undefined>(undefined);

export const PreferencesProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { i18n } = useTranslation();
    const [oddsFormat, setOddsFormat] = useState<OddsFormat>('AMERICAN');
    const [notifications, setNotifications] = useState<boolean>(true);
    const [isLoading, setIsLoading] = useState(true);

    // Load saved preferences on mount
    useEffect(() => {
        const loadPreferences = async () => {
            try {
                const savedOdds = await AsyncStorage.getItem('pref_odds_format');
                const savedNotif = await AsyncStorage.getItem('pref_notifications');

                if (savedOdds) setOddsFormat(savedOdds as OddsFormat);
                if (savedNotif !== null) setNotifications(JSON.parse(savedNotif));
            } catch (error) {
                console.error('Failed to load preferences', error);
            } finally {
                setIsLoading(false);
            }
        };
        loadPreferences();
    }, []);

    const toggleOddsFormat = async () => {
        const newFormat = oddsFormat === 'AMERICAN' ? 'DECIMAL' : 'AMERICAN';
        setOddsFormat(newFormat);
        await AsyncStorage.setItem('pref_odds_format', newFormat);
    };

    const toggleNotifications = async () => {
        const newState = !notifications;
        setNotifications(newState);
        await AsyncStorage.setItem('pref_notifications', JSON.stringify(newState));
    };

    const setLanguage = async (lang: 'en' | 'es') => {
        i18n.changeLanguage(lang);
        await AsyncStorage.setItem('user-language', lang);
    };

    return (
        <PreferencesContext.Provider value={{
            oddsFormat,
            notifications,
            toggleOddsFormat,
            toggleNotifications,
            setLanguage,
            isLoading
        }}>
            {children}
        </PreferencesContext.Provider>
    );
};

export const usePreferences = () => {
    const context = useContext(PreferencesContext);
    if (!context) {
        throw new Error('usePreferences must be used within a PreferencesProvider');
    }
    return context;
};

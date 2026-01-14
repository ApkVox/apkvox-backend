import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Localization from 'expo-localization';

import en from './locales/en';
import es from './locales/es';

const RESOURCES = {
    en: { translation: en },
    es: { translation: es },
};

const LANGUAGE_DETECTOR = {
    type: 'languageDetector',
    async: true,
    detect: async (callback: (lang: string) => void) => {
        try {
            // 1. Check local storage
            const savedLanguage = await AsyncStorage.getItem('user-language');
            if (savedLanguage) {
                return callback(savedLanguage);
            }

            // 2. Check device locale
            const deviceLanguage = Localization.getLocales()[0]?.languageCode;
            if (deviceLanguage && ['en', 'es'].includes(deviceLanguage)) {
                return callback(deviceLanguage);
            }

            // 3. Fallback to Spanish (User request)
            return callback('es');
        } catch (error) {
            callback('es');
        }
    },
    init: () => { },
    cacheUserLanguage: async (language: string) => {
        try {
            await AsyncStorage.setItem('user-language', language);
        } catch (error) {
            console.log('Language caching error', error);
        }
    },
};

i18n
    //.use(LANGUAGE_DETECTOR as any) // Temporarily disabling detector to force initial logic in App.tsx if needed, or use simpler init
    .use(initReactI18next)
    .init({
        compatibilityJSON: 'v4',
        resources: RESOURCES,
        lng: 'es', // Force Spanish default as requested
        fallbackLng: 'es',
        interpolation: {
            escapeValue: false,
        },
    });

export default i18n;

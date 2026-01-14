/**
 * API Service for NotiaBet
 * 
 * Handles communication with the FastAPI backend
 * with mock fallback for development/no-games scenarios.
 */

import axios, { AxiosInstance } from 'axios';
import { Platform } from 'react-native';
import { Prediction, PredictionsResponse, HealthResponse } from '../types';

// ============================================================
// API Base URL Configuration
// ============================================================
// IMPORTANT: For physical device testing, use your machine's LAN IP
// Find your IP with: ipconfig (Windows) or ifconfig (Mac/Linux)
// Change this IP to match your network when switching WiFi networks

import Constants from 'expo-constants';

// ============================================================
// API Base URL Configuration
// ============================================================
// Automatically detects the Metro bundler IP (your computer's IP)
// This enables the app to connect without manual IP updates.

const getBaseUrl = (): string => {
    // 1. Try to get IP from Expo config (works in Expo Go)
    const debuggerHost = Constants.expoConfig?.hostUri;

    if (debuggerHost) {
        // debuggerHost is "192.168.x.x:8081". We split to get just the IP.
        const ip = debuggerHost.split(':')[0];
        return `http://${ip}:8000`;
    }

    // 2. Fallback for production or if detection fails
    // Use localhost (0.0.0.0) for Android Emulator / iOS Simulator
    if (!Constants.isDevice) {
        return 'http://0.0.0.0:8000';
    }

    // 3. PHYSICAL DEVICE FALLBACK
    // REPLACE THIS IP with your computer's LAN IP (e.g., 192.168.1.15)
    // Run 'ipconfig' (Windows) or 'ifconfig' (Mac) to find it.
    return 'http://192.168.18.9:8000'; // Update this if connection fails!
};

// ============================================================
// Mock Data for Testing (when no games available)
// ============================================================
const MOCK_PREDICTIONS: Prediction[] = [
    {
        home_team: "Los Angeles Lakers",
        away_team: "Golden State Warriors",
        predicted_winner: "Los Angeles Lakers",
        home_win_probability: 58.5,
        away_win_probability: 41.5,
        winner_confidence: 58.5,
        under_over_prediction: "OVER",
        under_over_line: 228.5,
        ou_confidence: 62.3,
        home_odds: -145,
        away_odds: 125,
        start_time_utc: new Date(Date.now() + 3600000).toISOString(), // 1 hour from now
        timestamp: new Date().toISOString(),
        status: 'SCHEDULED',
    },
    {
        home_team: "Boston Celtics",
        away_team: "Miami Heat",
        predicted_winner: "Boston Celtics",
        home_win_probability: 72.1,
        away_win_probability: 27.9,
        winner_confidence: 72.1,
        under_over_prediction: "UNDER",
        under_over_line: 215.0,
        ou_confidence: 55.8,
        home_odds: -280,
        away_odds: 230,
        start_time_utc: new Date(Date.now() - 7200000).toISOString(), // 2 hours ago
        timestamp: new Date().toISOString(),
        status: 'FINAL',
        home_score: 112,
        away_score: 108,
    },
    {
        home_team: "Denver Nuggets",
        away_team: "Phoenix Suns",
        predicted_winner: "Phoenix Suns",
        home_win_probability: 45.2,
        away_win_probability: 54.8,
        winner_confidence: 54.8,
        under_over_prediction: "OVER",
        under_over_line: 232.0,
        ou_confidence: 58.4,
        home_odds: 115,
        away_odds: -135,
        start_time_utc: new Date(Date.now() + 1800000).toISOString(), // 30 mins
        timestamp: new Date().toISOString(),
        status: 'LIVE',
        home_score: 45,
        away_score: 48,
    },
];

// ============================================================
// API Client
// ============================================================
class ApiService {
    private client: AxiosInstance;
    private useMock: boolean = false;

    constructor() {
        this.client = axios.create({
            baseURL: getBaseUrl(),
            timeout: 60000, // Increased to 60s for slow Backfill operations
            headers: {
                'Content-Type': 'application/json',
            },
        });
    }

    /**
     * Enable/disable mock mode
     */
    setMockMode(enabled: boolean): void {
        this.useMock = enabled;
    }

    /**
     * Check if backend is healthy
     */
    async checkHealth(): Promise<HealthResponse | null> {
        try {
            const response = await this.client.get<HealthResponse>('/health');
            return response.data;
        } catch (error) {
            console.log('[API] Health check failed:', error);
            return null;
        }
    }

    /**
     * Get predictions for a specific date (or today/upcoming if null)
     */
    async getPredictions(date?: string | null, sportsbook: string = 'fanduel'): Promise<Prediction[]> {
        // If mock mode is explicitly enabled, return mock data
        if (this.useMock) {
            console.log('[API] Mock mode enabled, returning mock data');
            return MOCK_PREDICTIONS;
        }

        try {
            console.log('[API] Fetching from:', this.client.defaults.baseURL, 'Date:', date);
            const params: any = { sportsbook };
            if (date) params.date = date;

            const response = await this.client.get<PredictionsResponse>(
                '/api/predictions',
                { params }
            );

            console.log('[API] Response status:', response.status);
            console.log('[API] Response count:', response.data?.count);

            // If we got predictions, return them
            if (response.data.predictions && response.data.predictions.length > 0) {
                console.log('[API] Got', response.data.predictions.length, 'predictions from backend');
                return response.data.predictions;
            }

            // No games today - fall back to mock data
            console.log('[API] No games today, using mock data for UI testing');
            return MOCK_PREDICTIONS;

        } catch (error: any) {
            console.log('[API] Request failed:', error?.message || error);
            console.log('[API] Using mock data as fallback');
            return MOCK_PREDICTIONS;
        }
    }
}

// Singleton instance
const apiService = new ApiService();

// Export functions
export const checkHealth = () => apiService.checkHealth();
export const getPredictions = (date?: string | null, sportsbook?: string) => apiService.getPredictions(date, sportsbook);
export const setMockMode = (enabled: boolean) => apiService.setMockMode(enabled);

export default apiService;

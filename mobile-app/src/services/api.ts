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
// Production URL - Render Cloud Server
const API_BASE_URL = "https://apkvox-api.onrender.com";
// Local Development URL (Your computer's IP)
// const API_BASE_URL = "http://192.168.18.9:8004";

// Strategy interfaces
export interface StrategyResponse {
    strategy: string;
    bankroll_used: number;
    proposed_bets: ProposedBet[];
    risk_analysis: RiskAnalysis;
}

export interface ProposedBet {
    prediction_id: string;
    date: string;
    match: string;
    selection: string;
    odds: number;
    stake_amount: number;
    status: string;
    is_real_bet: boolean;
}

export interface RiskAnalysis {
    advisor: string;
    message: string;
    exposure_rating: string;
}

const getBaseUrl = (): string => {
    return API_BASE_URL;
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

    /**
     * Get Strategy Optimization (The Sniper Engine)
     */
    async optimizeStrategy(bankroll: number): Promise<StrategyResponse | null> {
        try {
            const response = await this.client.post<StrategyResponse>('/api/strategy/optimize', { bankroll });
            return response.data;
        } catch (error) {
            console.log('[API] Strategy optimization failed:', error);
            return null;
        }
    }
}

// Singleton instance
const apiService = new ApiService();

// Export functions
export const checkHealth = () => apiService.checkHealth();
export const getPredictions = (date?: string | null, sportsbook?: string) => apiService.getPredictions(date, sportsbook);
export const optimizeStrategy = (bankroll: number) => apiService.optimizeStrategy(bankroll);
export const setMockMode = (enabled: boolean) => apiService.setMockMode(enabled);

export default apiService;

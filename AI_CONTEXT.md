# NotiaBet Project Context

## Overview
NotiaBet is a sports prediction application focusing on NBA games. It combines a Python FastAPI backend for data analysis/prediction and a React Native (Expo) mobile application for the user interface.

## Tech Stack
- **Backend**: Python 3.12+, FastAPI, Pandas, NumPy, XGBoost.
- **Frontend**: React Native, Expo (SDK 52+), TypeScript, React Navigation, React Native Paper.
- **Database**: SQLite (local on device), JSON/CSV for backend data persistence.
- **External APIs**: NBA.com API (via custom scraper), Live Score API.

## Architecture

### Backend (`/backend`)
The backend serves as the intelligence engine.
- `main.py`: Entry point, API routes (`/api/predictions`, `/health`, `/api/history`).
- `predictor.py`: Core logic. Fetches stats, runs XGBoost models (`xgb_ml`, `xgb_uo`), and generates predictions.
- `engine/`: Contains ML models and data processing scripts.
- `timezone.py`: Centralized timezone handling (America/New_York).

### Mobile App (`/mobile-app`)
The frontend is a cross-platform mobile app.
- `App.tsx`: Root component, Navigation setup.
- `src/screens/`:
    - `HomeScreen.tsx`: Main dashboard, lists upcoming games.
    - `DetailsScreen.tsx`: Detailed analysis for a specific game.
    - `SettingsScreen.tsx`: User preferences (Language, Odds format).
- `src/services/api.ts`: API client for communicating with the backend (auto-detects IP).
- `src/i18n/`: Internationalization (English/Spanish).

## Key Workflows
1.  **Prediction Generation**:
    - Backend runs on a schedule (or on request).
    - Fetches schedule and stats from NBA.com.
    - Predicts Winner (Moneyline) and Total Points (Over/Under).
    - Calculates "Confidence" and "Edge".
    - Returns JSON response.

2.  **Data Consumption**:
    - Mobile app fetches `/api/predictions`.
    - Displays "Next Games" and "Live Games".
    - User taps a game -> `DetailsScreen` shows specific insights.

## Project Structure
```
root/
├── backend/
│   ├── main.py
│   ├── predictor.py
│   ├── timezone.py
│   ├── engine/          # ML Models & Data
│   └── requirements.txt
├── mobile-app/
│   ├── App.tsx
│   ├── app.json
│   ├── src/
│   │   ├── components/  # Reusable UI (ConfidenceRing, MatchCard)
│   │   ├── screens/     # Page Views
│   │   ├── services/    # API & Logic
│   │   ├── i18n/        # Locales
│   │   └── types/       # TypeScript Interfaces
│   └── package.json
└── README.md
```

## Important Notes for AI Agents
- **Timezones**: Critical. Backend operates in EST (America/New_York). Frontend converts to local time.
- **Data Source**: Backend uses `nba-2025-UTC.csv` as a schedule source of truth.
- **New Architecture**: Expo "New Architecture" is currently DISABLED in `app.json` (removed config) to ensure stability with current libraries.

# NotiaBet - NBA Prediction App

Cross-platform mobile application providing AI-powered predictions for NBA games.

## Features
- **AI Predictions**: Machine learning models (XGBoost) predict game winners and over/under totals.
- **Live Scores**: Real-time updates for ongoing games.
- **Detailed Analysis**: Confidence ratings, value detection ("Edge"), and key metrics.
- **Multi-language**: Full support for English and Spanish.

## Architecture
- **Backend**: Python FastAPI with XGBoost engine.
- **Frontend**: React Native (Expo).

## Setup & Running

### Prerequisites
- Node.js & npm
- Python 3.12+
- Expo Go app on your physical device (iOS/Android)

### 1. Start the Backend
Navigate to the root directory and run:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
The server will start on port 8000.

### 2. Start the Mobile App
Open a new terminal in `mobile-app` directory:
```bash
cd mobile-app
npx expo start -c
```
Scan the QR code with Expo Go.

## Project Structure
See [AI_CONTEXT.md](./AI_CONTEXT.md) for detailed architectural documentation.

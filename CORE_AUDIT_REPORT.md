# CORE AUDIT REPORT - NotiaBet NBA Prediction Engine

**Fecha:** 2026-01-13  
**Motor:** NBA-Machine-Learning-Sports-Betting  
**Repositorio:** https://github.com/kyleskom/NBA-Machine-Learning-Sports-Betting

---

## 1. Mapa de Datos

### Ubicación de Almacenamiento
Los datos se almacenan en archivos **SQLite** dentro de la carpeta `nba_engine/Data/`:

| Archivo | Tamaño | Propósito |
|---------|--------|-----------|
| `TeamData.sqlite` | 87 MB | Datos históricos de equipos (stats por día) |
| `OddsData.sqlite` | 4.4 MB | Datos de cuotas de apuestas |
| `dataset.sqlite` | 35 MB | Dataset procesado para entrenamiento |

### Archivos CSV de Calendario
- `nba-2023-UTC.csv` - Calendario temporada 2023
- `nba-2024-UTC.csv` - Calendario temporada 2024
- `nba-2025-UTC.csv` - Calendario temporada 2025

### Modelos Pre-entrenados
Ubicados en `nba_engine/Models/`:
- `XGBoost_Models/` - Modelos XGBoost (.json + calibración .pkl)
- `NN_Models/` - Redes Neuronales Keras (.keras, .h5)

---

## 2. Punto de Inyección para Predicciones

### Función Principal
El flujo completo de predicción se orquesta desde **`nba_engine/main.py`**:

```python
# Archivo: main.py, línea 132
def main(args):
    # 1. Obtiene odds del sportsbook (opcional)
    odds = SbrOddsProvider(sportsbook=args.odds).get_odds()
    
    # 2. Resuelve los partidos de hoy
    games, odds = resolve_games(odds, args.odds)
    
    # 3. Obtiene stats actuales de NBA.com
    stats_json = get_json_data(DATA_URL)
    df = to_data_frame(stats_json)
    
    # 4. Prepara datos del partido
    data, todays_games_uo, frame_ml, home_team_odds, away_team_odds = create_todays_games_data(...)
    
    # 5. Ejecuta los modelos
    run_models(data, ...)
```

### Funciones de Predicción Específicas

#### XGBoost (Recomendado para API)
```python
# Archivo: src/Predict/XGBoost_Runner.py, línea 142
def xgb_runner(data, todays_games_uo, frame_ml, games, home_team_odds, away_team_odds, kelly_criterion):
    _load_models()  # Carga modelos globales
    ml_predictions_array = _predict_probs(xgb_ml, data, xgb_ml_calibrator)
    # Retorna: array de probabilidades [away_win, home_win]
```

#### Neural Network
```python
# Archivo: src/Predict/NN_Runner.py, línea 63
def nn_runner(data, todays_games_uo, frame_ml, games, home_team_odds, away_team_odds, kelly_criterion):
    _load_models()
    # Usa TensorFlow/Keras
```

---

## 3. Estrategia de API - Pseudo-código

### Problema Actual
El código original tiene `print()` statements embebidos que interfieren con una API limpia.

### Solución: Wrapper de Predicción Desacoplado

```python
# Archivo propuesto: api/predictor.py

import sys
from pathlib import Path

# Agregar nba_engine al path
NBA_ENGINE_PATH = Path(__file__).parent.parent / "nba_engine"
sys.path.insert(0, str(NBA_ENGINE_PATH))

# Suprimir prints del módulo original
import io
import contextlib

from src.Predict.XGBoost_Runner import _load_models, _predict_probs, xgb_ml, xgb_ml_calibrator
from src.Utils.tools import get_json_data, to_data_frame
import xgboost as xgb

class NBAPredictionService:
    """Servicio desacoplado de predicción NBA"""
    
    def __init__(self):
        self.models_loaded = False
    
    def load_models(self):
        """Carga modelos XGBoost en memoria"""
        with contextlib.redirect_stdout(io.StringIO()):
            _load_models()
        self.models_loaded = True
    
    def predict_game(self, home_team: str, away_team: str, game_data: dict) -> dict:
        """
        Retorna predicción estructurada sin prints.
        
        Returns:
            {
                "home_team": str,
                "away_team": str,
                "predicted_winner": str,
                "home_win_probability": float,
                "away_win_probability": float,
                "under_over": str,
                "ou_confidence": float
            }
        """
        if not self.models_loaded:
            self.load_models()
        
        # Preparar DMatrix para XGBoost
        dmatrix = xgb.DMatrix(game_data)
        predictions = xgb_ml.predict(dmatrix)
        
        home_prob = float(predictions[0][1])
        away_prob = float(predictions[0][0])
        
        return {
            "home_team": home_team,
            "away_team": away_team,
            "predicted_winner": home_team if home_prob > 0.5 else away_team,
            "home_win_probability": round(home_prob * 100, 2),
            "away_win_probability": round(away_prob * 100, 2),
        }

# Uso en FastAPI/Flask:
# 
# predictor = NBAPredictionService()
# predictor.load_models()  # Al iniciar servidor
# 
# @app.get("/predict/{home}/{away}")
# def get_prediction(home: str, away: str):
#     return predictor.predict_game(home, away, prepared_data)
```

### Puntos Clave de Integración

1. **Importar sin ejecutar CLI:**
   - No importar `main.py` directamente
   - Importar desde `src/Predict/XGBoost_Runner.py`

2. **Suprimir outputs:**
   - Usar `contextlib.redirect_stdout(io.StringIO())`
   - O modificar las funciones para aceptar flag `verbose=False`

3. **Datos requeridos por predicción:**
   - Stats actuales de ambos equipos (60+ features)
   - Días de descanso por equipo
   - Over/Under line (para predicción O/U)

---

## 4. Estado de Dependencias

### ⚠️ ADVERTENCIA CRÍTICA

| Librería | Versión Requerida | Estado |
|----------|-------------------|--------|
| colorama | 0.4.6 | ✅ Instalado |
| pandas | 2.1.1 | ✅ Instalado (última versión) |
| sbrscrape | 0.0.10 | ✅ Instalado |
| xgboost | 2.0.0 | ✅ Instalado (v3.1.3) |
| tqdm | 4.66.1 | ✅ Instalado |
| flask | 3.0.0 | ✅ Instalado |
| scikit-learn | 1.3.1 | ✅ Instalado |
| toml | 0.10.2 | ✅ Instalado |
| **tensorflow** | 2.14.0 | ❌ **NO COMPATIBLE** |

### Problema con TensorFlow

```
Python 3.14.0 detectado en el sistema.
TensorFlow NO soporta Python 3.14 (máximo soportado: Python 3.12).
```

### Soluciones Propuestas

1. **Usar solo XGBoost (Recomendado):**
   - El modelo XGBoost está completamente funcional
   - No requiere TensorFlow
   - Rendimiento similar al Neural Network

2. **Crear venv con Python 3.11/3.12:**
   ```bash
   py -3.11 -m venv venv_compat
   venv_compat\Scripts\activate
   pip install -r nba_engine/requirements.txt
   ```

3. **Modificar requirements.txt:**
   - Eliminar `tensorflow==2.14.0`
   - Agregar `tensorflow==2.18.0` (cuando soporte Py3.14)

---

## 5. Resumen Ejecutivo

| Aspecto | Estado |
|---------|--------|
| Repositorio clonado | ✅ OK |
| Entorno virtual | ✅ OK (`venv/`) |
| Dependencias XGBoost | ✅ OK |
| Dependencias TensorFlow | ❌ Incompatible |
| Modelos pre-entrenados | ✅ Incluidos |
| Datos históricos | ✅ SQLite |
| API-Ready | ⚠️ Requiere wrapper |

### Siguiente Paso Recomendado

Crear un módulo `api/predictor.py` que envuelva `XGBoost_Runner` para exponer predicciones via FastAPI sin dependencia de TensorFlow ni outputs de consola.

---

*Reporte generado automáticamente por auditoría de arquitectura NotiaBet*

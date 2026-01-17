
import pandas as pd
import numpy as np

class FeatureEngine:
    """
    Unified engine to calculate efficiency metrics and process features
    for both Training and Inference pipelines.
    """
    
    @staticmethod
    def calculate_efficiency_metrics(row):
        """
        Calculate efficiency metrics from base stats.
        Returns a Series with calculated metrics.
        """
        try:
            pts = float(row.get('PTS', 0))
            fga = float(row.get('FGA', 1))
            fta = float(row.get('FTA', 0))
            fgm = float(row.get('FGM', 0))
            fg3m = float(row.get('FG3M', 0))
            ast = float(row.get('AST', 0))
            tov = float(row.get('TOV', 1))
            oreb = float(row.get('OREB', 0))
            
            ts_attempts = 2 * (fga + 0.44 * fta)
            ts_pct = pts / ts_attempts if ts_attempts > 0 else 0
            efg_pct = (fgm + 0.5 * fg3m) / fga if fga > 0 else 0
            ast_tov = ast / tov if tov > 0 else ast
            pace_est = fga + 0.44 * fta - oreb + tov
            off_eff = (pts / pace_est * 100) if pace_est > 0 else 0
            
            return pd.Series({
                'TS_PCT': ts_pct,
                'EFG_PCT': efg_pct,
                'AST_TOV': ast_tov,
                'PACE_EST': pace_est,
                'OFF_EFF': off_eff
            })
        except Exception:
            return pd.Series({
                'TS_PCT': 0,
                'EFG_PCT': 0,
                'AST_TOV': 0,
                'PACE_EST': 0,
                'OFF_EFF': 0
            })

    @staticmethod
    def process_dataframe(df):
        """
        Apply efficiency calculations to an entire dataframe.
        """
        if df.empty:
            return df
            
        metrics = df.apply(FeatureEngine.calculate_efficiency_metrics, axis=1)
        return pd.concat([df, metrics], axis=1)

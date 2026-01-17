"""
Sentinel Agent (Risk Management AI)

Uses Groq API to analyze the daily betting portfolio and provide
risk management advice as if it were a senior portfolio manager.
"""

import os
import json
from groq import Groq
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

class SentinelAgent:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            print("⚠️ Sentinel Agent: No GROQ_API_KEY found.")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key)

    def analyze_risk(self, daily_bets: List[Dict], current_bankroll: float) -> str:
        """
        Analyzes the proposed bets and returns a risk warning/advice.
        """
        if not self.client:
            return "Sentinel Offline: API Key Missing."

        if not daily_bets:
            return "No hay apuestas propuestas para hoy. El capital está seguro."

        # Summarize bets for the LLM to save tokens
        total_stake = sum(b.get('stake_amount', 0) for b in daily_bets)
        exposure_pct = (total_stake / current_bankroll * 100) if current_bankroll > 0 else 0
        
        bet_summary = f"""
        Capital Actual: ${current_bankroll:,.2f}
        Total Apostado: ${total_stake:,.2f} ({exposure_pct:.2f}% del banco)
        Apuestas:
        """
        
        for bet in daily_bets[:10]: # Limit to top 10 to save context
            bet_summary += f"- {bet.get('selection')} @ {bet.get('odds')} (Stake: ${bet.get('stake_amount')})\n"
            
        system_prompt = (
            "Eres 'Sentinel', un Gestor de Riesgo de Inversiones Deportivas experto y conservador. "
            "Tu trabajo es proteger el capital. Analiza las apuestas propuestas."
            "Si la exposición es > 10%, lanza una advertencia severa."
            "Si hay muchas apuestas a 'Underdogs' (cuotas altas), advierte sobre la volatilidad."
            "Sé conciso (máximo 50 palabras). Habla en español profesional y directo."
        )

        try:
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": bet_summary}
                ],
                temperature=0.5,
                max_tokens=100
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Sentinel Error: {e}")
            return "Sentinel Offline: Error de conexión con IA."

# Singleton instance
sentinel = SentinelAgent()

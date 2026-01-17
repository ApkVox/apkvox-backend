
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from duckduckgo_search import DDGS
from pydantic import BaseModel, Field
from typing import List, Optional

# Load environment variables
load_dotenv()

class ImpactAnalysis(BaseModel):
    summary: str = Field(description="Resumen de 1 linea")
    impact_score: float = Field(description="Impacto de -10.0 a 10.0", ge=-10.0, le=10.0)
    key_factors: List[str] = Field(description="Lista de factores clave")
    confidence: int = Field(description="Nivel de confianza 1-100", ge=1, le=100)

class SportsInvestigator:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            # Fallback or warning if key is missing during init
            print("⚠️ WARNING: GROQ_API_KEY is missing via os.getenv(). Make sure .env is loaded.")
        self.groq_client = Groq(api_key=api_key)
        
    def search_news(self, query: str) -> str:
        """Search for news using DuckDuckGo with retries."""
        print(f"🔎 Buscando noticias sobre: {query}...")
        results = []
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                with DDGS() as ddgs:
                    # Search specifically for news in the last day (d=1)
                    # Note: 'timelimit' parameter might be 'd' for day or 'w' for week.
                    results = list(ddgs.news(query, region="wt-wt", safesearch="off", timelimit="d", max_results=5))
                    if results:
                        break # Success
            except Exception as e:
                print(f"⚠️ Intento {attempt+1}/{max_retries} fallido: {e}")
                import time
                time.sleep(1) # Wait before retry

        if not results:
            return "No se encontraron noticias recientes relevantes en las últimas 24h o hubo un error de conexión."
            
        context = ""
        for r in results:
            # Handle variations in DDG response keys
            date = r.get('date', 'Unknown Date')
            title = r.get('title', 'No Title')
            body = r.get('body', 'No Content')
            context += f"- [{date}] {title}: {body}\n"
        
        return context

    def analyze_impact(self, news_context: str, team_name: str) -> dict:
        """Analyze impact using Groq LLM with JSON mode."""
        if "Error" in news_context or "No se encontraron" in news_context:
             return {
                "summary": "No hay datos suficientes para análisis o error en búsqueda.",
                "impact_score": 0.0,
                "key_factors": ["Falta de información reciente"],
                "confidence": 0
            }

        print(f"🧠 Analizando impacto para {team_name}...")
        
        system_prompt = (
            "Eres un analista deportivo experto. Ignora el ruido, céntrate en lesiones confirmadas (OUT/DOUBTFUL) y fatiga. "
            "Si una estrella está fuera, el impacto es altamente negativo. "
            f"Analiza las siguientes noticias sobre {team_name} y determina el impacto en su próximo partido. "
            "Responde SIEMPRE con un objeto JSON válido que siga esta estructura: "
            "{'summary': str, 'impact_score': float (-10 a 10), 'key_factors': [str], 'confidence': int (0-100)}."
        )

        try:
            completion = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Noticias recientes:\n{news_context}"}
                ],
                temperature=0,
                response_format={"type": "json_object"} 
            )
            
            response_content = completion.choices[0].message.content
            return json.loads(response_content)
            
        except Exception as e:
            print(f"Error en LLM: {str(e)}")
            return {
                "summary": "Error en análisis AI",
                "impact_score": 0.0,
                "key_factors": [str(e)],
                "confidence": 0
            }

if __name__ == "__main__":
    # Test script setup
    target_team = "Golden State Warriors"
    
    # Check for API Key explicitly
    if not os.getenv("GROQ_API_KEY"):
        print("❌ Error: GROQ_API_KEY no encontrada. Asegúrate de tener el archivo .env configurado.")
        # Try to suggest setting it manually for the run if needed, but exiting is safer.
        # exit(1) # We won't exit hard in the tool call, just print error.
    else:
        investigator = SportsInvestigator()

        print(f"\n--- Iniciando Investigación para {target_team} ---")
        
        # 1. Search
        # Adding 'injuries' to query to be specific
        news = investigator.search_news(f"{target_team} injuries news")
        print(f"\n📰 Contexto Recopilado:\n{news}")
        
        # 2. Analyze
        analysis = investigator.analyze_impact(news, target_team)
        print(f"\n📊 Análisis de Impacto:\n{json.dumps(analysis, indent=2)}")

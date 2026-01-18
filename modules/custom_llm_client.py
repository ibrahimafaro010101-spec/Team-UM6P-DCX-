# Version simplifiée de llm_client.py
import os
import json
import pandas as pd
from typing import Dict, Any
from openai import OpenAI
import numpy as np


class OpenAIAnalyzer:
    """
    Client OpenAI simplifié
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Clé API OpenAI requise")

        self.api_key = api_key
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4.1"

    def analyze_query(self, query: str, dataframe: pd.DataFrame) -> Dict[str, Any]:
        """Analyse une requête avec les données"""
        try:
            # Résumé simple des données
            summary = f"Données: {len(dataframe)} lignes, {len(dataframe.columns)} colonnes. Colonnes: {', '.join(dataframe.columns[:10])}"

            prompt = f"""En tant qu'expert assurance, analysez cette question: {query}

            Contexte: {summary}

            Répondez en français avec: compréhension, méthodologie, insights."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Expert assurance automobile"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=800
            )

            result = response.choices[0].message.content

            return {
                "comprehension": "Analyse effectuée",
                "methodologie": "Analyse IA",
                "insights": ["Insight 1", "Insight 2"],
                "reponse_detaillee": result
            }

        except Exception as e:
            return {"erreur": str(e)}

    def process_query(self, prompt: str) -> str:
        """Traite une requête simple"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Erreur: {e}"


# Alias pour compatibilité
AdvancedOpenAIClient = OpenAIAnalyzer

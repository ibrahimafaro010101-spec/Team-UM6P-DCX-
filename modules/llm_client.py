import os
import json
import pandas as pd
from typing import Dict, Any, Optional
from openai import OpenAI
import numpy as np

class OpenAIAnalyzer:
    """
    Analyseur ChatBot par API KEY checking
    """

    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

        if not self.api_key:
            raise ValueError("Clé API OpenAI manquante")

        self.client = OpenAI(api_key=self.api_key)

    def analyze_query(self, query: str, dataframe: pd.DataFrame, context: Dict = None) -> Dict[str, Any]:
        """
        Analyse de questions
        """
        # Créer un résumé des données
        data_summary = {
            "nombre_lignes": len(dataframe),
            "nombre_colonnes": len(dataframe.columns),
            "colonnes": dataframe.columns.tolist()[:20],
            "types_donnees": {col: str(dtype) for col, dtype in dataframe.dtypes.items()},
            "statistiques": self._get_basic_stats(dataframe)
        }

        prompt = f"""
        Vous êtes un expert en analyse de données d'assurance automobile et très pertinent.

        DONNÉES DISPONIBLES :
        {json.dumps(data_summary, indent=2, ensure_ascii=False)}

        QUESTION DE L'UTILISATEUR :
        {query}

        CONTEXTE SUPPLÉMENTAIRE :
        {context if context else "Aucun contexte supplémentaire"}

        VOTRE MISSION :
        1. Comprendre la question métier
        2. Proposer une méthodologie d'analyse
        3. Suggérer des visualisations pertinentes
        4. Fournir des insights actionnables
        5. Fournir des codes de graphiques plotly ou PowerBI

        Répondez au format JSON avec cette structure :
        {{
            "comprehension": "Explication de la demande",
            "methodologie": "Comment analyser cela",
            "visualisations": ["type de graphique 1", "type de graphique 2"],
            "insights": ["insight 1", "insight 2"],
            "recommandations": ["recommandation 1", "recommandation 2"],
            "reponse_detaillee": "Réponse complète en français"
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Vous êtes un expert en analyse de données d'assurance."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )

            result_text = response.choices[0].message.content

            # Essayer de parser le JSON
            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                # Si ce n'est pas du JSON valide, retourner un format structuré
                return {
                    "comprehension": "Analyse effectuée",
                    "methodologie": "Analyse par IA OpenAI",
                    "visualisations": ["histogramme", "scatter plot"],
                    "insights": ["Insight généré par IA"],
                    "recommandations": ["Recommandation générée par IA"],
                    "reponse_detaillee": result_text
                }

        except Exception as e:
            return {
                "erreur": str(e),
                "reponse_detaillee": f"Erreur lors de l'analyse: {str(e)}"
            }

    def _get_basic_stats(self, df: pd.DataFrame) -> Dict:
        """Obtient des statistiques de base du DataFrame"""
        stats = {}

        # Pour les colonnes numériques
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols[:5]:  # Limiter aux 5 premières
            stats[col] = {
                "moyenne": float(df[col].mean()),
                "mediane": float(df[col].median()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "ecart_type": float(df[col].std())
            }

        return stats

    def generate_sql_query(self, query: str, table_name: str = "donnees") -> str:
        """
        Génère une requête SQL basée sur la question
        """
        prompt = f"""
        Génère une requête SQL pour répondre à cette question :
        {query}

        Table: {table_name}
        Retourne uniquement la requête SQL sans explications.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Vous êtes un expert SQL."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"-- Erreur: {str(e)}"

class OpenAIAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        ...

    def analyze_text(self, prompt: str) -> str:
        # implémentation existante
        ...

    # 🔥 MÉTHODE MANQUANTE (À AJOUTER)
    def process_query(self, prompt: str) -> str:
        return self.analyze_text(prompt)

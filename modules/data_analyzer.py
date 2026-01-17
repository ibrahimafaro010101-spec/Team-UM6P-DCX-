# modules/data_analyzer.py
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional


class DataAnalyzer:
    """
    Analyseur de données
    """

    def __init__(self, dataframe: pd.DataFrame):
        self.df = dataframe
        self.insights = []

    def get_basic_info(self) -> Dict[str, Any]:
        """Obtient les informations de base du DataFrame"""
        info = {
            "rows": len(self.df),
            "columns": len(self.df.columns),
            "missing_values": int(self.df.isna().sum().sum()),
            "duplicates": int(self.df.duplicated().sum()),
            "memory_usage_mb": self.df.memory_usage(deep=True).sum() / 1024 ** 2
        }

        # Types de données
        dtype_counts = self.df.dtypes.value_counts()
        info["dtypes"] = {str(k): int(v) for k, v in dtype_counts.items()}

        # Colonnes numériques et catégorielles
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = self.df.select_dtypes(include=['object', 'category']).columns.tolist()

        info["numeric_columns"] = numeric_cols
        info["categorical_columns"] = categorical_cols

        # Statistiques des colonnes numériques
        if numeric_cols:
            stats = {}
            for col in numeric_cols[:5]:  # Limiter aux 5 premières
                stats[col] = {
                    "mean": float(self.df[col].mean()),
                    "median": float(self.df[col].median()),
                    "std": float(self.df[col].std()),
                    "min": float(self.df[col].min()),
                    "max": float(self.df[col].max())
                }
            info["numeric_stats"] = stats

        return info

    def generate_insights(self) -> List[str]:
        """Génère des insights automatiques"""
        insights = []

        info = self.get_basic_info()

        # Insight sur la taille
        insights.append(f" **{info['rows']} lignes** et **{info['columns']} colonnes** analysées")

        # Insight sur les valeurs manquantes
        missing_pct = (info['missing_values'] / (info['rows'] * info['columns'])) * 100
        if missing_pct > 10:
            insights.append(f" **{missing_pct:.1f}% de valeurs manquantes** - Nettoyage nécessaire")
        elif missing_pct > 0:
            insights.append(f" **{missing_pct:.1f}% de valeurs manquantes**")
        else:
            insights.append("**Aucune valeur manquante**")

        # Insight sur les doublons
        if info['duplicates'] > 0:
            insights.append(f" **{info['duplicates']} doublons** détectés")

        # Insight sur les types de données
        if info['numeric_columns']:
            insights.append(f" **{len(info['numeric_columns'])} colonnes numériques** pour l'analyse statistique")

        # Insight sur les corrélations fortes
        if info['numeric_columns'] and len(info['numeric_columns']) >= 2:
            # Chercher une corrélation forte
            corr_matrix = self.df[info['numeric_columns']].corr().abs()
            np.fill_diagonal(corr_matrix.values, 0)
            max_corr = corr_matrix.max().max()

            if max_corr > 0.7:
                insights.append(f" **Forte corrélation détectée** ({max_corr:.2f}) entre certaines variables")

        self.insights = insights
        return insights

    def get_column_stats(self, column: str) -> Dict[str, Any]:
        """Obtient les statistiques d'une colonne spécifique"""
        if column not in self.df.columns:
            raise ValueError(f"Colonne '{column}' non trouvée")

        if pd.api.types.is_numeric_dtype(self.df[column]):
            return {
                "type": "numeric",
                "count": int(self.df[column].count()),
                "mean": float(self.df[column].mean()),
                "median": float(self.df[column].median()),
                "std": float(self.df[column].std()),
                "min": float(self.df[column].min()),
                "max": float(self.df[column].max()),
                "q25": float(self.df[column].quantile(0.25)),
                "q75": float(self.df[column].quantile(0.75))
            }
        else:
            # Pour les colonnes catégorielles
            value_counts = self.df[column].value_counts()
            return {
                "type": "categorical",
                "count": int(self.df[column].count()),
                "unique_values": int(self.df[column].nunique()),
                "top_values": value_counts.head(5).to_dict()
            }
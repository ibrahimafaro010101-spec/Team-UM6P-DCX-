# Importation et chargement
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional


class VisualizationGenerator:
    """
    Visualisations Plotly
    """

    def __init__(self, dataframe: pd.DataFrame):
        self.df = dataframe

    def create_histogram(self, column: str, title: str = None) -> go.Figure:
        """Histogramme"""
        if column not in self.df.columns:
            raise ValueError(f"Colonne '{column}' non trouvée")

        fig = px.histogram(
            self.df,
            x=column,
            title=title or f"Distribution de {column}",
            nbins=30
        )
        fig.update_layout(template="plotly_white")
        return fig

    def create_scatter(self, x_col: str, y_col: str, title: str = None) -> go.Figure:
        """Nuage de points"""
        if x_col not in self.df.columns or y_col not in self.df.columns:
            raise ValueError("Colonne(s) non trouvée(s)")

        fig = px.scatter(
            self.df,
            x=x_col,
            y=y_col,
            title=title or f"{x_col} vs {y_col}",
            trendline="ols"
        )
        fig.update_layout(template="plotly_white")
        return fig

    def create_bar_chart(self, x_col: str, y_col: str = None, title: str = None) -> go.Figure:
        """Diagramme en barres"""
        if x_col not in self.df.columns:
            raise ValueError(f"Colonne '{x_col}' non trouvée")

        if y_col:
            # Agrégation
            if y_col not in self.df.columns:
                raise ValueError(f"Colonne '{y_col}' non trouvée")

            # Grouper et agréger
            data = self.df.groupby(x_col)[y_col].mean().reset_index()
            fig = px.bar(
                data,
                x=x_col,
                y=y_col,
                title=title or f"{y_col} par {x_col}"
            )
        else:
            # Compter les occurrences
            value_counts = self.df[x_col].value_counts().reset_index()
            value_counts.columns = [x_col, 'count']
            fig = px.bar(
                value_counts.head(10),
                x=x_col,
                y='count',
                title=title or f"Top 10 - {x_col}"
            )

        fig.update_layout(template="plotly_white")
        return fig

    def create_correlation_heatmap(self, title: str = "Matrice de corrélation") -> go.Figure:
        """Crée une heatmap de corrélation"""
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns

        if len(numeric_cols) < 2:
            raise ValueError("Au moins 2 colonnes numériques sont nécessaires")

        corr_matrix = self.df[numeric_cols].corr()

        fig = px.imshow(
            corr_matrix,
            title=title,
            color_continuous_scale="RdBu",
            zmin=-1,
            zmax=1
        )
        fig.update_layout(template="plotly_white")
        return fig

    def create_box_plot(self, x_col: str, y_col: str, title: str = None) -> go.Figure:
        """Crée un box plot"""
        if x_col not in self.df.columns or y_col not in self.df.columns:
            raise ValueError("Colonne(s) non trouvée(s)")

        fig = px.box(
            self.df,
            x=x_col,
            y=y_col,
            title=title or f"Distribution de {y_col} par {x_col}"
        )
        fig.update_layout(template="plotly_white")
        return fig

    def auto_suggest_visualizations(self) -> List[Dict[str, Any]]:
        """Suggère automatiquement des visualisations"""
        suggestions = []

        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = self.df.select_dtypes(include=['object', 'category']).columns.tolist()

        # Suggestion 1: Distribution des colonnes numériques
        for col in numeric_cols[:3]:
            suggestions.append({
                "type": "histogram",
                "title": f"Distribution de {col}",
                "description": f"Histogramme montrant la distribution de {col}",
                "function": "create_histogram",
                "params": {"column": col}
            })

        # Suggestion 2: Corrélations entre variables numériques
        if len(numeric_cols) >= 2:
            suggestions.append({
                "type": "heatmap",
                "title": "Matrice de corrélation",
                "description": "Corrélations entre toutes les variables numériques",
                "function": "create_correlation_heatmap",
                "params": {}
            })

            # Ajouter un scatter plot pour la première paire
            suggestions.append({
                "type": "scatter",
                "title": f"{numeric_cols[0]} vs {numeric_cols[1]}",
                "description": f"Relation entre {numeric_cols[0]} et {numeric_cols[1]}",
                "function": "create_scatter",
                "params": {"x_col": numeric_cols[0], "y_col": numeric_cols[1]}
            })

        # Suggestion 3: Analyse par catégorie
        if categorical_cols and numeric_cols:
            cat_col = categorical_cols[0]
            if self.df[cat_col].nunique() <= 10:  # Si peu de catégories
                suggestions.append({
                    "type": "box",
                    "title": f"Distribution de {numeric_cols[0]} par {cat_col}",
                    "description": f"Comparaison de {numeric_cols[0]} entre les catégories de {cat_col}",
                    "function": "create_box_plot",
                    "params": {"x_col": cat_col, "y_col": numeric_cols[0]}
                })

        return suggestions
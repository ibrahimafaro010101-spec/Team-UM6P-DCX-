# modules/metadata_extractor.py
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import json


class MetadataExtractor:
    """
    Extrait les métadonnées sécurisées d'un DataFrame
    Sans exposer les données sensibles
    """

    def __init__(self, dataframe: pd.DataFrame):
        self.df = dataframe
        self.metadata = {}

    def extract_safe_metadata(self) -> Dict[str, Any]:
        """
        Extrait uniquement les métadonnées sécurisées
        (pas de données réelles, seulement des descriptions)
        """

        metadata = {
            "general_info": {
                "nombre_lignes": int(len(self.df)),
                "nombre_colonnes": int(len(self.df.columns)),
                "valeur_manquante_total": int(self.df.isna().sum().sum()),
                "doublons_total": int(self.df.duplicated().sum()),
                "taille_memoire_mo": float(self.df.memory_usage(deep=True).sum() / 1024 ** 2)
            },

            "structure_columns": self._extract_column_structure(),

            "statistical_profiles": self._extract_statistical_profiles(),

            "data_types_summary": self._extract_data_types_summary(),

            "quality_indicators": self._extract_quality_indicators(),

            "business_context_hints": self._infer_business_context()
        }

        self.metadata = metadata
        return metadata

    def _extract_column_structure(self) -> List[Dict[str, Any]]:
        """Structure des colonnes sans données réelles"""
        columns_info = []

        for col in self.df.columns:
            col_info = {
                "nom": str(col),
                "type_donnee": str(self.df[col].dtype),
                "valeurs_uniques": int(self.df[col].nunique()),
                "valeurs_manquantes": int(self.df[col].isna().sum()),
                "valeurs_manquantes_pct": float((self.df[col].isna().sum() / len(self.df)) * 100),
                "est_numerique": bool(pd.api.types.is_numeric_dtype(self.df[col])),
                "est_categorielle": bool(self.df[col].dtype == 'object' or self.df[col].dtype.name == 'category'),
                "est_datetime": bool(pd.api.types.is_datetime64_any_dtype(self.df[col])),
                "exemple_formats": self._get_example_formats(col)  # Formats, pas les données
            }
            columns_info.append(col_info)

        return columns_info

    def _extract_statistical_profiles(self) -> Dict[str, Any]:
        """Profils statistiques (sans données individuelles)"""
        profiles = {
            "variables_numeriques": [],
            "variables_categorielles": []
        }

        # Pour les variables numériques
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if not self.df[col].empty:
                profile = {
                    "nom": col,
                    "plage": {
                        "min": float(self.df[col].min()),
                        "max": float(self.df[col].max()),
                        "moyenne": float(self.df[col].mean()),
                        "mediane": float(self.df[col].median())
                    },
                    "distribution_type": self._infer_distribution_type(self.df[col])
                }
                profiles["variables_numeriques"].append(profile)

        # Pour les variables catégorielles
        categorical_cols = self.df.select_dtypes(include=['object', 'category']).columns
        for col in categorical_cols[:10]:  # Limiter aux 10 premières
            if not self.df[col].empty:
                value_counts = self.df[col].value_counts()
                profile = {
                    "nom": col,
                    "categories_count": int(len(value_counts)),
                    "top_categories_count": int(min(5, len(value_counts))),
                    "dominance": float(value_counts.iloc[0] / len(self.df) * 100) if len(value_counts) > 0 else 0
                }
                profiles["variables_categorielles"].append(profile)

        return profiles

    def _extract_data_types_summary(self) -> Dict[str, int]:
        """Résumé des types de données"""
        type_counts = self.df.dtypes.value_counts().to_dict()
        return {str(k): int(v) for k, v in type_counts.items()}

    def _extract_quality_indicators(self) -> Dict[str, float]:
        """Indicateurs de qualité"""
        total_cells = len(self.df) * len(self.df.columns)

        return {
            "completude_pct": float((1 - (self.df.isna().sum().sum() / total_cells)) * 100),
            "unicite_pct": float((1 - (self.df.duplicated().sum() / len(self.df))) * 100),
            "consistence_types": self._calculate_type_consistency()
        }

    def _infer_business_context(self) -> Dict[str, Any]:
        """Infère le contexte métier basé sur les noms de colonnes"""
        context = {
            "domaine_probable": "inconnu",
            "indicateurs_potentiels": [],
            "relations_potentielles": []
        }

        # Détection de domaine
        column_names = [str(col).lower() for col in self.df.columns]

        # Détection assurance
        insurance_keywords = ['prime', 'assur', 'sinistr', 'client', 'contrat', 'police', 'risque', 'couv']
        if any(any(keyword in col for keyword in insurance_keywords) for col in column_names):
            context["domaine_probable"] = "assurance"

            # Détection d'indicateurs d'assurance
            for col in self.df.columns:
                col_lower = str(col).lower()
                if any(word in col_lower for word in ['prime', 'montant', 'cout']):
                    context["indicateurs_potentiels"].append({"type": "financier", "colonne": col})
                elif any(word in col_lower for word in ['sinistr', 'accident', 'claim']):
                    context["indicateurs_potentiels"].append({"type": "risque", "colonne": col})
                elif any(word in col_lower for word in ['client', 'age', 'genre']):
                    context["indicateurs_potentiels"].append({"type": "demographique", "colonne": col})

        # Détection de relations potentielles
        numeric_cols = list(self.df.select_dtypes(include=[np.number]).columns)
        if len(numeric_cols) >= 2:
            context["relations_potentielles"] = [
                {"variables": numeric_cols[:2], "type": "correlation_numerique"}
            ]

        return context

    def _get_example_formats(self, column: str) -> List[str]:
        """Retourne des exemples de formats (pas les données)"""
        sample = self.df[column].dropna().head(3)
        formats = []

        for val in sample:
            if isinstance(val, (int, np.integer)):
                formats.append("entier")
            elif isinstance(val, (float, np.floating)):
                formats.append("decimal")
            elif isinstance(val, str):
                if val.replace('.', '').isdigit():
                    formats.append("chaine_numerique")
                else:
                    formats.append("texte")
            elif pd.api.types.is_datetime64_any_dtype(self.df[column]):
                formats.append("date_heure")
            else:
                formats.append("autre")

        return list(set(formats))[:2]

    def _infer_distribution_type(self, series: pd.Series) -> str:
        """Infère le type de distribution"""
        if len(series.dropna()) < 2:
            return "insuffisant"

        skew = float(series.skew())
        if abs(skew) > 1:
            return "asymetrique"
        elif abs(skew) > 0.5:
            return "legerement_asymetrique"
        else:
            return "symetrique"

    def _calculate_type_consistency(self) -> float:
        """Calcule la cohérence des types de données"""
        total = len(self.df.columns)
        consistent = 0

        for col in self.df.columns:
            # Vérifier si la colonne semble cohérente
            if self.df[col].dtype != 'object':
                consistent += 1
            else:
                # Pour les colonnes object, vérifier si elles semblent être du même type
                unique_types = set(type(x).__name__ for x in self.df[col].dropna().head(10))
                if len(unique_types) <= 2:
                    consistent += 1

        return float(consistent / total * 100) if total > 0 else 0.0

    def generate_schema_json(self) -> Dict[str, Any]:
        """Génère un schéma JSON sécurisé pour le LLM"""
        return {
            "schema_version": "1.0",
            "extraction_date": pd.Timestamp.now().isoformat(),
            "metadata": self.metadata,
            "note_securite": "Aucune donnee sensible incluse. Seulement des metadonnees structurelles."
        }
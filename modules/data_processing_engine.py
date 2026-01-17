# ============================================================
# data_processing_engine.py
# Moteur de traitement de données avancé pour l'assurance
# ============================================================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
from typing import Dict, List, Tuple, Optional, Any
import warnings

warnings.filterwarnings('ignore')


class DataProcessingEngine:
    """
    Moteur de traitement de données avancé pour l'assurance automobile
    Architecture pensée par un expert du domaine
    """

    def __init__(self):
        """Initialise le moteur avec des configurations expertes"""
        self.processing_steps = []
        self.metadata = {}
        self.quality_metrics = {}

        # Configurations spécifiques à l'assurance
        self.insurance_config = {
            'risk_categories': ['Faible', 'Moyen', 'Élevé', 'Très élevé'],
            'prime_brackets': [0, 1000, 5000, 15000, float('inf')],
            'age_groups': ['<25', '25-35', '35-45', '45-55', '55-65', '>65'],
            'vehicle_categories': ['Citadine', 'Berline', 'SUV', 'Utilitaire', 'Sportive', 'Luxe'],
            'coverage_types': ['Tiers', 'Tiers étendu', 'Tous risques']
        }

    # ========================================================
    # TRAITEMENTS FONDAMENTAUX
    # ========================================================

    def comprehensive_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Nettoyage complet des données d'assurance
        Approche systématique et robuste
        """
        original_shape = df.shape
        self.processing_steps.append({
            'step': 'Comprehensive Clean',
            'timestamp': datetime.now(),
            'original_shape': original_shape
        })

        df_clean = df.copy()

        # 1. Standardisation des noms de colonnes
        df_clean.columns = self._standardize_column_names(df_clean.columns)

        # 2. Traitement des valeurs manquantes par type
        df_clean = self._handle_missing_values(df_clean)

        # 3. Détection et traitement des outliers
        df_clean = self._handle_outliers(df_clean)

        # 4. Correction des types de données
        df_clean = self._correct_data_types(df_clean)

        # 5. Standardisation des formats
        df_clean = self._standardize_formats(df_clean)

        # 6. Validation des contraintes métier
        df_clean = self._validate_business_constraints(df_clean)

        # Mise à jour des métriques
        self.quality_metrics.update({
            'rows_removed': original_shape[0] - df_clean.shape[0],
            'columns_modified': len(set(df.columns) - set(df_clean.columns)),
            'completeness_score': self._calculate_completeness(df_clean),
            'consistency_score': self._calculate_consistency(df_clean)
        })

        self.processing_steps[-1]['final_shape'] = df_clean.shape
        self.processing_steps[-1]['quality_metrics'] = self.quality_metrics.copy()

        return df_clean

    def _standardize_column_names(self, columns: pd.Index) -> List[str]:
        """Standardisation experte des noms de colonnes"""
        column_mapping = {
            # Identifiants
            r'(?i)num.*cli': 'id_client',
            r'(?i)ref.*client': 'id_client',
            r'(?i)ncli': 'id_client',
            r'(?i)matricule': 'immatriculation',
            r'(?i)immat': 'immatriculation',

            # Démographie
            r'(?i)nom.*cli': 'nom_client',
            r'(?i)prenom.*cli': 'prenom_client',
            r'(?i)age': 'age',
            r'(?i)date.*nais': 'date_naissance',
            r'(?i)sexe': 'genre',

            # Véhicule
            r'(?i)marque': 'marque_vehicule',
            r'(?i)modele': 'modele_vehicule',
            r'(?i)type.*veh': 'type_vehicule',
            r'(?i)puissance': 'puissance_fiscale',
            r'(?i)cv': 'chevaux_fiscaux',

            # Prime et risque
            r'(?i)prime.*tot': 'prime_totale',
            r'(?i)montant.*prime': 'prime_annuelle',
            r'(?i)prime.*ann': 'prime_annuelle',
            r'(?i)risque': 'niveau_risque',
            r'(?i)score.*risq': 'score_risque',

            # Couverture
            r'(?i)nb.*jour.*couv': 'jours_couverture',
            r'(?i)duree.*contrat': 'duree_contrat',
            r'(?i)date.*effet': 'date_effet',
            r'(?i)date.*echeance': 'date_echeance',

            # Sinistres
            r'(?i)nb.*sinistre': 'nombre_sinistres',
            r'(?i)cout.*sinistre': 'cout_sinistres',
            r'(?i)freq.*sinistre': 'frequence_sinistres'
        }

        standardized = []
        for col in columns:
            col_str = str(col).strip().lower()
            matched = False
            for pattern, replacement in column_mapping.items():
                if re.search(pattern, col_str):
                    standardized.append(replacement)
                    matched = True
                    break
            if not matched:
                # Nettoyage basique
                clean_name = re.sub(r'[^a-zA-Z0-9]', '_', col_str)
                clean_name = re.sub(r'_+', '_', clean_name).strip('_')
                standardized.append(clean_name)

        return standardized

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Traitement intelligent des valeurs manquantes"""
        df_clean = df.copy()

        # Stratégie par type de colonne
        for col in df_clean.columns:
            if df_clean[col].dtype in ['int64', 'float64']:
                # Pour les numériques, imputation basée sur la distribution
                if df_clean[col].isna().sum() > 0:
                    if df_clean[col].skew() > 1:  # Distribution asymétrique
                        df_clean[col].fillna(df_clean[col].median(), inplace=True)
                    else:
                        df_clean[col].fillna(df_clean[col].mean(), inplace=True)

            elif df_clean[col].dtype == 'object':
                # Pour les catégorielles, mode ou 'Non spécifié'
                if df_clean[col].isna().sum() > 0:
                    mode_val = df_clean[col].mode()
                    df_clean[col].fillna(
                        mode_val[0] if not mode_val.empty else 'Non spécifié',
                        inplace=True
                    )

        return df_clean

    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Détection et traitement des outliers avec IQR amélioré"""
        df_clean = df.copy()

        for col in df_clean.select_dtypes(include=[np.number]).columns:
            if df_clean[col].nunique() > 10:  # Uniquement pour les variables continues
                Q1 = df_clean[col].quantile(0.25)
                Q3 = df_clean[col].quantile(0.75)
                IQR = Q3 - Q1

                # Bornes plus larges pour l'assurance (les primes peuvent varier)
                lower_bound = Q1 - 3 * IQR
                upper_bound = Q3 + 3 * IQR

                # Winsorization au lieu de suppression
                df_clean[col] = np.where(
                    df_clean[col] < lower_bound, lower_bound,
                    np.where(df_clean[col] > upper_bound, upper_bound, df_clean[col])
                )

        return df_clean

    def _correct_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Correction intelligente des types de données"""
        df_clean = df.copy()

        for col in df_clean.columns:
            # Détection des dates
            if any(keyword in col.lower() for keyword in ['date', 'jour', 'mois', 'annee', 'temps']):
                try:
                    df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')
                except:
                    pass

            # Détection des booléens
            elif df_clean[col].nunique() == 2:
                unique_vals = df_clean[col].dropna().unique()
                if set(map(str, unique_vals)) <= {'0', '1', 'true', 'false', 'oui', 'non'}:
                    df_clean[col] = df_clean[col].astype('bool')

            # Détection des catégories
            elif df_clean[col].dtype == 'object' and df_clean[col].nunique() < 50:
                df_clean[col] = pd.Categorical(df_clean[col])

        return df_clean

    # ========================================================
    # ENRICHISSEMENT DES DONNÉES (FEATURE ENGINEERING)
    # ========================================================

    def engineer_insurance_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Création de features métier pour l'assurance
        Approche basée sur l'expertise du domaine
        """
        df_enriched = df.copy()

        # 1. Features démographiques
        df_enriched = self._create_demographic_features(df_enriched)

        # 2. Features véhicule
        df_enriched = self._create_vehicle_features(df_enriched)

        # 3. Features risque
        df_enriched = self._create_risk_features(df_enriched)

        # 4. Features temporelles
        df_enriched = self._create_temporal_features(df_enriched)

        # 5. Features composites
        df_enriched = self._create_composite_features(df_enriched)

        # Enregistrement des features créées
        self.metadata['engineered_features'] = list(set(df_enriched.columns) - set(df.columns))

        return df_enriched

    def _create_demographic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Features démographiques pour scoring risque"""
        df_feat = df.copy()

        # Âge catégorisé (important pour l'assurance)
        if 'age' in df_feat.columns:
            bins = [0, 25, 35, 45, 55, 65, 100]
            labels = ['<25', '25-35', '35-45', '45-55', '55-65', '>65']
            df_feat['categorie_age'] = pd.cut(df_feat['age'], bins=bins, labels=labels)

            # Risque par âge (jeunes conducteurs = risque plus élevé)
            age_risk_map = {'<25': 3, '25-35': 2, '35-45': 1, '45-55': 1, '55-65': 2, '>65': 3}
            df_feat['risque_age'] = df_feat['categorie_age'].map(age_risk_map)

        # Expérience client (si date de naissance disponible)
        if 'date_naissance' in df_feat.columns and df_feat['date_naissance'].dtype == 'datetime64[ns]':
            df_feat['age_permis'] = (datetime.now() - df_feat['date_naissance']).dt.days / 365.25 - 18
            df_feat['age_permis'] = df_feat['age_permis'].clip(lower=0)
            df_feat['categorie_experience'] = pd.cut(
                df_feat['age_permis'],
                bins=[0, 2, 5, 10, float('inf')],
                labels=['Novice', 'Intermediaire', 'Experimente', 'Expert']
            )

        return df_feat

    def _create_vehicle_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Features liées au véhicule"""
        df_feat = df.copy()

        # Catégorie véhicule basée sur la marque/modèle
        if 'marque_vehicule' in df_feat.columns:
            # Mapping expert des marques par catégorie de risque
            marque_categories = {
                # Citadines (risque bas)
                'renault': 'Citadine', 'peugeot': 'Citadine', 'citroen': 'Citadine',
                'fiat': 'Citadine', 'toyota': 'Citadine', 'hyundai': 'Citadine',

                # Berlines (risque moyen)
                'bmw': 'Berline', 'mercedes': 'Berline', 'audi': 'Berline',
                'volkswagen': 'Berline', 'ford': 'Berline',

                # SUV (risque moyen-élevé)
                'land rover': 'SUV', 'jeep': 'SUV', 'porsche': 'SUV',

                # Sportives (risque élevé)
                'ferrari': 'Sportive', 'lamborghini': 'Sportive', 'mclaren': 'Sportive'
            }

            df_feat['categorie_vehicule'] = df_feat['marque_vehicule'].str.lower().map(
                lambda x: next((v for k, v in marque_categories.items() if k in str(x)), 'Autre')
            )

        # Prime par jour si durée disponible
        if all(col in df_feat.columns for col in ['prime_totale', 'jours_couverture']):
            df_feat['prime_par_jour'] = df_feat['prime_totale'] / df_feat['jours_couverture'].clip(lower=1)

        return df_feat

    def _create_risk_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Features de risque calculées"""
        df_feat = df.copy()

        # Score risque basique
        risk_factors = []

        if 'age' in df_feat.columns:
            # Jeunes conducteurs = risque plus élevé
            df_feat['facteur_age'] = np.where(df_feat['age'] < 25, 1.5,
                                              np.where(df_feat['age'] > 65, 1.3, 1.0))
            risk_factors.append('facteur_age')

        if 'nombre_sinistres' in df_feat.columns:
            # Historique sinistre
            df_feat['facteur_sinistre'] = 1 + (df_feat['nombre_sinistres'] * 0.3)
            risk_factors.append('facteur_sinistre')

        if 'prime_par_jour' in df_feat.columns:
            # Prime élevée peut indiquer risque élevé
            df_feat['facteur_prime'] = df_feat['prime_par_jour'] / df_feat['prime_par_jour'].median()
            risk_factors.append('facteur_prime')

        # Calcul du score risque composite
        if risk_factors:
            df_feat['score_risque_composite'] = df_feat[risk_factors].prod(axis=1)

            # Normalisation 0-100
            min_score = df_feat['score_risque_composite'].min()
            max_score = df_feat['score_risque_composite'].max()
            if max_score > min_score:
                df_feat['score_risque_normalise'] = (
                        (df_feat['score_risque_composite'] - min_score) / (max_score - min_score) * 100
                )

        return df_feat

    def _create_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Features temporelles pour analyse saisonnière"""
        df_feat = df.copy()

        # Extraction des composantes temporelles
        date_cols = df_feat.select_dtypes(include=['datetime64[ns]']).columns

        for col in date_cols:
            # Année, mois, jour, jour de la semaine
            df_feat[f'{col}_annee'] = df_feat[col].dt.year
            df_feat[f'{col}_mois'] = df_feat[col].dt.month
            df_feat[f'{col}_jour'] = df_feat[col].dt.day
            df_feat[f'{col}_jour_semaine'] = df_feat[col].dt.dayofweek
            df_feat[f'{col}_trimestre'] = df_feat[col].dt.quarter

            # Saisonnalité (important pour sinistres)
            df_feat[f'{col}_saison'] = df_feat[col].dt.month.map({
                12: 'Hiver', 1: 'Hiver', 2: 'Hiver',
                3: 'Printemps', 4: 'Printemps', 5: 'Printemps',
                6: 'Été', 7: 'Été', 8: 'Été',
                9: 'Automne', 10: 'Automne', 11: 'Automne'
            })

        return df_feat

    def _create_composite_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Features composites avancées"""
        df_feat = df.copy()

        # Ratio prime/âge (proxy pour risque)
        if all(col in df_feat.columns for col in ['prime_totale', 'age']):
            df_feat['ratio_prime_age'] = df_feat['prime_totale'] / df_feat['age'].clip(lower=18)

        # Densitité sinistres (sinistres par an d'expérience)
        if all(col in df_feat.columns for col in ['nombre_sinistres', 'age_permis']):
            df_feat['densite_sinistres'] = df_feat['nombre_sinistres'] / df_feat['age_permis'].clip(lower=1)

        # Prime ajustée au risque
        if all(col in df_feat.columns for col in ['prime_totale', 'score_risque_normalise']):
            df_feat['prime_ajustee_risque'] = df_feat['prime_totale'] * (df_feat['score_risque_normalise'] / 50)

        return df_feat

    # ========================================================
    # SEGMENTATION CLIENT
    # ========================================================

    def segment_clients(self, df: pd.DataFrame, method: str = 'rfm_risk') -> pd.DataFrame:
        """
        Segmentation des clients selon différentes méthodes

        Args:
            method: 'rfm_risk' (Recency, Frequency, Monetary + Risk),
                   'profitability', 'behavioral', 'comprehensive'
        """
        if method == 'rfm_risk':
            return self._segment_rfm_risk(df)
        elif method == 'profitability':
            return self._segment_profitability(df)
        elif method == 'behavioral':
            return self._segment_behavioral(df)
        else:
            return self._segment_comprehensive(df)

    def _segment_rfm_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        """Segmentation RFM adaptée à l'assurance"""
        df_seg = df.copy()

        # Initialisation des scores
        scores = {}

        # Recency (dernier sinistre ou dernière transaction)
        if 'date_dernier_sinistre' in df_seg.columns:
            recency = (datetime.now() - df_seg['date_dernier_sinistre']).dt.days
            scores['recency'] = pd.qcut(recency, q=5, labels=[5, 4, 3, 2, 1])

        # Frequency (fréquence des sinistres)
        if 'nombre_sinistres' in df_seg.columns:
            scores['frequency'] = pd.qcut(
                df_seg['nombre_sinistres'],
                q=5,
                labels=[1, 2, 3, 4, 5],
                duplicates='drop'
            )

        # Monetary (montant des primes)
        if 'prime_totale' in df_seg.columns:
            scores['monetary'] = pd.qcut(df_seg['prime_totale'], q=5, labels=[1, 2, 3, 4, 5])

        # Risk (niveau de risque)
        if 'score_risque_normalise' in df_seg.columns:
            scores['risk'] = pd.qcut(df_seg['score_risque_normalise'], q=5, labels=[1, 2, 3, 4, 5])

        # Combinaison des scores
        if scores:
            df_seg['segment_rfm'] = ''
            for name, score in scores.items():
                df_seg['segment_rfm'] += score.astype(str)

            # Mapping des segments
            segment_map = self._create_rfm_segments(df_seg['segment_rfm'])
            df_seg['segment_cluster'] = df_seg['segment_rfm'].map(segment_map)

        return df_seg

    def _create_rfm_segments(self, rfm_scores: pd.Series) -> Dict[str, str]:
        """Création des segments RFM"""
        segments = {
            # Clients idéaux
            '5555': 'Champions', '5554': 'Champions', '4555': 'Champions',
            # Clients fidèles
            '5545': 'Loyaux', '5455': 'Loyaux', '4554': 'Loyaux',
            # Clients à potentiel
            '4444': 'Potentiel', '3444': 'Potentiel', '4344': 'Potentiel',
            # Clients à risque
            '3333': 'À risque', '2333': 'À risque', '3233': 'À risque',
            # Clients perdus
            '2222': 'En danger', '1222': 'En danger', '2122': 'En danger',
            '1111': 'Perdus'
        }

        # Default mapping
        default_segments = {}
        for score in rfm_scores.unique():
            if score not in segments:
                # Classification basée sur le score moyen
                avg_score = sum(int(d) for d in str(score)) / len(str(score))
                if avg_score >= 4:
                    default_segments[score] = 'Haut potentiel'
                elif avg_score >= 3:
                    default_segments[score] = 'Moyen'
                elif avg_score >= 2:
                    default_segments[score] = 'Bas'
                else:
                    default_segments[score] = 'Très bas'

        segments.update(default_segments)
        return segments

    # ========================================================
    # ANALYSE DE QUALITÉ
    # ========================================================

    def analyze_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyse complète de la qualité des données
        Retourne des métriques détaillées
        """
        analysis = {
            'basic_stats': self._get_basic_stats(df),
            'completeness': self._analyze_completeness(df),
            'consistency': self._analyze_consistency(df),
            'accuracy': self._analyze_accuracy(df),
            'uniqueness': self._analyze_uniqueness(df),
            'timeliness': self._analyze_timeliness(df),
            'business_rules': self._check_business_rules(df)
        }

        # Score global de qualité
        weights = {
            'completeness': 0.25,
            'consistency': 0.20,
            'accuracy': 0.20,
            'uniqueness': 0.15,
            'timeliness': 0.10,
            'business_rules': 0.10
        }

        quality_score = 0
        for metric, weight in weights.items():
            if metric in analysis and 'score' in analysis[metric]:
                quality_score += analysis[metric]['score'] * weight

        analysis['overall_quality_score'] = round(quality_score, 2)
        analysis['quality_grade'] = self._get_quality_grade(quality_score)

        return analysis

    def _get_basic_stats(self, df: pd.DataFrame) -> Dict:
        """Statistiques de base"""
        return {
            'rows': df.shape[0],
            'columns': df.shape[1],
            'memory_mb': df.memory_usage(deep=True).sum() / 1024 / 1024,
            'dtypes_distribution': dict(df.dtypes.value_counts()),
            'numeric_columns': list(df.select_dtypes(include=[np.number]).columns),
            'categorical_columns': list(df.select_dtypes(include=['object', 'category']).columns),
            'date_columns': list(df.select_dtypes(include=['datetime64[ns]']).columns)
        }

    def _analyze_completeness(self, df: pd.DataFrame) -> Dict:
        """Analyse de la complétude"""
        missing_per_column = df.isnull().sum()
        missing_percentage = (missing_per_column / len(df) * 100).round(2)

        return {
            'total_missing': df.isnull().sum().sum(),
            'missing_per_column': missing_per_column.to_dict(),
            'missing_percentage': missing_percentage.to_dict(),
            'columns_with_missing': list(missing_percentage[missing_percentage > 0].index),
            'score': 100 - (df.isnull().sum().sum() / (df.shape[0] * df.shape[1]) * 100)
        }

    def _analyze_consistency(self, df: pd.DataFrame) -> Dict:
        """Analyse de la cohérence"""
        issues = []

        # Cohérence des formats
        for col in df.select_dtypes(include=['object']).columns:
            if df[col].nunique() < 100:  # Pour éviter les colonnes textuelles
                # Vérifier les formats incohérents
                unique_samples = df[col].dropna().unique()[:10]
                issues.append({
                    'column': col,
                    'issue': 'format_inconsistency',
                    'samples': list(unique_samples)
                })

        return {
            'issues_found': len(issues),
            'issues_details': issues,
            'score': max(0, 100 - len(issues) * 10)
        }

    def _get_quality_grade(self, score: float) -> str:
        """Conversion du score en grade"""
        if score >= 90:
            return 'A+ (Excellent)'
        elif score >= 80:
            return 'A (Très bon)'
        elif score >= 70:
            return 'B (Bon)'
        elif score >= 60:
            return 'C (Moyen)'
        elif score >= 50:
            return 'D (Faible)'
        else:
            return 'E (Critique)'

    # ========================================================
    # UTILITAIRES
    # ========================================================

    def get_processing_summary(self) -> Dict:
        """Résumé des traitements effectués"""
        return {
            'total_steps': len(self.processing_steps),
            'steps_details': self.processing_steps,
            'quality_metrics': self.quality_metrics,
            'engineered_features': self.metadata.get('engineered_features', []),
            'last_processed': datetime.now()
        }

    def export_quality_report(self, df: pd.DataFrame, format: str = 'html') -> str:
        """Génère un rapport de qualité"""
        analysis = self.analyze_data_quality(df)

        if format == 'html':
            return self._generate_html_report(analysis, df)
        else:
            return self._generate_text_report(analysis)

    def _generate_html_report(self, analysis: Dict, df: pd.DataFrame) -> str:
        """Génère un rapport HTML"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Rapport de Qualité des Données</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #1E3A8A; color: white; padding: 20px; border-radius: 10px; }}
                .section {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #f0f0f0; border-radius: 5px; }}
                .grade-A {{ color: green; font-weight: bold; }}
                .grade-B {{ color: orange; }}
                .grade-C {{ color: red; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Rapport de Qualité des Données</h1>
                <p>Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            </div>

            <div class="section">
                <h2>📈 Score Global de Qualité</h2>
                <div class="metric">
                    <h3>{analysis['overall_quality_score']}/100</h3>
                    <p class="grade-{analysis['quality_grade'][0]}">{analysis['quality_grade']}</p>
                </div>
                <div class="metric">
                    <h3>{analysis['basic_stats']['rows']:,}</h3>
                    <p>Lignes</p>
                </div>
                <div class="metric">
                    <h3>{analysis['basic_stats']['columns']}</h3>
                    <p>Colonnes</p>
                </div>
            </div>

            <div class="section">
                <h2>🔍 Détails par Métrique</h2>
                <table>
                    <tr>
                        <th>Métrique</th>
                        <th>Score</th>
                        <th>Détails</th>
                    </tr>
                    <tr>
                        <td>Complétude</td>
                        <td>{analysis['completeness']['score']:.1f}/100</td>
                        <td>{len(analysis['completeness']['columns_with_missing'])} colonnes avec valeurs manquantes</td>
                    </tr>
                    <tr>
                        <td>Cohérence</td>
                        <td>{analysis['consistency']['score']:.1f}/100</td>
                        <td>{analysis['consistency']['issues_found']} problèmes détectés</td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <h2>📋 Types de Données</h2>
                <table>
                    <tr>
                        <th>Type</th>
                        <th>Nombre</th>
                        <th>Exemples</th>
                    </tr>
                    <tr>
                        <td>Numériques</td>
                        <td>{len(analysis['basic_stats']['numeric_columns'])}</td>
                        <td>{', '.join(analysis['basic_stats']['numeric_columns'][:3])}...</td>
                    </tr>
                    <tr>
                        <td>Catégorielles</td>
                        <td>{len(analysis['basic_stats']['categorical_columns'])}</td>
                        <td>{', '.join(analysis['basic_stats']['categorical_columns'][:3])}...</td>
                    </tr>
                </table>
            </div>
        </body>
        </html>
        """
        return html

    def _generate_text_report(self, analysis: Dict) -> str:
        """Génère un rapport texte"""
        report = f"""
        ===========================================
        RAPPORT DE QUALITÉ DES DONNÉES
        Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}
        ===========================================

        SCORE GLOBAL: {analysis['overall_quality_score']}/100
        GRADE: {analysis['quality_grade']}

        STATISTIQUES DE BASE:
        - Lignes: {analysis['basic_stats']['rows']:,}
        - Colonnes: {analysis['basic_stats']['columns']}
        - Mémoire: {analysis['basic_stats']['memory_mb']:.1f} MB

        MÉTRIQUES DÉTAILLÉES:
        1. Complétude: {analysis['completeness']['score']:.1f}/100
           • Colonnes avec valeurs manquantes: {len(analysis['completeness']['columns_with_missing'])}

        2. Cohérence: {analysis['consistency']['score']:.1f}/100
           • Problèmes détectés: {analysis['consistency']['issues_found']}

        TYPES DE DONNÉES:
        • Numériques: {len(analysis['basic_stats']['numeric_columns'])} colonnes
        • Catégorielles: {len(analysis['basic_stats']['categorical_columns'])} colonnes
        • Dates: {len(analysis['basic_stats']['date_columns'])} colonnes

        ===========================================
        """
        return report
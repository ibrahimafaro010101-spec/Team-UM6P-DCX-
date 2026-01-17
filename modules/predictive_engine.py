# =================================================
# predictive_engine.py — Modèles prédictifs
# =================================================

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
    precision_recall_curve, roc_curve, matthews_corrcoef,
    cohen_kappa_score, balanced_accuracy_score, log_loss,
    brier_score_loss, average_precision_score
)
import joblib
import plotly.graph_objects as go
import plotly.express as px
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
import warnings
import streamlit as st

warnings.filterwarnings('ignore')

# Importation conditionnelle de CatBoost et XGBoost
try:
    from catboost import CatBoostClassifier

    CATBOOST_AVAILABLE = True
except ImportError:
    CATBOOST_AVAILABLE = False
    st.warning("⚠️ CatBoost n'est pas installé. Installation recommandée: pip install catboost")

try:
    from xgboost import XGBClassifier

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    st.warning("⚠️ XGBoost n'est pas installé. Installation recommandée: pip install xgboost")


class PredictiveEngine:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.imputer = SimpleImputer(strategy='median')
        self.label_encoders = {}
        self.feature_importance = None
        self.threshold_optimized = 0.5
        self.model_type = None
        self.target_binary = False
        self.cat_features = []
        self.train_metrics = None
        self.test_metrics = None

    def prepare_training_data(self, df, target_col, test_size=0.2, random_state=42):
        """
        Prépare les données pour l'entraînement avec gestion des déséquilibres
        """
        # Vérifier que la colonne cible existe
        if target_col not in df.columns:
            raise ValueError(f"La colonne cible '{target_col}' n'existe pas dans les données.")

        # Créer une copie pour éviter les modifications sur l'original
        df_processed = df.copy()

        # ANALYSE DE LA VARIABLE CIBLE
        y = df_processed[target_col]
        unique_values = y.nunique()
        value_counts = y.value_counts()

        st.info(f"Analyse de la variable cible '{target_col}':")
        st.info(f"- Nombre de classes uniques: {unique_values}")
        st.info(f"- Distribution: {dict(value_counts.head(10))}")

        # Détection automatique du type de problème
        if unique_values == 2:
            # Problème de classification binaire
            self.target_binary = True
            st.success("✅ Classification binaire détectée")

        elif unique_values > 2 and unique_values <= 10:
            # Problème de classification multi-classes (max 10 classes)
            self.target_binary = False
            if value_counts.min() < 5:
                st.warning(f"⚠️ Certaines classes ont très peu d'échantillons (min: {value_counts.min()})")
            st.info(f"Classification multi-classes ({unique_values} classes)")

        else:
            # Trop de classes - créer une variable binaire à partir de la distribution
            st.warning(f"⚠️ Trop de classes ({unique_values}). Création d'une variable cible binaire...")

            # Option 1: Si la colonne contient des codes risque
            if any(keyword in target_col.lower() for keyword in ['risque', 'risk', 'niveau', 'classe', 'grade']):
                # Garder les 20% des classes les plus rares comme risque élevé
                threshold = value_counts.quantile(0.2)
                rare_classes = value_counts[value_counts <= threshold].index
                y_binary = y.isin(rare_classes).astype(int)
                st.info(
                    f"Classes rares considérées comme risque ({len(rare_classes)} classes): {list(rare_classes)[:10]}")

            # Option 2: Basé sur les quantiles (si numérique)
            elif pd.api.types.is_numeric_dtype(y):
                threshold = y.quantile(0.75)  # Top 25% = risque élevé
                y_binary = (y >= threshold).astype(int)
                st.info(f"Seuil de risque: valeurs >= {threshold:.2f}")

            # Option 3: Par défaut, risque = 20% des échantillons les plus rares
            else:
                # Sélectionner 20% des échantillons comme risque
                n_risk = int(len(y) * 0.2)
                # Identifier les classes avec le moins d'occurrences
                rare_samples = y.value_counts().nsmallest(n_risk).index
                y_binary = y.isin(rare_samples).astype(int)
                st.info(f"20% des échantillons les plus rares considérés comme risque")

            # Remplacer y par la variable binaire
            y = y_binary
            df_processed[target_col] = y
            self.target_binary = True
            st.success(f"✅ Variable cible binaire créée. Distribution: {y.value_counts().to_dict()}")

        # Identifier les features catégorielles pour CatBoost
        categorical_cols = df_processed.select_dtypes(include=['object', 'category']).columns.tolist()
        if target_col in categorical_cols:
            categorical_cols.remove(target_col)
        self.cat_features = categorical_cols

        # Séparer features et target
        X = df_processed.drop(columns=[target_col])

        # Encodage des variables catégorielles (pour RandomForest et XGBoost)
        X = self._encode_categorical_features(X)

        # Imputation des valeurs manquantes
        X_imputed = self.imputer.fit_transform(X)
        X = pd.DataFrame(X_imputed, columns=X.columns)

        # Normalisation des features (sauf pour les arbres qui n'en ont pas besoin)
        # Mais utile pour la cohérence
        X_scaled = self.scaler.fit_transform(X)
        X = pd.DataFrame(X_scaled, columns=X.columns)

        # Diviser en train/test - SANS stratification si trop peu d'échantillons par classe
        if self.target_binary and y.nunique() == 2:
            min_class_count = y.value_counts().min()
            if min_class_count >= 2:
                # Stratification possible
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=test_size, random_state=random_state, stratify=y
                )
            else:
                # Pas assez d'échantillons pour stratification
                st.warning("⚠️ Pas assez d'échantillons pour la stratification")
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=test_size, random_state=random_state
                )
        else:
            # Pas de stratification pour multi-classes ou classification non binaire
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state
            )

        # Gérer le déséquilibre des classes avec SMOTE (seulement pour classification binaire)
        if self.target_binary and y_train.nunique() == 2:
            class_counts = y_train.value_counts()
            st.info(f"Distribution avant SMOTE: {class_counts.to_dict()}")

            if class_counts.min() >= 2:  # Au moins 2 échantillons par classe
                try:
                    smote = SMOTE(random_state=random_state, sampling_strategy='auto')
                    X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)

                    st.info(f"Distribution après SMOTE: {pd.Series(y_train_resampled).value_counts().to_dict()}")

                    return X_train_resampled, X_test, y_train_resampled, y_test
                except Exception as e:
                    st.warning(f"SMOTE échoué: {e}. Utilisation des données originales.")

        return X_train, X_test, y_train, y_test

    def _encode_categorical_features(self, X):
        """Encode les variables catégorielles pour RandomForest et XGBoost"""
        X_encoded = X.copy()

        for col in X_encoded.select_dtypes(include=['object', 'category']).columns:
            # Ne pas encoder les colonnes avec trop de catégories
            if X_encoded[col].nunique() > 50:
                st.warning(f"Colonne '{col}' a trop de catégories ({X_encoded[col].nunique()}). Suppression.")
                X_encoded = X_encoded.drop(columns=[col])
                continue

            le = LabelEncoder()
            X_encoded[col] = le.fit_transform(X_encoded[col].astype(str))
            self.label_encoders[col] = le

        return X_encoded

    def train_model(self, X_train, y_train, model_type='random_forest', optimize=True):
        """
        Entraîne un modèle de prédiction du risque client
        """
        self.model_type = model_type

        # Vérifier la taille des données
        n_samples = len(X_train)
        n_features = X_train.shape[1]
        st.info(f"Nombre d'échantillons d'entraînement: {n_samples}")
        st.info(f"Nombre de features: {n_features}")

        # Préparer les données catégorielles pour CatBoost
        cat_features_indices = []
        if model_type == 'catboost' and CATBOOST_AVAILABLE:
            # Identifier les indices des colonnes catégorielles
            for i, col in enumerate(X_train.columns):
                if col in self.cat_features:
                    cat_features_indices.append(i)
            st.info(f"CatBoost utilisera {len(cat_features_indices)} features catégorielles")

        if n_samples < 50:
            st.warning("⚠️ Très peu d'échantillons. Utilisation de RandomForest par défaut.")
            model_type = 'random_forest'

        if model_type == 'random_forest':
            # Définir les hyperparamètres adaptés à la taille des données
            if n_samples < 100:
                param_grid = {
                    'n_estimators': [50, 100],
                    'max_depth': [3, 5, 10],
                    'min_samples_split': [2, 5],
                    'min_samples_leaf': [1, 2],
                    'max_features': ['sqrt', 'log2']
                }
            else:
                param_grid = {
                    'n_estimators': [100, 200],
                    'max_depth': [5, 10, 15, None],
                    'min_samples_split': [2, 5, 10],
                    'min_samples_leaf': [1, 2, 4],
                    'max_features': ['sqrt', 'log2'],
                    'class_weight': ['balanced', 'balanced_subsample'] if self.target_binary else [None]
                }

            base_model = RandomForestClassifier(
                random_state=42,
                n_jobs=-1,
                oob_score=True,
                class_weight='balanced' if self.target_binary else None
            )

        elif model_type == 'catboost':
            if not CATBOOST_AVAILABLE:
                st.error("❌ CatBoost n'est pas installé. Veuillez installer avec: pip install catboost")
                st.info("Utilisation de RandomForest à la place.")
                return self.train_model(X_train, y_train, 'random_forest', optimize)

            # Paramètres pour CatBoost
            param_grid = {
                'iterations': [100, 200, 300],
                'depth': [4, 6, 8],
                'learning_rate': [0.01, 0.05, 0.1],
                'l2_leaf_reg': [1, 3, 5],
                'border_count': [32, 64, 128]
            }

            if n_samples < 100:
                # Réduire la complexité pour petits datasets
                param_grid = {
                    'iterations': [50, 100],
                    'depth': [3, 4, 6],
                    'learning_rate': [0.05, 0.1],
                    'l2_leaf_reg': [3, 5]
                }

            base_model = CatBoostClassifier(
                random_state=42,
                verbose=0,  # Désactiver les logs
                cat_features=cat_features_indices,
                auto_class_weights='Balanced' if self.target_binary else None
            )

        elif model_type == 'xgboost':
            if not XGBOOST_AVAILABLE:
                st.error("❌ XGBoost n'est pas installé. Veuillez installer avec: pip install xgboost")
                st.info("Utilisation de RandomForest à la place.")
                return self.train_model(X_train, y_train, 'random_forest', optimize)

            # Paramètres pour XGBoost
            param_grid = {
                'n_estimators': [100, 200],
                'max_depth': [3, 5, 7],
                'learning_rate': [0.01, 0.05, 0.1],
                'subsample': [0.8, 1.0],
                'colsample_bytree': [0.8, 1.0],
                'gamma': [0, 0.1, 0.2]
            }

            if n_samples < 100:
                param_grid = {
                    'n_estimators': [50, 100],
                    'max_depth': [3, 5],
                    'learning_rate': [0.05, 0.1]
                }

            base_model = XGBClassifier(
                random_state=42,
                n_jobs=-1,
                use_label_encoder=False,
                eval_metric='logloss',
                scale_pos_weight=(len(y_train) - sum(y_train)) / sum(y_train) if self.target_binary and sum(
                    y_train) > 0 else 1
            )

        else:
            raise ValueError(f"Type de modèle non supporté: {model_type}")

        # Optimisation des hyperparamètres
        if optimize and n_samples >= 30 and X_train.shape[1] >= 2:
            try:
                # Réduire la grille si peu d'échantillons
                if n_samples < 100:
                    # Simplifier la grille
                    simplified_grid = {}
                    for key in list(param_grid.keys()):
                        simplified_grid[key] = [param_grid[key][0]]  # Prendre seulement la première valeur
                    param_grid = simplified_grid

                # Ajuster le nombre de folds pour la cross-validation
                n_folds = min(3, max(2, n_samples // 10))

                grid_search = GridSearchCV(
                    estimator=base_model,
                    param_grid=param_grid,
                    cv=n_folds,
                    scoring='f1' if self.target_binary else 'accuracy',
                    n_jobs=-1,
                    verbose=0
                )

                with st.spinner(f"Optimisation des hyperparamètres ({model_type})..."):
                    grid_search.fit(X_train, y_train)

                self.model = grid_search.best_estimator_

                st.success(f"✅ Meilleurs paramètres: {grid_search.best_params_}")
                st.success(f"✅ Meilleur score CV: {grid_search.best_score_:.3f}")

            except Exception as e:
                st.warning(f"⚠️ Échec de l'optimisation: {e}. Utilisation du modèle par défaut.")
                self.model = base_model
                with st.spinner(f"Entraînement du modèle {model_type}..."):
                    self.model.fit(X_train, y_train)
        else:
            self.model = base_model
            with st.spinner(f"Entraînement du modèle {model_type}..."):
                self.model.fit(X_train, y_train)

        # Calcul de l'importance des features
        if hasattr(self.model, 'feature_importances_'):
            self.feature_importance = pd.DataFrame({
                'feature': X_train.columns,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)

            st.info("📊 Importance des features calculée")

        # Calcul des métriques sur l'ensemble d'entraînement
        self._compute_train_metrics(X_train, y_train)

        # Optimisation du seuil de classification (seulement pour classification binaire)
        if self.target_binary and hasattr(self.model, 'predict_proba'):
            self._optimize_threshold(X_train, y_train)

        st.success(f"✅ Modèle {model_type} entraîné avec succès!")

    def _compute_train_metrics(self, X_train, y_train):
        """Calcule les métriques sur l'ensemble d'entraînement"""
        predictions, probabilities = self.predict(X_train, use_optimized_threshold=False)

        self.train_metrics = {
            'accuracy': accuracy_score(y_train, predictions),
            'precision': precision_score(y_train, predictions, zero_division=0,
                                         average='weighted' if not self.target_binary else 'binary'),
            'recall': recall_score(y_train, predictions, zero_division=0,
                                   average='weighted' if not self.target_binary else 'binary'),
            'f1_score': f1_score(y_train, predictions, zero_division=0,
                                 average='weighted' if not self.target_binary else 'binary'),
            'balanced_accuracy': balanced_accuracy_score(y_train, predictions),
            'mcc': matthews_corrcoef(y_train, predictions),
            'kappa': cohen_kappa_score(y_train, predictions),
            'n_samples': len(y_train),
            'n_features': X_train.shape[1]
        }

        # Métriques supplémentaires pour classification binaire
        if self.target_binary and probabilities is not None:
            try:
                self.train_metrics.update({
                    'roc_auc': roc_auc_score(y_train, probabilities),
                    'average_precision': average_precision_score(y_train, probabilities),
                    'log_loss': log_loss(y_train, probabilities),
                    'brier_score': brier_score_loss(y_train, probabilities)
                })
            except:
                pass

    def _optimize_threshold(self, X_train, y_train):
        """Optimise le seuil de classification pour maximiser le F1-score"""
        try:
            y_proba = self.model.predict_proba(X_train)[:, 1]

            # Calcul des métriques pour différents seuils
            thresholds = np.arange(0.1, 0.9, 0.05)
            best_f1 = 0
            best_threshold = 0.5
            best_metrics = {}

            for threshold in thresholds:
                y_pred = (y_proba >= threshold).astype(int)
                f1 = f1_score(y_train, y_pred, zero_division=0)

                if f1 > best_f1:
                    best_f1 = f1
                    best_threshold = threshold
                    best_metrics = {
                        'f1': f1,
                        'precision': precision_score(y_train, y_pred, zero_division=0),
                        'recall': recall_score(y_train, y_pred, zero_division=0),
                        'mcc': matthews_corrcoef(y_train, y_pred)
                    }

            self.threshold_optimized = best_threshold
            st.info(f"🔧 Seuil optimal pour classification: {best_threshold:.2f}")
            st.info(f"   F1-score: {best_metrics['f1']:.3f}, Précision: {best_metrics['precision']:.3f}, "
                    f"Recall: {best_metrics['recall']:.3f}, MCC: {best_metrics['mcc']:.3f}")

        except Exception as e:
            st.warning(f"⚠️ Impossible d'optimiser le seuil: {e}")
            self.threshold_optimized = 0.5

    def predict(self, X, use_optimized_threshold=True):
        """
        Prédiction avec seuil optimisé
        """
        if self.model is None:
            raise ValueError("Le modèle n'a pas été entraîné. Veuillez d'abord entraîner le modèle.")

        if self.target_binary and hasattr(self.model, 'predict_proba') and use_optimized_threshold:
            probabilities = self.model.predict_proba(X)[:, 1]
            predictions = (probabilities >= self.threshold_optimized).astype(int)
            return predictions, probabilities
        else:
            predictions = self.model.predict(X)
            probabilities = self.model.predict_proba(X) if hasattr(self.model, 'predict_proba') else None
            return predictions, probabilities

    def evaluate(self, X_test, y_test):
        """
        Évalue les performances du modèle avec des métriques complètes
        """
        predictions, probabilities = self.predict(X_test)

        # Métriques de base
        metrics = {
            'accuracy': accuracy_score(y_test, predictions),
            'precision': precision_score(y_test, predictions, zero_division=0,
                                         average='weighted' if not self.target_binary else 'binary'),
            'recall': recall_score(y_test, predictions, zero_division=0,
                                   average='weighted' if not self.target_binary else 'binary'),
            'f1_score': f1_score(y_test, predictions, zero_division=0,
                                 average='weighted' if not self.target_binary else 'binary'),
            'balanced_accuracy': balanced_accuracy_score(y_test, predictions),
            'mcc': matthews_corrcoef(y_test, predictions),
            'kappa': cohen_kappa_score(y_test, predictions),
            'model_type': self.model_type,
            'n_features': X_test.shape[1],
            'test_samples': len(y_test),
            'target_binary': self.target_binary,
            'optimal_threshold': self.threshold_optimized if self.target_binary else None
        }

        # ROC-AUC seulement pour classification binaire avec probabilités
        if self.target_binary and probabilities is not None and y_test.nunique() == 2:
            try:
                metrics.update({
                    'roc_auc': roc_auc_score(y_test, probabilities),
                    'average_precision': average_precision_score(y_test, probabilities),
                    'log_loss': log_loss(y_test, probabilities),
                    'brier_score': brier_score_loss(y_test, probabilities)
                })
            except:
                metrics.update({
                    'roc_auc': None,
                    'average_precision': None,
                    'log_loss': None,
                    'brier_score': None
                })

        # Matrice de confusion
        metrics['confusion_matrix'] = confusion_matrix(y_test, predictions).tolist()

        # Rapport de classification
        metrics['classification_report'] = classification_report(
            y_test, predictions,
            output_dict=True,
            zero_division=0
        )

        # Calcul des métriques par classe pour classification binaire
        if self.target_binary and y_test.nunique() == 2:
            try:
                tn, fp, fn, tp = confusion_matrix(y_test, predictions).ravel()
                metrics.update({
                    'specificity': tn / (tn + fp) if (tn + fp) > 0 else 0,
                    'false_positive_rate': fp / (fp + tn) if (fp + tn) > 0 else 0,
                    'false_negative_rate': fn / (fn + tp) if (fn + tp) > 0 else 0,
                    'true_positive': int(tp),
                    'true_negative': int(tn),
                    'false_positive': int(fp),
                    'false_negative': int(fn),
                    'precision_positive': tp / (tp + fp) if (tp + fp) > 0 else 0,
                    'precision_negative': tn / (tn + fn) if (tn + fn) > 0 else 0,
                    'f1_positive': 2 * metrics['precision_positive'] * metrics['recall'] /
                                   (metrics['precision_positive'] + metrics['recall'])
                    if (metrics['precision_positive'] + metrics['recall']) > 0 else 0
                })
            except:
                pass

        # Scores de calibration (seulement pour les probabilités)
        if probabilities is not None and self.target_binary:
            try:
                # Binning pour évaluer la calibration
                n_bins = 10
                bin_edges = np.linspace(0, 1, n_bins + 1)
                bin_indices = np.digitize(probabilities, bin_edges) - 1

                calibration_data = []
                for i in range(n_bins):
                    mask = bin_indices == i
                    if mask.any():
                        mean_pred = probabilities[mask].mean()
                        mean_true = y_test[mask].mean()
                        calibration_data.append({
                            'bin': i,
                            'mean_prediction': mean_pred,
                            'mean_actual': mean_true,
                            'count': mask.sum()
                        })

                metrics['calibration_data'] = calibration_data

                # Score ECE (Expected Calibration Error)
                ece = 0
                total_samples = len(y_test)
                for calib in calibration_data:
                    ece += (calib['count'] / total_samples) * abs(calib['mean_prediction'] - calib['mean_actual'])
                metrics['ece'] = ece

            except:
                metrics['calibration_data'] = None
                metrics['ece'] = None

        self.test_metrics = metrics
        return metrics

    def get_comprehensive_metrics_table(self):
        """Retourne un tableau complet des métriques"""
        if not self.test_metrics:
            return None

        # Préparer les données pour le tableau
        metrics_data = []

        # Métriques principales
        main_metrics = [
            ('Accuracy', self.test_metrics.get('accuracy', 0), 'Taux de prédictions correctes'),
            ('Précision', self.test_metrics.get('precision', 0), 'Précision des prédictions positives'),
            ('Recall', self.test_metrics.get('recall', 0), 'Taux de détection des vrais positifs'),
            ('F1-Score', self.test_metrics.get('f1_score', 0), 'Moyenne harmonique de précision et recall'),
            ('MCC', self.test_metrics.get('mcc', 0), 'Corrélation de Matthews (bon pour les classes déséquilibrées)'),
            ('Kappa', self.test_metrics.get('kappa', 0), "Accord entre prédictions et réalité"),
            ('Balanced Accuracy', self.test_metrics.get('balanced_accuracy', 0), 'Accuracy pondérée')
        ]

        for name, value, description in main_metrics:
            metrics_data.append({
                'Métrique': name,
                'Valeur': f'{value:.4f}' if value is not None else 'N/A',
                'Description': description
            })

        # Métriques supplémentaires pour classification binaire
        if self.target_binary:
            binary_metrics = [
                ('AUC-ROC', self.test_metrics.get('roc_auc'), 'Aire sous la courbe ROC'),
                ('Average Precision', self.test_metrics.get('average_precision'),
                 'Précision moyenne sur tous les seuils'),
                ('Log Loss', self.test_metrics.get('log_loss'), 'Erreur logarithmique'),
                ('Brier Score', self.test_metrics.get('brier_score'), 'Erreur quadratique moyenne des probabilités'),
                ('Specificity', self.test_metrics.get('specificity'), 'Taux de vrais négatifs'),
                ('FPR', self.test_metrics.get('false_positive_rate'), 'Taux de faux positifs'),
                ('FNR', self.test_metrics.get('false_negative_rate'), 'Taux de faux négatifs'),
                ('ECE', self.test_metrics.get('ece'), "Erreur d'étalonnage attendue")
            ]

            for name, value, description in binary_metrics:
                if value is not None:
                    metrics_data.append({
                        'Métrique': name,
                        'Valeur': f'{value:.4f}',
                        'Description': description
                    })

        return pd.DataFrame(metrics_data)

    def get_feature_importance_plot(self):
        """Génère un graphique d'importance des features"""
        if self.feature_importance is None:
            return None

        top_features = self.feature_importance.head(15)  # Augmenté à 15 features

        fig = go.Figure(data=[
            go.Bar(
                x=top_features['importance'],
                y=top_features['feature'],
                orientation='h',
                marker_color='crimson',
                text=[f'{imp:.3f}' for imp in top_features['importance']],
                textposition='outside'
            )
        ])

        fig.update_layout(
            title=f'Top 15 des Features les plus importantes ({self.model_type})',
            xaxis_title='Importance',
            yaxis_title='Feature',
            height=500,
            template='plotly_white',
            showlegend=False
        )

        return fig

    def get_roc_curve_plot(self, X_test, y_test):
        """Génère la courbe ROC (seulement pour classification binaire)"""
        if not self.target_binary or not hasattr(self.model, 'predict_proba'):
            return None

        try:
            probabilities = self.model.predict_proba(X_test)[:, 1]
            if y_test.nunique() != 2:
                return None

            fpr, tpr, thresholds = roc_curve(y_test, probabilities)
            auc_score = roc_auc_score(y_test, probabilities)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=fpr, y=tpr,
                mode='lines',
                name=f'ROC curve (AUC = {auc_score:.3f})',
                line=dict(color='darkorange', width=3),
                fill='tozeroy',
                fillcolor='rgba(255, 140, 0, 0.2)'
            ))
            fig.add_trace(go.Scatter(
                x=[0, 1], y=[0, 1],
                mode='lines',
                name='Random (AUC = 0.5)',
                line=dict(color='navy', width=2, dash='dash')
            ))

            fig.update_layout(
                title=f'Courbe ROC - {self.model_type}',
                xaxis_title='Taux de Faux Positifs',
                yaxis_title='Taux de Vrais Positifs',
                yaxis=dict(scaleanchor="x", scaleratio=1),
                xaxis=dict(constrain='domain'),
                height=500,
                template='plotly_white',
                hovermode='x unified'
            )

            return fig
        except:
            return None

    def get_precision_recall_plot(self, X_test, y_test):
        """Génère la courbe Precision-Recall"""
        if not self.target_binary or not hasattr(self.model, 'predict_proba'):
            return None

        try:
            probabilities = self.model.predict_proba(X_test)[:, 1]
            if y_test.nunique() != 2:
                return None

            precision, recall, _ = precision_recall_curve(y_test, probabilities)
            avg_precision = average_precision_score(y_test, probabilities)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=recall, y=precision,
                mode='lines',
                name=f'Precision-Recall curve (AP = {avg_precision:.3f})',
                line=dict(color='green', width=3),
                fill='tozeroy',
                fillcolor='rgba(0, 255, 0, 0.2)'
            ))

            # Ajouter le seuil optimal
            fig.add_vline(x=self.threshold_optimized, line_dash="dash",
                          line_color="red", annotation_text=f"Seuil optimal: {self.threshold_optimized:.2f}")

            fig.update_layout(
                title=f'Courbe Precision-Recall - {self.model_type}',
                xaxis_title='Recall',
                yaxis_title='Precision',
                height=500,
                template='plotly_white'
            )

            return fig
        except:
            return None

    def get_calibration_plot(self, X_test, y_test):
        """Génère un graphique de calibration des probabilités"""
        if not self.target_binary or not hasattr(self.model, 'predict_proba'):
            return None

        try:
            probabilities = self.model.predict_proba(X_test)[:, 1]

            # Binning pour évaluer la calibration
            n_bins = 10
            bin_edges = np.linspace(0, 1, n_bins + 1)
            bin_indices = np.digitize(probabilities, bin_edges) - 1

            bin_centers = []
            bin_means = []
            bin_counts = []

            for i in range(n_bins):
                mask = bin_indices == i
                if mask.any():
                    bin_centers.append((bin_edges[i] + bin_edges[i + 1]) / 2)
                    bin_means.append(y_test[mask].mean())
                    bin_counts.append(mask.sum())

            fig = go.Figure()

            # Courbe de calibration
            fig.add_trace(go.Scatter(
                x=bin_centers,
                y=bin_means,
                mode='lines+markers',
                name='Calibration',
                line=dict(color='blue', width=3),
                marker=dict(size=10)
            ))

            # Ligne de calibration parfaite
            fig.add_trace(go.Scatter(
                x=[0, 1],
                y=[0, 1],
                mode='lines',
                name='Calibration parfaite',
                line=dict(color='red', width=2, dash='dash')
            ))

            # Ajouter la taille des bins comme taille des points
            fig.update_traces(
                marker=dict(
                    size=[count / 10 for count in bin_counts],  # Ajuster la taille selon le nombre d'échantillons
                    sizemode='area',
                    sizeref=2. * max(bin_counts) / (40. ** 2),
                    sizemin=4
                ),
                selector=dict(mode='lines+markers')
            )

            fig.update_layout(
                title=f'Courbe de Calibration - {self.model_type}',
                xaxis_title='Probabilité prédite',
                yaxis_title='Fraction de positifs',
                height=500,
                template='plotly_white'
            )

            return fig
        except:
            return None

    def get_metrics_comparison_chart(self):
        """Génère un graphique comparatif des métriques train/test"""
        if not self.train_metrics or not self.test_metrics:
            return None

        # Sélectionner les métriques à comparer
        metrics_to_compare = ['accuracy', 'precision', 'recall', 'f1_score']

        train_values = []
        test_values = []
        metric_names = []

        for metric in metrics_to_compare:
            if metric in self.train_metrics and metric in self.test_metrics:
                train_values.append(self.train_metrics[metric])
                test_values.append(self.test_metrics[metric])
                metric_names.append(metric.replace('_', ' ').title())

        if not train_values:
            return None

        fig = go.Figure(data=[
            go.Bar(name='Entraînement', x=metric_names, y=train_values, marker_color='blue'),
            go.Bar(name='Test', x=metric_names, y=test_values, marker_color='orange')
        ])

        fig.update_layout(
            title='Comparaison des métriques Train/Test',
            barmode='group',
            height=400,
            template='plotly_white'
        )

        return fig

    def predict_risk_clients(self, df, target_col=None, risk_threshold=0.7):
        """
        Identifie les clients à risque élevé (seulement pour classification binaire)
        """
        if self.model is None:
            raise ValueError("Le modèle n'a pas été entraîné.")

        if not self.target_binary:
            st.warning("⚠️ La prédiction de risque est optimisée pour la classification binaire.")
            return None

        # Préparer les données
        X = df.copy()
        if target_col and target_col in X.columns:
            X = X.drop(columns=[target_col])

        # Gérer l'ID client
        client_id = None
        id_columns = ['client_id', 'id', 'contract_id', 'ID', 'CLIENT_ID', 'CONTRACT_ID', 'N°Contrat', 'numero_contrat']
        for id_col in id_columns:
            if id_col in X.columns:
                client_id = X[id_col].copy()
                X = X.drop(columns=[id_col])
                break

        if client_id is None:
            client_id = pd.Series(range(len(X)), name='client_id')

        # Préparer les données selon le type de modèle
        if self.model_type == 'catboost':
            # CatBoost gère directement les catégories
            X_prepared = X.copy()
            # Encoder seulement les colonnes non-catégorielles
            for col in X_prepared.select_dtypes(include=['object', 'category']).columns:
                if col not in self.cat_features:
                    le = LabelEncoder()
                    X_prepared[col] = le.fit_transform(X_prepared[col].astype(str))
        else:
            X_prepared = self._encode_categorical_features(X)

        # Imputation et normalisation
        X_imputed = self.imputer.transform(X_prepared)
        X_prepared = pd.DataFrame(X_imputed, columns=X_prepared.columns)
        X_scaled = self.scaler.transform(X_prepared)
        X_prepared = pd.DataFrame(X_scaled, columns=X_prepared.columns)

        # Prédictions
        if hasattr(self.model, 'predict_proba'):
            probabilities = self.model.predict_proba(X_prepared)[:, 1]
            predictions = (probabilities >= self.threshold_optimized).astype(int)

            # Créer DataFrame de résultats
            results = pd.DataFrame({
                'client_id': client_id.values,
                'predicted_risk': predictions,
                'risk_probability': probabilities,
                'risk_level': pd.cut(probabilities,
                                     bins=[0, 0.3, 0.7, 1],
                                     labels=['Faible', 'Modéré', 'Élevé'],
                                     include_lowest=True)
            })

            # Clients à haut risque
            high_risk_clients = results[results['risk_probability'] >= risk_threshold].copy()
            high_risk_clients = high_risk_clients.sort_values('risk_probability', ascending=False)

            # Ajouter les features importantes pour l'analyse
            if self.feature_importance is not None:
                top_features = self.feature_importance.head(5)['feature'].tolist()
                for feature in top_features:
                    if feature in df.columns:
                        results[feature] = df[feature].values
                        if not high_risk_clients.empty and feature in df.columns:
                            high_risk_clients[feature] = df.loc[high_risk_clients.index, feature].values

            # Statistiques
            risk_distribution = results['risk_level'].value_counts().to_dict()

            return {
                'all_predictions': results,
                'high_risk_clients': high_risk_clients,
                'risk_distribution': risk_distribution,
                'average_risk': results['risk_probability'].mean(),
                'n_high_risk': len(high_risk_clients),
                'high_risk_percentage': (len(high_risk_clients) / len(results)) * 100
            }

        return None

    def save_model(self, path='models/risk_model.pkl'):
        """Sauvegarde le modèle entraîné"""
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)

        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'imputer': self.imputer,
            'label_encoders': self.label_encoders,
            'feature_importance': self.feature_importance,
            'threshold': self.threshold_optimized,
            'model_type': self.model_type,
            'target_binary': self.target_binary,
            'cat_features': self.cat_features,
            'train_metrics': self.train_metrics,
            'test_metrics': self.test_metrics
        }

        joblib.dump(model_data, path)
        st.success(f"✅ Modèle sauvegardé: {path}")

    def load_model(self, path='models/risk_model.pkl'):
        """Charge un modèle sauvegardé"""
        model_data = joblib.load(path)

        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.imputer = model_data['imputer']
        self.label_encoders = model_data['label_encoders']
        self.feature_importance = model_data['feature_importance']
        self.threshold_optimized = model_data['threshold']
        self.model_type = model_data['model_type']
        self.target_binary = model_data['target_binary']
        self.cat_features = model_data.get('cat_features', [])
        self.train_metrics = model_data.get('train_metrics')
        self.test_metrics = model_data.get('test_metrics')

        st.success(f"✅ Modèle chargé: {path}")

    def get_model_info(self):
        """Retourne des informations sur le modèle"""
        if self.model is None:
            return "Modèle non entraîné"

        info = {
            'type': self.model_type,
            'target_type': 'Binaire' if self.target_binary else 'Multi-classes',
            'optimal_threshold': self.threshold_optimized if self.target_binary else 'N/A',
            'features_count': self.feature_importance.shape[0] if self.feature_importance is not None else 'N/A',
            'cat_features_count': len(self.cat_features),
            'train_metrics_available': self.train_metrics is not None,
            'test_metrics_available': self.test_metrics is not None
        }

        return info
# ============================================================
# app.py — LIK Insurance Analyst
# Orchestrateur central de tous les moteurs
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
import json
import io
import tempfile
import zipfile
import traceback
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(BASE_DIR, "modules"))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Vérifier si report_engine est disponible
try:
    from report_engine import ReportEngine

    REPORT_ENGINE_AVAILABLE = True
except ImportError:
    REPORT_ENGINE_AVAILABLE = False
    ReportEngine = None

# ------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------
st.set_page_config(
    page_title="LIK Insurance Analyst",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ------------------------------------------------------------
# LOAD CSS
# ------------------------------------------------------------
def load_css():
    css_path = os.path.join(ASSETS_DIR, "style.css")
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        # Style CSS par défaut
        st.markdown("""
        <style>
        .main-header {
            color: #1E3A8A;
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }
        .stButton > button {
            width: 100%;
        }
        </style>
        """, unsafe_allow_html=True)


load_css()

# ------------------------------------------------------------
# SESSION STATE (CENTRAL)
# ------------------------------------------------------------
# Initialisation des états de session
session_defaults = {
    "df": None,
    "dataframe": None,
    "metadata": None,
    "data_ready": False,
    "data_loaded": False,
    "metadata_ready": False,
    "openai_client": None,
    "nlq_engine": None,
    "predictive_engine": None,
    "insight_engine": None,
    "scored_clients": None,
    "client_table": None,
    "raw_data": None,
    "conversation_history": [],
    "business_context": None,
    "column_documentation": None,
    "column_explainer": None,
    "uploaded_file_name": None,
    "df_final": None,
    "report_engine": None,
    "using_mateur": False,
    "generated_report_md": None,
    "generated_report_pdf": None,
    "generated_report_word": None,
    "generated_report_html": None
}

for key, value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ------------------------------------------------------------
# HEADER
# ------------------------------------------------------------
st.markdown('<h1 class="main-header">LIK Insurance Analyst</h1>', unsafe_allow_html=True)
st.caption("Orchestrateur IA – Données → Modèles → Décision")

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    # Logo
    logo_path = os.path.join(ASSETS_DIR, "logo0.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=180)
    else:
        st.markdown("### 🔒 LIK Insurance")

    # Configuration API
    st.markdown("### 🔐 Configuration API")

    api_key_input = st.text_input(
        "Clé OpenAI API",
        type="password",
        help="Obtenez votre clé sur platform.openai.com",
        placeholder="sk-...",
        key="api_key_input"
    )

    if api_key_input:
        try:
            from llm_client import OpenAIAnalyzer

            st.session_state.openai_client = OpenAIAnalyzer(api_key=api_key_input)
            st.success("✅ Clé API validée")
        except ImportError:
            st.warning("Clé API validée invalide")
        except Exception as e:
            st.error(f"Erreur : {e}")

    st.markdown("---")

    # Navigation
    st.markdown("### 🧭 Navigation")

    page = st.radio(
        "",
        [
            "📤 Chargement des données",
            "🔧 Traitement des données",
            "🔍 Métadonnées",
            "🤖 Assistant IA",
            "📈 Modèles Prédictifs",
            "🔍 Insights Avancés",
            "📝 Rapport"
        ]
    )

    st.markdown("---")

    # État de l'application
    st.markdown("### 📊 État")

    if st.session_state.data_loaded:
        df = st.session_state.dataframe
        st.success("✅ Données chargées")
        st.caption(f"• {len(df):,} lignes")
        st.caption(f"• {len(df.columns)} colonnes")
    else:
        st.warning("⚠️ Aucune donnée")

    if st.session_state.metadata is not None:
        st.success("✅ Métadonnées prêtes")

    if st.session_state.scored_clients is not None:
        st.success("✅ Analyse risque complète")

# ------------------------------------------------------------
# Initialisation des moteurs IA dépendants de OpenAI
# ------------------------------------------------------------
if st.session_state.openai_client is not None:
    if st.session_state.report_engine is None:
        try:
            st.session_state.report_engine = ReportEngine(
                ai_client=st.session_state.openai_client
            )
        except:
            pass

# ============================================================
# 1️⃣ CHARGEMENT DES DONNÉES
# ============================================================
if page == "📤 Chargement des données":
    st.header("📤 Chargement des données")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Téléversez votre fichier de données",
            type=["csv", "xlsx", "xls", "txt", "dta"],
            help="Formats supportés: CSV, Excel, Texte, Stata"
        )

        if uploaded_file is not None:
            try:
                # Sauvegarder le nom du fichier
                st.session_state.uploaded_file_name = uploaded_file.name

                # Détection du type de fichier
                file_name = uploaded_file.name.lower()

                if file_name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file, encoding='utf-8')
                elif file_name.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(uploaded_file)
                elif file_name.endswith('.txt'):
                    df = pd.read_csv(uploaded_file, sep='\t', encoding='utf-8')
                elif file_name.endswith('.dta'):
                    df = pd.read_stata(uploaded_file)
                else:
                    st.error("Format de fichier non supporté")
                    df = None

                if df is not None:
                    # Préparation des données
                    try:
                        from data_prep_engine import DataPrepEngine

                        prep = DataPrepEngine()
                        df = prep.clean_data(df)
                        df = prep.engineer_features(df)
                        st.session_state.df_final = df
                    except ImportError:
                        # Si le module n'est pas disponible, utiliser les données brutes
                        st.info("Module data_prep_engine non disponible - données brutes utilisées")
                        st.session_state.df_final = df

                    # Affichage des informations de base
                    st.success(f"✅ Fichier chargé: {uploaded_file.name}")

                    with st.expander("📋 Aperçu des données", expanded=True):
                        st.dataframe(df.head(10), use_container_width=True)

                    # Statistiques rapides
                    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                    with col_stat1:
                        st.metric("Lignes", f"{len(df):,}")
                    with col_stat2:
                        st.metric("Colonnes", len(df.columns))
                    with col_stat3:
                        st.metric("Valeurs manquantes", f"{df.isna().sum().sum():,}")
                    with col_stat4:
                        st.metric("Doublons", f"{df.duplicated().sum():,}")

                    # Sauvegarde dans la session
                    st.session_state.dataframe = df
                    st.session_state.df = df
                    st.session_state.data_loaded = True
                    st.session_state.data_ready = True

                    # Réinitialiser les analyses existantes
                    st.session_state.metadata = None
                    st.session_state.business_context = None
                    st.session_state.scored_clients = None
                    st.session_state.client_table = None

                    st.success("✅ Données prêtes pour l'analyse!")

            except Exception as e:
                st.error(f"❌ Erreur lors du chargement: {str(e)}")

    with col2:
        st.markdown("** ℹ️ Sécurité 100%")
        st.info("""
        **Sachez que :**
        cette application vous permet de capitaliser sur vos objectifs pour le profilage et la gestion des clients en risque.

        **Vos données restent:**
        - En local sur votre ordinateur
        - Ne sont jamais partagées
        - Entièrement sous votre contrôle
        """)

# ============================================================
# 🔧 TRAITEMENT DES DONNÉES
# ============================================================
elif page == "🔧 Traitement des données":
    st.header("🔧 Traitement Avancé des Données")

    if not st.session_state.data_loaded:
        st.warning("⚠️ Veuillez d'abord charger des données")
        st.stop()

    df = st.session_state.dataframe.copy()

    # Initialisation du moteur
    try:
        from data_processing_engine import DataProcessingEngine

        processor = DataProcessingEngine()
        st.success("✅ Moteur de traitement chargé")
    except ImportError:
        st.error("❌ Module data_processing_engine non disponible")
        st.info("Assurez-vous que le module est dans le dossier 'modules/'")
        st.stop()

    # Layout en onglets
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏗️ Nettoyage",
        "⚙️ Enrichissement",
        "🎯 Segmentation",
        "📊 Qualité",
        "🚀 Pipeline"
    ])

    with tab1:
        st.subheader("🏗️ Nettoyage Complet des Données")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("""
            **Fonctionnalités de nettoyage:**
            - ✅ Standardisation des noms de colonnes
            - ✅ Traitement intelligent des valeurs manquantes
            - ✅ Détection et correction des outliers
            - ✅ Correction des types de données
            - ✅ Validation des contraintes métier
            """)

            if st.button("🔧 Exécuter le nettoyage complet", type="primary"):
                with st.spinner("Nettoyage en cours..."):
                    try:
                        df_clean = processor.comprehensive_clean(df)
                        st.session_state.df_processed = df_clean
                        st.session_state.processor = processor

                        # Afficher les résultats
                        st.success(f"✅ Nettoyage terminé: {df.shape[0]} → {df_clean.shape[0]} lignes")

                        # Métriques
                        summary = processor.get_processing_summary()
                        col_met1, col_met2, col_met3 = st.columns(3)
                        with col_met1:
                            st.metric("Lignes retirées", summary['quality_metrics'].get('rows_removed', 0))
                        with col_met2:
                            st.metric("Score complétude",
                                      f"{summary['quality_metrics'].get('completeness_score', 0):.1f}%")
                        with col_met3:
                            st.metric("Score cohérence",
                                      f"{summary['quality_metrics'].get('consistency_score', 0):.1f}%")

                    except Exception as e:
                        st.error(f"❌ Erreur lors du nettoyage: {str(e)}")

        with col2:
            st.info("""
            **Approche experte:**

            Notre algorithme applique des traitements spécifiques à l'assurance:

            1. **Standardisation intelligente** des noms selon le domaine
            2. **Imputation contextuelle** des valeurs manquantes
            3. **Winsorization** des outliers (préservation des données)
            4. **Validation métier** des règles d'assurance
            """)

    with tab2:
        st.subheader("⚙️ Enrichissement des Données")

        if 'df_processed' not in st.session_state:
            st.info("ℹ️ Veuillez d'abord nettoyer les données")
        else:
            df_clean = st.session_state.df_processed

            st.markdown("""
            **Features d'assurance à créer:**
            - 📊 **Démographiques:** Catégories d'âge, expérience de conduite
            - 🚗 **Véhicule:** Catégories de risque par marque
            - ⚠️ **Risque:** Scores composites et normalisés
            - 📅 **Temporelles:** Saisons, trimestres, jours de semaine
            - 🎯 **Composites:** Ratios métier avancés
            """)

            col_feat1, col_feat2 = st.columns(2)

            with col_feat1:
                create_demographic = st.checkbox("Features démographiques", value=True)
                create_vehicle = st.checkbox("Features véhicule", value=True)
                create_risk = st.checkbox("Features risque", value=True)

            with col_feat2:
                create_temporal = st.checkbox("Features temporelles", value=True)
                create_composite = st.checkbox("Features composites", value=True)

            if st.button("⚡ Générer les features", type="primary"):
                with st.spinner("Enrichissement en cours..."):
                    try:
                        # Appliquer l'enrichissement
                        processor = st.session_state.processor
                        df_enriched = processor.engineer_insurance_features(df_clean)

                        # Sauvegarder
                        st.session_state.df_enriched = df_enriched
                        st.session_state.processor = processor

                        # Afficher les nouvelles features
                        new_features = processor.metadata.get('engineered_features', [])
                        st.success(f"✅ {len(new_features)} nouvelles features créées")

                        # Aperçu des nouvelles colonnes
                        with st.expander("📋 Voir les nouvelles features"):
                            for i, feat in enumerate(new_features[:10]):
                                st.markdown(f"- **{feat}**")
                                if i >= 9 and len(new_features) > 10:
                                    st.markdown(f"... et {len(new_features) - 10} autres")

                        # Statistiques
                        st.markdown("#### 📈 Statistiques des nouvelles features")

                        # Afficher quelques statistiques pour les nouvelles features numériques
                        numeric_new = [f for f in new_features if df_enriched[f].dtype in ['int64', 'float64']]
                        if numeric_new:
                            stats_df = df_enriched[numeric_new[:5]].describe().T
                            st.dataframe(stats_df.style.format("{:.2f}"), use_container_width=True)

                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'enrichissement: {str(e)}")

    with tab3:
        st.subheader("🎯 Segmentation Client")

        if 'df_enriched' not in st.session_state:
            st.info("ℹ️ Veuillez d'abord enrichir les données")
        else:
            df_enriched = st.session_state.df_enriched

            st.markdown("""
            **Méthodes de segmentation:**

            1. **RFM + Risque:** Recency, Frequency, Monetary adapté à l'assurance
            2. **Rentabilité:** Basé sur la valeur client
            3. **Comportemental:** Par habitudes de sinistres
            4. **Complet:** Combinaison de toutes les méthodes
            """)

            method = st.selectbox(
                "Méthode de segmentation:",
                ["RFM + Risque", "Rentabilité", "Comportemental", "Complet"],
                help="Choisissez la méthode la plus adaptée à votre analyse"
            )

            method_map = {
                "RFM + Risque": "rfm_risk",
                "Rentabilité": "profitability",
                "Comportemental": "behavioral",
                "Complet": "comprehensive"
            }

            if st.button("🎯 Segmenter les clients", type="primary"):
                with st.spinner("Segmentation en cours..."):
                    try:
                        processor = st.session_state.processor
                        df_segmented = processor.segment_clients(
                            df_enriched,
                            method=method_map[method]
                        )

                        st.session_state.df_segmented = df_segmented

                        # Analyse des segments
                        if 'segment_cluster' in df_segmented.columns:
                            segment_counts = df_segmented['segment_cluster'].value_counts()

                            st.success(f"✅ {len(segment_counts)} segments identifiés")

                            # Visualisation
                            col_seg1, col_seg2 = st.columns(2)

                            with col_seg1:
                                st.markdown("#### 📊 Distribution des segments")
                                st.dataframe(
                                    segment_counts.reset_index().rename(
                                        columns={'segment_cluster': 'Segment', 'count': 'Nombre'}
                                    ),
                                    use_container_width=True
                                )

                            with col_seg2:
                                # Graphique
                                import plotly.express as px

                                fig = px.pie(
                                    values=segment_counts.values,
                                    names=segment_counts.index,
                                    title="Répartition des segments"
                                )
                                st.plotly_chart(fig, use_container_width=True)

                    except Exception as e:
                        st.error(f"❌ Erreur lors de la segmentation: {str(e)}")

    with tab4:
        st.subheader("📊 Analyse de Qualité")

        # Sélection du dataset à analyser
        dataset_options = ["Données brutes", "Données nettoyées", "Données enrichies"]
        if 'df_segmented' in st.session_state:
            dataset_options.append("Données segmentées")

        selected_dataset = st.selectbox("Dataset à analyser:", dataset_options)

        # Mapping des datasets
        dataset_map = {
            "Données brutes": ("dataframe", "Données originales"),
            "Données nettoyées": ("df_processed", "Données après nettoyage"),
            "Données enrichies": ("df_enriched", "Données après enrichissement"),
            "Données segmentées": ("df_segmented", "Données après segmentation")
        }

        if selected_dataset in dataset_map:
            dataset_key, dataset_desc = dataset_map[selected_dataset]

            if dataset_key in st.session_state:
                df_to_analyze = st.session_state[dataset_key]

                if st.button("🔍 Analyser la qualité", type="primary"):
                    with st.spinner("Analyse en cours..."):
                        try:
                            # Analyse de qualité
                            processor = DataProcessingEngine()
                            quality_report = processor.analyze_data_quality(df_to_analyze)

                            # Affichage des résultats
                            st.success("✅ Analyse de qualité terminée")

                            # Score global
                            col_q1, col_q2, col_q3 = st.columns(3)
                            with col_q1:
                                st.metric(
                                    "Score global",
                                    f"{quality_report['overall_quality_score']}/100",
                                    delta=None
                                )
                            with col_q2:
                                grade = quality_report['quality_grade']
                                st.metric("Grade", grade.split(' ')[0])
                            with col_q3:
                                st.metric("Lignes", f"{quality_report['basic_stats']['rows']:,}")

                            # Détails par métrique
                            st.markdown("#### 📈 Métriques détaillées")

                            metrics_cols = st.columns(2)

                            with metrics_cols[0]:
                                # Complétude
                                completeness = quality_report['completeness']
                                st.markdown(f"**📊 Complétude:** {completeness['score']:.1f}/100")
                                st.progress(completeness['score'] / 100)

                                if completeness['columns_with_missing']:
                                    st.warning(
                                        f"Colonnes avec valeurs manquantes: {len(completeness['columns_with_missing'])}")

                            with metrics_cols[1]:
                                # Cohérence
                                consistency = quality_report['consistency']
                                st.markdown(f"**🔧 Cohérence:** {consistency['score']:.1f}/100")
                                st.progress(consistency['score'] / 100)

                                if consistency['issues_found'] > 0:
                                    st.warning(f"Problèmes de cohérence: {consistency['issues_found']}")

                            # Types de données
                            st.markdown("#### 🏷️ Types de données")

                            types_cols = st.columns(3)
                            basic_stats = quality_report['basic_stats']

                            with types_cols[0]:
                                st.metric("Numériques", len(basic_stats['numeric_columns']))
                                if basic_stats['numeric_columns']:
                                    st.caption(", ".join(basic_stats['numeric_columns'][:3]))

                            with types_cols[1]:
                                st.metric("Catégorielles", len(basic_stats['categorical_columns']))
                                if basic_stats['categorical_columns']:
                                    st.caption(", ".join(basic_stats['categorical_columns'][:3]))

                            with types_cols[2]:
                                st.metric("Dates", len(basic_stats['date_columns']))
                                if basic_stats['date_columns']:
                                    st.caption(", ".join(basic_stats['date_columns'][:3]))

                            # Export du rapport
                            st.markdown("---")
                            st.markdown("#### 📤 Export du rapport")

                            report_format = st.radio("Format:", ["HTML", "Texte"])

                            if st.button("📄 Générer le rapport complet"):
                                report = processor.export_quality_report(
                                    df_to_analyze,
                                    format='html' if report_format == 'HTML' else 'text'
                                )

                                if report_format == 'HTML':
                                    st.download_button(
                                        label="⬇️ Télécharger HTML",
                                        data=report,
                                        file_name="rapport_qualite.html",
                                        mime="text/html"
                                    )
                                else:
                                    st.download_button(
                                        label="⬇️ Télécharger Texte",
                                        data=report,
                                        file_name="rapport_qualite.txt",
                                        mime="text/plain"
                                    )

                        except Exception as e:
                            st.error(f"❌ Erreur lors de l'analyse: {str(e)}")
            else:
                st.info(f"ℹ️ {dataset_desc} non disponible")
        else:
            st.info("ℹ️ Sélectionnez un dataset à analyser")

    with tab5:
        st.subheader("🚀 Pipeline Automatisé")

        st.markdown("""
        **Exécutez le pipeline complet de traitement:**

        1. 🏗️ **Nettoyage** - Préparation des données
        2. ⚙️ **Enrichissement** - Création des features
        3. 🎯 **Segmentation** - Groupement des clients
        4. 📊 **Qualité** - Validation des résultats
        """)

        # Options du pipeline
        st.markdown("#### ⚙️ Configuration du pipeline")

        col_pipe1, col_pipe2 = st.columns(2)

        with col_pipe1:
            run_cleaning = st.checkbox("Exécuter le nettoyage", value=True)
            run_enrichment = st.checkbox("Exécuter l'enrichissement", value=True)

        with col_pipe2:
            run_segmentation = st.checkbox("Exécuter la segmentation", value=True)
            segmentation_method = st.selectbox(
                "Méthode de segmentation:",
                ["RFM + Risque", "Rentabilité"],
                disabled=not run_segmentation
            )

        run_quality_check = st.checkbox("Vérifier la qualité finale", value=True)

        # Bouton d'exécution
        if st.button("🚀 Exécuter le pipeline complet", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()

            df_current = df.copy()
            processor = DataProcessingEngine()

            try:
                # Étape 1: Nettoyage
                if run_cleaning:
                    status_text.text("🏗️ Nettoyage des données...")
                    df_current = processor.comprehensive_clean(df_current)
                    progress_bar.progress(25)

                # Étape 2: Enrichissement
                if run_enrichment:
                    status_text.text("⚙️ Enrichissement des données...")
                    df_current = processor.engineer_insurance_features(df_current)
                    progress_bar.progress(50)

                # Étape 3: Segmentation
                if run_segmentation:
                    status_text.text("🎯 Segmentation des clients...")
                    method_map = {"RFM + Risque": "rfm_risk", "Rentabilité": "profitability"}
                    df_current = processor.segment_clients(df_current, method=method_map[segmentation_method])
                    progress_bar.progress(75)

                # Étape 4: Qualité
                if run_quality_check:
                    status_text.text("📊 Analyse de qualité...")
                    quality_report = processor.analyze_data_quality(df_current)
                    progress_bar.progress(100)

                # Sauvegarde des résultats
                st.session_state.df_processed_pipeline = df_current
                st.session_state.processor_pipeline = processor

                # Affichage des résultats
                st.success("✅ Pipeline exécuté avec succès!")

                # Résumé
                col_res1, col_res2, col_res3 = st.columns(3)

                with col_res1:
                    st.metric("Lignes finales", f"{df_current.shape[0]:,}")

                with col_res2:
                    new_features = len(set(df_current.columns) - set(df.columns))
                    st.metric("Nouvelles features", new_features)

                with col_res3:
                    if run_quality_check:
                        score = quality_report['overall_quality_score']
                        st.metric("Score qualité", f"{score}/100")

                # Export des données traitées
                st.markdown("---")
                st.markdown("#### 📤 Export des données traitées")

                csv = df_current.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="⬇️ Télécharger CSV",
                    data=csv,
                    file_name="donnees_traitees.csv",
                    mime="text/csv"
                )

                # Résumé du pipeline
                with st.expander("📋 Voir le résumé du pipeline"):
                    summary = processor.get_processing_summary()

                    st.markdown(f"**Nombre d'étapes:** {summary['total_steps']}")
                    st.markdown(f"**Dernière exécution:** {summary['last_processed'].strftime('%d/%m/%Y %H:%M')}")

                    if summary['engineered_features']:
                        st.markdown("**Features créées:**")
                        for feat in summary['engineered_features'][:10]:
                            st.markdown(f"- {feat}")

            except Exception as e:
                st.error(f"❌ Erreur lors de l'exécution du pipeline: {str(e)}")
                progress_bar.empty()
                status_text.empty()
# ============================================================
# 2️⃣ MÉTADONNÉES
# ============================================================
elif page == "🔍 Métadonnées":
    st.header("🔍 Extraction des Métadonnées")

    if not st.session_state.data_loaded:
        st.warning("⚠️ Veuillez d'abord charger des données")
        st.stop()

    df = st.session_state.dataframe

    try:
        from metadata_extractor import MetadataExtractor
        from business_context import BusinessContextProvider

        with st.spinner("Extraction des métadonnées sécurisées..."):
            # Extraction des métadonnées
            metadata_extractor = MetadataExtractor(df)
            metadata = metadata_extractor.extract_safe_metadata()
            schema_json = metadata_extractor.generate_schema_json()

            # Détermination du contexte métier
            business_context = BusinessContextProvider.get_context(
                BusinessContextProvider.infer_domain_from_columns(df.columns)
            )

            # Sauvegarde dans la session
            st.session_state.metadata = metadata
            st.session_state.business_context = business_context

        st.success("✅ Métadonnées extraites avec succès!")

        # Affichage des métadonnées
        tab1, tab2, tab3 = st.tabs(["📋 Vue d'ensemble", "📊 Structure", "🎯 Contexte Métier"])

        with tab1:
            st.subheader("Informations Générales")
            general_info = metadata.get('general_info', {})

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Lignes", general_info.get('nombre_lignes', 0))
            with col2:
                st.metric("Colonnes", general_info.get('nombre_colonnes', 0))
            with col3:
                st.metric("Mémoire (Mo)", f"{general_info.get('taille_memoire_mo', 0):.1f}")
            with col4:
                st.metric("Qualité", f"{metadata.get('quality_indicators', {}).get('completude_pct', 0):.1f}%")

            # Types de données
            st.subheader("Types de Données")
            dtype_summary = metadata.get('data_types_summary', {})
            if dtype_summary:
                dtype_df = pd.DataFrame({
                    "Type": list(dtype_summary.keys()),
                    "Nombre": list(dtype_summary.values())
                })
                st.dataframe(dtype_df, use_container_width=True)

        with tab2:
            st.subheader("Structure des Colonnes")
            columns_info = metadata.get('structure_columns', [])

            # Afficher les 10 premières colonnes
            columns_df = pd.DataFrame(columns_info[:10])
            st.dataframe(columns_df, use_container_width=True)

            # Statistiques des profils
            st.subheader("Profils Statistiques")
            profiles = metadata.get('statistical_profiles', {})

            if profiles.get('variables_numeriques'):
                st.markdown("**Variables Numériques:**")
                for var in profiles['variables_numeriques'][:3]:
                    st.markdown(f"- {var['nom']}: [{var['plage']['min']:.2f}, {var['plage']['max']:.2f}]")

            if profiles.get('variables_categorielles'):
                st.markdown("**Variables Catégorielles:**")
                for var in profiles['variables_categorielles'][:3]:
                    st.markdown(f"- {var['nom']}: {var['categories_count']} catégories")

        with tab3:
            st.subheader("Contexte Métier Inféré")
            context = business_context

            st.markdown(f"**Domaine:** {context.get('domaine', 'Non déterminé')}")
            st.markdown(f"**Description:** {context.get('description', '')}")

            st.markdown("**Concepts Clés:**")
            concepts = context.get('concepts_cles', [])
            for concept in concepts[:5]:
                st.markdown(f"- {concept}")

            st.markdown("**Analyses Courantes:**")
            analyses = context.get('analyses_courantes', [])
            for analyse in analyses[:3]:
                st.markdown(f"- {analyse}")

        # Export des métadonnées
        st.markdown("---")
        st.subheader("📤 Export des Métadonnées")

        col_exp1, col_exp2 = st.columns(2)

        with col_exp1:
            # Export JSON
            json_str = json.dumps(schema_json, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 Télécharger JSON",
                data=json_str,
                file_name="metadata.json",
                mime="application/json"
            )

        with col_exp2:
            # Export du contexte
            context_str = json.dumps(context, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 Contexte Métier",
                data=context_str,
                file_name="business_context.json",
                mime="application/json"
            )

    except ImportError as e:
        st.error(f"❌ Erreur d'importation: {e}")
        st.info("Vérifiez que les modules sécurisés sont installés dans le dossier 'modules/'")

# ============================================================
# 5️⃣ ASSISTANT IA
# ============================================================
elif page == "🤖 Assistant IA":
    st.header("🤖 Assistant IA")

    if not st.session_state.data_loaded:
        st.warning("⚠️ Veuillez d'abord charger des données")
        st.stop()

    if st.session_state.openai_client is None:
        st.warning("⚠️ Veuillez configurer votre clé API OpenAI dans la barre latérale")
        st.stop()

    df = st.session_state.dataframe
    client = st.session_state.openai_client

    # Interface de requête
    user_query = st.text_area(
        "💬 Posez votre question d'analyse:",
        height=100,
        placeholder="Ex: Quels sont les clients les plus à risque? Quelles sont les corrélations entre les variables? Génère un graphique montrant la distribution..."
    )

    if st.button("🔍 Analyser avec l'IA", type="primary") and user_query:
        with st.spinner("🤖 L'IA analyse votre question..."):
            try:
                # Analyse avec l'IA
                result = client.analyze_query(user_query, df)

                # Afficher les résultats
                st.success("✅ Analyse terminée!")

                # Onglets pour différents aspects
                tabs = st.tabs(["📋 Résumé", "🔍 Détails", "📊 Graphiques"])

                with tabs[0]:
                    st.markdown("### 🎯 Compréhension")
                    st.info(result.get("comprehension", "Analyse effectuée"))

                    st.markdown("### 📝 Réponse détaillée")
                    st.markdown(result.get("reponse_detaillee", "Pas de réponse détaillée"))

                with tabs[1]:
                    st.markdown("### 🧠 Méthodologie")
                    st.markdown(result.get("methodologie", "Non spécifiée"))

                    st.markdown("### 💡 Insights")
                    insights = result.get("insights", [])
                    if isinstance(insights, list):
                        for insight in insights:
                            st.markdown(f"- {insight}")
                    else:
                        st.markdown(str(insights))

                    st.markdown("### 🎯 Recommandations")
                    recommendations = result.get("recommandations", [])
                    if isinstance(recommendations, list):
                        for rec in recommendations:
                            st.markdown(f"- {rec}")
                    else:
                        st.markdown(str(recommendations))

                with tabs[2]:
                    st.markdown("### 🎨 Visualisations suggérées")
                    visualizations = result.get("visualisations", [])

                    if isinstance(visualizations, list) and visualizations:
                        try:
                            from visualization_generator import VisualizationGenerator

                            viz_gen = VisualizationGenerator(df)

                            for i, viz_type in enumerate(visualizations[:3]):
                                try:
                                    if viz_type.lower() in ["histogram", "histogramme"]:
                                        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                                        if numeric_cols:
                                            fig = viz_gen.create_histogram(numeric_cols[0])
                                            st.plotly_chart(fig, use_container_width=True)

                                    elif viz_type.lower() in ["scatter", "nuage de points"]:
                                        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                                        if len(numeric_cols) >= 2:
                                            fig = viz_gen.create_scatter(numeric_cols[0], numeric_cols[1])
                                            st.plotly_chart(fig, use_container_width=True)

                                    elif viz_type.lower() in ["heatmap", "carte de chaleur"]:
                                        try:
                                            fig = viz_gen.create_correlation_heatmap()
                                            st.plotly_chart(fig, use_container_width=True)
                                        except:
                                            st.info("Pas assez de colonnes numériques pour une heatmap")

                                    else:
                                        st.info(f"Type de visualisation '{viz_type}' non implémenté")
                                except Exception as e:
                                    st.error(f"Erreur avec la visualisation {viz_type}: {e}")
                        except ImportError:
                            st.info("Module de visualisation non disponible")
                    else:
                        st.info("Aucune visualisation spécifique suggérée")

                        # Proposer des visualisations automatiques
                        try:
                            from visualization_generator import VisualizationGenerator

                            viz_gen = VisualizationGenerator(df)
                            suggestions = viz_gen.auto_suggest_visualizations()

                            if suggestions:
                                st.markdown("### 📊 Visualisations automatiques suggérées")
                                for suggestion in suggestions[:2]:
                                    try:
                                        func = getattr(viz_gen, suggestion["function"])
                                        fig = func(**suggestion["params"])
                                        st.plotly_chart(fig, use_container_width=True)
                                    except Exception as e:
                                        st.error(f"Erreur: {e}")
                        except ImportError:
                            st.info("Module de visualisation non disponible")

            except Exception as e:
                st.error(f"❌ Erreur lors de l'analyse: {str(e)}")

# ============================================================
# 6️⃣ MODÈLES PRÉDICTIFS
# ============================================================
elif page == "📈 Modèles Prédictifs":
    st.header("🧠 Modèles Prédictifs")

    if not st.session_state.data_loaded:
        st.warning("⚠️ Chargez d'abord les données")
        st.stop()

    try:
        from predictive_engine import PredictiveEngine

        df = st.session_state.dataframe

        if st.session_state.predictive_engine is None:
            st.session_state.predictive_engine = PredictiveEngine()

        predictive_engine = st.session_state.predictive_engine

        st.subheader("⚙️ Configuration du modèle")

        # Détection automatique de la variable cible
        possible_targets = []
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ["risque", "churn", "attrition", "target",
                                                        "resilie", "renouvelle", "statut", "classe"]):
                possible_targets.append(col)

        if not possible_targets:
            possible_targets = list(df.select_dtypes(include=[np.number]).columns.tolist())

        col_config1, col_config2, col_config3 = st.columns(3)

        with col_config1:
            target_col = st.selectbox(
                "Variable cible",
                possible_targets,
                help="Colonne à prédire"
            )

        with col_config2:
            model_options = ["random_forest"]

            try:
                from catboost import CatBoostClassifier

                model_options.append("catboost")
            except:
                pass

            try:
                from xgboost import XGBClassifier

                model_options.append("xgboost")
            except:
                pass

            model_type = st.selectbox(
                "Algorithme",
                model_options,
                help="Random Forest: robuste, CatBoost: données catégorielles, XGBoost: performance"
            )

        with col_config3:
            test_size = st.slider(
                "Taille du jeu de test (%)",
                min_value=10,
                max_value=40,
                value=20,
                step=5
            ) / 100

        # Options avancées
        with st.expander("⚙️ Paramètres avancées"):
            col_adv1, col_adv2 = st.columns(2)

            with col_adv1:
                optimize = st.checkbox("Optimiser les hyperparamètres", value=True)
                handle_imbalance = st.checkbox("Gérer le déséquilibre", value=True)

            with col_adv2:
                cross_val = st.slider(
                    "Folds de validation croisée",
                    min_value=2,
                    max_value=5,
                    value=3
                )
                random_state = st.number_input("Random State", value=42, min_value=0, max_value=100)

        if st.button("🚀 Entraîner le modèle", type="primary"):
            with st.spinner("Préparation des données..."):
                X_train, X_test, y_train, y_test = predictive_engine.prepare_training_data(
                    df, target_col, test_size=test_size, random_state=random_state
                )

            with st.spinner(f"Entraînement du modèle {model_type}..."):
                predictive_engine.train_model(X_train, y_train, model_type, optimize)
                predictions, probabilities = predictive_engine.predict(X_test)
                metrics = predictive_engine.evaluate(X_test, y_test)

            st.success("✅ Modèle entraîné avec succès!")

            # Affichage des métriques
            st.subheader("📊 Métriques principales")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Accuracy", f"{metrics.get('accuracy', 0):.3f}")
            with col2:
                st.metric("Précision", f"{metrics.get('precision', 0):.3f}")
            with col3:
                st.metric("Recall", f"{metrics.get('recall', 0):.3f}")
            with col4:
                st.metric("F1-Score", f"{metrics.get('f1_score', 0):.3f}")

            # Matrice de confusion
            st.subheader("🎯 Matrice de confusion")
            if 'confusion_matrix' in metrics:
                cm = metrics['confusion_matrix']
                fig_cm = go.Figure(data=go.Heatmap(
                    z=cm,
                    x=['Prédit 0', 'Prédit 1'],
                    y=['Réel 0', 'Réel 1'],
                    colorscale='Blues',
                    text=cm,
                    texttemplate='%{text}'
                ))
                fig_cm.update_layout(
                    title='Matrice de Confusion',
                    height=400
                )
                st.plotly_chart(fig_cm, use_container_width=True)

            # Importance des features
            st.subheader("📈 Importance des features")
            try:
                importance_fig = predictive_engine.get_feature_importance_plot()
                if importance_fig:
                    st.plotly_chart(importance_fig, use_container_width=True)
            except:
                st.info("Importance des features non disponible pour ce modèle")

    except ImportError as e:
        st.error(f"❌ Module predictive_engine non disponible: {e}")


# ============================================================
# 8️⃣ INSIGHTS AVANCÉS (VOTRE CODE)
# ============================================================
elif page == "🔍 Insights Avancés":
    st.header("🔍 Analyse du Risque Client - Insights Avancés")

    if not st.session_state.data_loaded:
        st.warning("⚠️ Veuillez charger les données.")
        st.stop()

    # Utiliser df_final si disponible, sinon dataframe
    if st.session_state.df_final is not None:
        df_final = st.session_state.df_final
    else:
        df_final = st.session_state.dataframe

    if df_final is None:
        st.warning("Veuillez charger les données.")
        st.stop()

    # Vérifier si l'analyse de risque a déjà été faite
    if st.session_state.scored_clients is None:
        st.info("ℹ️ L'analyse de risque n'a pas encore été effectuée.")

        # Vérifier les colonnes nécessaires pour l'analyse
        required_cols = ['ncli', 'Prime', 'nb_jour_couv']
        missing_cols = [col for col in required_cols if col not in df_final.columns]

        if missing_cols:
            st.warning(f"⚠️ Colonnes manquantes pour l'analyse risque: {', '.join(missing_cols)}")
            st.info("""
            **Colonnes nécessaires:**
            - `ncli` : Identifiant client
            - `Prime` : Montant de la prime
            - `nb_jour_couv` : Durée de couverture en jours

            **Pour continuer:**
            1. Chargez un fichier avec ces colonnes
            2. Ou allez dans 'Analyse Risque' pour générer l'analyse
            """)
            st.stop()

        if st.button("🚀 Effectuer l'analyse de risque maintenant", type="primary"):
            try:
                from insight_engine import InsightEngine

                insight_engine = InsightEngine()

                with st.spinner("Analyse de risque en cours..."):
                    client_table = insight_engine.build_client_risk_table(df_final)
                    ppj_median = client_table["prime_par_jour_moy"].median()
                    scored_clients = insight_engine.compute_risk_score(client_table)
                    scored_clients["insight"] = scored_clients.apply(
                        lambda row: insight_engine.generate_client_insight(row, ppj_median),
                        axis=1
                    )

                    st.session_state.scored_clients = scored_clients
                    st.session_state.client_table = client_table
                    st.session_state.raw_data = df_final
                    st.session_state.insight_engine = insight_engine

                    st.success("✅ Analyse de risque terminée! Actualisez la page.")
                    st.rerun()

            except ImportError as e:
                st.error(f"❌ Module insight_engine non disponible: {e}")
                st.stop()

    # Récupérer les données analysées
    scored_clients = st.session_state.scored_clients
    insight_engine = st.session_state.insight_engine

    if scored_clients is None or insight_engine is None:
        st.stop()

    # Interface d'analyse
    analysis_type = st.radio(
        "Type d'analyse :",
        [
            "📋 Vue d'ensemble",
            "📊 Analyse Univariée",
            "📈 Analyse Bivariée",
            "📄 Rapport Narratif"
        ],
        horizontal=True
    )

    if analysis_type == "📋 Vue d'ensemble":
        st.subheader("Vue d'ensemble du portefeuille")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Clients", len(scored_clients))
        with col2:
            st.metric("Prime totale", f"{scored_clients['prime_totale'].sum():,.0f} MAD")
        with col3:
            st.metric("Score risque moyen", f"{scored_clients['score_risque'].mean():.1f}/100")
        with col4:
            high_risk = (scored_clients['niveau_risque'] == 'Élevé').sum()
            st.metric("Risque élevé", f"{high_risk} clients")

        st.subheader("Insights clés")
        insights = insight_engine.generate_insights(scored_clients)
        for ins in insights:
            st.markdown(f"• {ins}")

        st.subheader("📊 Distribution des risques")
        risk_dist = scored_clients["niveau_risque"].value_counts()
        fig_pie = go.Figure(data=[go.Pie(
            labels=risk_dist.index,
            values=risk_dist.values,
            hole=.3,
            marker_colors=['#2ECC71', '#F39C12', '#E74C3C']
        )])
        fig_pie.update_layout(title="Répartition par niveau de risque")
        st.plotly_chart(fig_pie, use_container_width=True)

    elif analysis_type == "📊 Analyse Univariée":
        st.subheader("Analyse Univariée")

        numeric_cols = scored_clients.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = scored_clients.select_dtypes(include=['object', 'category']).columns.tolist()

        col1, col2 = st.columns(2)
        with col1:
            selected_var = st.selectbox(
                "Sélectionnez une variable numérique :",
                options=numeric_cols,
                index=numeric_cols.index('score_risque') if 'score_risque' in numeric_cols else 0
            )

        with col2:
            chart_type = st.selectbox(
                "Type de visualisation :",
                ["Histogramme", "Boîte à moustaches", "Statistiques descriptives"]
            )

        st.subheader(f"Analyse de : {selected_var}")

        col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
        with col_stats1:
            st.metric("Moyenne", f"{scored_clients[selected_var].mean():.2f}")
        with col_stats2:
            st.metric("Médiane", f"{scored_clients[selected_var].median():.2f}")
        with col_stats3:
            st.metric("Écart-type", f"{scored_clients[selected_var].std():.2f}")
        with col_stats4:
            st.metric("Valeurs manquantes", f"{scored_clients[selected_var].isna().sum()}")

        if chart_type == "Histogramme":
            fig = insight_engine.create_univariate_histogram(scored_clients, selected_var)
            st.plotly_chart(fig, use_container_width=True)

        elif chart_type == "Boîte à moustaches":
            fig = insight_engine.create_univariate_boxplot(scored_clients, selected_var)
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.dataframe(scored_clients[selected_var].describe().round(2))

        st.subheader("Analyse des variables catégorielles")
        cat_var = st.selectbox(
            "Sélectionnez une variable catégorielle :",
            options=categorical_cols,
            index=categorical_cols.index('niveau_risque') if 'niveau_risque' in categorical_cols else 0
        )

        if cat_var in scored_clients.columns:
            cat_dist = scored_clients[cat_var].value_counts()
            fig_bar = go.Figure(data=[go.Bar(
                x=cat_dist.index,
                y=cat_dist.values,
                marker_color='#3498DB'
            )])
            fig_bar.update_layout(
                title=f"Distribution de {cat_var}",
                xaxis_title=cat_var,
                yaxis_title="Nombre"
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    elif analysis_type == "📈 Analyse Bivariée":
        st.subheader("Analyse Bivariée")

        numeric_cols = scored_clients.select_dtypes(include=[np.number]).columns.tolist()

        col1, col2, col3 = st.columns(3)
        with col1:
            x_var = st.selectbox(
                "Variable X :",
                options=numeric_cols,
                index=numeric_cols.index('prime_par_jour_moy') if 'prime_par_jour_moy' in numeric_cols else 0
            )

        with col2:
            y_var = st.selectbox(
                "Variable Y :",
                options=numeric_cols,
                index=numeric_cols.index('score_risque') if 'score_risque' in numeric_cols else 1
            )

        with col3:
            color_var = st.selectbox(
                "Variable de couleur (optionnel) :",
                options=['Aucune'] + scored_clients.columns.tolist(),
                index=0
            )

        viz_type = st.selectbox(
            "Type de visualisation bivariée :",
            ["Nuage de points", "Graphique en barres groupées"]
        )

        if viz_type == "Nuage de points":
            fig = insight_engine.create_bivariate_scatter(
                scored_clients, x_var, y_var, color_var if color_var != 'Aucune' else None
            )
            st.plotly_chart(fig, use_container_width=True)

            try:
                correlation = scored_clients[[x_var, y_var]].corr().iloc[0, 1]
                st.info(f"📊 Coefficient de corrélation : {correlation:.3f}")
            except:
                pass

        else:
            cat_cols = scored_clients.select_dtypes(include=['object', 'category']).columns.tolist()
            if cat_cols:
                cat_var = st.selectbox("Variable catégorielle :", cat_cols, key="cat_var_bivariate")
                grouped = scored_clients.groupby(cat_var)[y_var].mean().reset_index()
                fig = go.Figure(data=[go.Bar(
                    x=grouped[cat_var],
                    y=grouped[y_var],
                    marker_color='#3498DB'
                )])
                fig.update_layout(
                    title=f"{y_var} par {cat_var}",
                    xaxis_title=cat_var,
                    yaxis_title=f"Moyenne {y_var}"
                )
                st.plotly_chart(fig, use_container_width=True)

    else:  # Rapport Narratif
        st.subheader("📄 Rapport narratif pour décideur")
        report = insight_engine.generate_narrative_report(scored_clients)
        st.markdown(report)

        st.subheader("📤 Export du rapport")
        col1, col2 = st.columns(2)

        with col1:
            # Export PDF (simulé)
            if st.button("🖨️ Générer PDF"):
                st.success("Rapport PDF généré (simulation)")
                st.info("Fonctionnalité PDF à implémenter avec reportlab ou weasyprint")

        with col2:
            # Export texte
            txt_report = insight_engine.generate_narrative_report(scored_clients)
            st.download_button(
                label="📥 Télécharger rapport (TXT)",
                data=txt_report,
                file_name="rapport_risque_clients.txt",
                mime="text/plain"
            )
# ============================================================
# RAPPORT
# ============================================================
elif page == "📝 Rapport":
    st.header("📝 Génération de rapport IA")

    # Vérifier si report_engine est disponible
    if not REPORT_ENGINE_AVAILABLE:
        st.error("❌ Le module report_engine n'est pas disponible. Installez les dépendances nécessaires.")
        st.info("""
        **Dépendances nécessaires :**
        ```bash
        pip install reportlab python-docx markdown
        ```
        """)
        st.stop()

    if st.session_state.report_engine is None:
        # Initialiser un report_engine de base
        try:
            st.session_state.report_engine = ReportEngine(ai_client=None)
        except Exception as e:
            st.error(f"❌ Impossible d'initialiser le moteur de rapport: {e}")
            st.stop()

    # Indicateur du moteur utilisé
    if hasattr(st.session_state, 'using_mateur') and st.session_state.using_mateur:
        st.info("🔒 **Moteur : Mateur AI** - Analyse 100% locale, aucune donnée externe")
    elif st.session_state.openai_client is not None:
        st.info("☁️ **Moteur : OpenAI** - Utilise l'API cloud OpenAI")
    else:
        st.info("⚡ **Moteur : Local** - Génération basique")

    if not st.session_state.data_ready:
        st.warning("⚠️ Veuillez charger les données")
        st.stop()

    title = st.text_input(
        "Titre du rapport",
        "Rapport d'analyse – Assurance Automobile"
    )

    audience = st.selectbox(
        "Public cible",
        ["Direction générale", "Direction métier", "Équipe data", "Audit", "Comité de pilotage"]
    )

    sections = st.multiselect(
        "Sections à inclure",
        [
            "executive_summary",
            "data_context",
            "data_quality",
            "statistics",
            "models",
            "scoring",
            "insights",
            "recommendations",
            "limitations",
            "annexes"
        ],
        default=["executive_summary", "scoring", "recommendations"]
    )

    custom_instructions = st.text_area(
        "Instructions personnalisées",
        placeholder="Ex : Insister sur la rentabilité, mentionner les risques réglementaires, proposer un plan d'action concret...",
        height=100
    )

    # Options d'export
    st.subheader("📤 Options d'export")
    col_export1, col_export2, col_export3, col_export4 = st.columns(4)
    with col_export1:
        export_md = st.checkbox("Markdown (.md)", value=True)
    with col_export2:
        export_pdf = st.checkbox("PDF (.pdf)", value=True)
    with col_export3:
        export_word = st.checkbox("Word (.docx)", value=True)
    with col_export4:
        export_html = st.checkbox("HTML (.html)", value=True)

    if st.button("🤖 Générer le rapport complet", type="primary"):
        with st.spinner("Génération du rapport en cours..."):
            try:
                # Préparation des données
                data_summary = {
                    "rows": st.session_state.dataframe.shape[0],
                    "columns": st.session_state.dataframe.shape[1],
                    "key_variables": list(st.session_state.dataframe.columns[:10]),
                    "completeness": round((1 - st.session_state.dataframe.isna().sum().sum() /
                                           (st.session_state.dataframe.shape[0] * st.session_state.dataframe.shape[
                                               1])) * 100, 1)
                }

                analysis_summary = "Analyse descriptive + scoring client"

                # Ajout des informations spécifiques si disponibles
                if st.session_state.scored_clients is not None:
                    scored_clients = st.session_state.scored_clients
                    analysis_summary += f"\n- Clients analysés : {len(scored_clients):,}"
                    analysis_summary += f"\n- Score risque moyen : {scored_clients['score_risque'].mean():.1f}/100"
                    high_risk = (scored_clients['niveau_risque'] == 'Élevé').sum()
                    analysis_summary += f"\n- Clients à risque élevé : {high_risk}"
                    data_summary["high_risk_count"] = high_risk

                # Ajout des insights si disponibles
                insights = None
                if st.session_state.scored_clients is not None:
                    try:
                        from insight_engine import InsightEngine

                        insight_engine = InsightEngine()
                        insights = insight_engine.generate_insights(st.session_state.scored_clients)
                    except ImportError as e:
                        insights = ["Insights sur les risques clients disponibles dans l'onglet 'Insights Avancés'"]
                    except Exception as e:
                        insights = [f"Insights : {str(e)}"]

                # Génération du rapport markdown
                report_md = st.session_state.report_engine.generate_report(
                    title=title,
                    audience=audience,
                    sections=sections,
                    data_summary=data_summary,
                    analysis_summary=analysis_summary,
                    model_results=None,
                    insights=insights,
                    custom_instructions=custom_instructions,
                    detail_level=4
                )

                st.session_state.generated_report_md = report_md
                st.success("✅ Rapport markdown généré avec succès!")

                # Génération des exports
                if export_pdf:
                    with st.spinner("Génération du PDF..."):
                        try:
                            pdf_buffer = st.session_state.report_engine.to_pdf(report_md, title)
                            st.session_state.generated_report_pdf = pdf_buffer.getvalue()
                            st.success("✅ PDF généré avec succès!")
                        except Exception as e:
                            st.warning(f"⚠️ PDF non généré: {str(e)}")
                            st.session_state.generated_report_pdf = None

                if export_word:
                    with st.spinner("Génération du document Word..."):
                        try:
                            word_buffer = st.session_state.report_engine.to_word(report_md, title)
                            st.session_state.generated_report_word = word_buffer.getvalue()
                            st.success("✅ Document Word généré avec succès!")
                        except Exception as e:
                            st.warning(f"⚠️ Word non généré: {str(e)}")
                            st.session_state.generated_report_word = None

                # Génération HTML
                if export_html:
                    try:
                        html_report = st.session_state.report_engine.to_html(report_md)
                        st.session_state.generated_report_html = html_report
                        st.success("✅ HTML généré avec succès!")
                    except Exception as e:
                        st.warning(f"⚠️ HTML non généré: {str(e)}")
                        st.session_state.generated_report_html = None

            except Exception as e:
                st.error(f"❌ Erreur lors de la génération du rapport: {str(e)}")
                import traceback

                st.code(traceback.format_exc())

    # Affichage et téléchargements
    if hasattr(st.session_state, 'generated_report_md') and st.session_state.generated_report_md:
        st.markdown("---")
        st.subheader("📄 Aperçu du rapport")

        with st.expander("📋 Voir le rapport complet", expanded=False):
            st.markdown(st.session_state.generated_report_md)

        st.subheader("📥 Téléchargements")

        # Création des boutons de téléchargement
        cols = st.columns(4)

        # Bouton Markdown
        with cols[0]:
            filename = f"rapport_{datetime.now().strftime('%Y%m%d_%H%M')}"
            st.download_button(
                label="📄 Markdown",
                data=st.session_state.generated_report_md,
                file_name=f"{filename}.md",
                mime="text/markdown",
                help="Format texte avec mise en forme"
            )

        # Bouton PDF
        if hasattr(st.session_state, 'generated_report_pdf') and st.session_state.generated_report_pdf:
            with cols[1]:
                st.download_button(
                    label="📊 PDF",
                    data=st.session_state.generated_report_pdf,
                    file_name=f"{filename}.pdf",
                    mime="application/pdf",
                    help="Document formaté pour impression"
                )

        # Bouton Word
        if hasattr(st.session_state, 'generated_report_word') and st.session_state.generated_report_word:
            with cols[2]:
                st.download_button(
                    label="📝 Word",
                    data=st.session_state.generated_report_word,
                    file_name=f"{filename}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    help="Document éditable Microsoft Word"
                )

        # Bouton HTML
        if hasattr(st.session_state, 'generated_report_html') and st.session_state.generated_report_html:
            with cols[3]:
                st.download_button(
                    label="🌐 HTML",
                    data=st.session_state.generated_report_html,
                    file_name=f"{filename}.html",
                    mime="text/html",
                    help="Page web autonome"
                )

        # Message d'information
        st.info("""
        **Formats disponibles :**
        - **Markdown** : Format texte simple, éditable
        - **PDF** : Document formaté pour impression et partage
        - **Word** : Document éditable (nécessite Microsoft Word)
        - **HTML** : Page web autonome

        *Note : Les exports nécessitent les bibliothèques reportlab et python-docx.*
        """)

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9rem; padding: 1rem;'>
    <p><b>🔒 LIK Insurance Analyst Sécurisé</b> | Architecture Zéro Partage de Données</p>
    <p>Vos données restent 100% locales • Conforme RGPD • Année 2026-2027</p>
    </div>
    """,
    unsafe_allow_html=True
)
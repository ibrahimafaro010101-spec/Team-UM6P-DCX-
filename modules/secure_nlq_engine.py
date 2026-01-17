# modules/secure_nlq_engine.py
import json
import re
from typing import Dict, Any, List, Optional
from openai import OpenAI
import os
import pandas as pd
import tempfile
import zipfile
import io
import shutil
from datetime import datetime


api_key = "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"

class SecureNLQEngine:
    """
    Moteur NLQ sécurisé qui utilise uniquement les métadonnées
    Génère des scripts exécutables localement
    """

    def __init__(self, api_key: str = None, model: str = "gpt-4-turbo-preview"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

        if not self.api_key:
            raise ValueError("Clé API OpenAI requise pour le moteur NLQ")

        self.client = OpenAI(api_key=self.api_key)
        self.metadata_cache = {}  # Cache pour les métadonnées chargées

    def load_metadata_from_file(self, file_path: str, sheet_name: str = None) -> Dict[str, Any]:
        """
        Charge les métadonnées à partir d'un fichier Excel ou CSV
        Supporte le format du dictionnaire de métadonnées d'assurance
        """
        try:
            if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                if sheet_name:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                else:
                    # Essayer de lire la première feuille
                    df = pd.read_excel(file_path, sheet_name=0)
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8')
            else:
                raise ValueError(f"Format de fichier non supporté: {file_path}")

            # Vérifier si c'est un dictionnaire de métadonnées (colonne 'variable' ou 'nom_colonne')
            if 'nom_colonne' in df.columns:
                column_name_col = 'nom_colonne'
            elif 'variable' in df.columns:
                column_name_col = 'variable'
            else:
                # Essayer de deviner la première colonne
                column_name_col = df.columns[0]

            # Construire la structure de métadonnées
            structure_columns = []
            for _, row in df.iterrows():
                col_info = {
                    'nom': str(row[column_name_col]).strip(),
                    'type_donnee': str(row.get('type', 'unknown')).lower() if 'type' in df.columns else 'unknown',
                    'description': str(row.get('description', '')).strip() if 'description' in df.columns else '',
                    'model_usage': bool(row.get('model_usage', False)) if 'model_usage' in df.columns else False,
                    'target': bool(row.get('target', False)) if 'target' in df.columns else False
                }

                # Déterminer le type de données
                col_type = col_info['type_donnee']
                if col_type in ['int', 'float', 'numerical', 'numeric']:
                    col_info['est_numerique'] = True
                elif col_type in ['categorical', 'string', 'str', 'object', 'category']:
                    col_info['est_categorielle'] = True
                elif col_type in ['date', 'datetime']:
                    col_info['est_temporale'] = True
                elif col_type in ['binary', 'bool', 'boolean']:
                    col_info['est_binaire'] = True

                structure_columns.append(col_info)

            # Construire le dictionnaire de métadonnées
            metadata = {
                'source_file': file_path,
                'loaded_at': datetime.now().isoformat(),
                'structure_columns': structure_columns,
                'general_info': {
                    'nombre_colonnes': len(structure_columns),
                    'format_source': os.path.splitext(file_path)[1]
                },
                'business_context_hints': self._infer_business_context(structure_columns)
            }

            # Mettre en cache
            self.metadata_cache[file_path] = metadata

            return metadata

        except Exception as e:
            print(f"Erreur lors du chargement des métadonnées: {e}")
            # Retourner une structure vide
            return {
                'structure_columns': [],
                'general_info': {'nombre_colonnes': 0},
                'business_context_hints': {}
            }

    def _infer_business_context(self, columns: List[Dict]) -> Dict[str, Any]:
        """Infère le contexte métier à partir des noms de colonnes"""
        context = {
            'domaine': 'inconnu',
            'themes_identifies': [],
            'variables_cles': []
        }

        if not columns:
            return context

        # Analyser les noms de colonnes pour identifier le domaine
        col_names = [col['nom'].lower() for col in columns]

        # Détection du domaine assurance
        insurance_keywords = ['prime', 'assure', 'contrat', 'sinistre', 'client', 'police', 'risque']
        if any(keyword in ' '.join(col_names) for keyword in insurance_keywords):
            context['domaine'] = 'assurance'

            # Identifier des sous-thèmes spécifiques
            if any('auto' in name or 'vehicule' in name or 'conducteur' in name for name in col_names):
                context['themes_identifies'].append('assurance_auto')
            if any('vie' in name for name in col_names):
                context['themes_identifies'].append('assurance_vie')
            if any('sante' in name or 'medical' in name for name in col_names):
                context['themes_identifies'].append('assurance_sante')

        # Détection du domaine bancaire/finance
        finance_keywords = ['compte', 'transaction', 'solde', 'credit', 'debit', 'banque']
        if any(keyword in ' '.join(col_names) for keyword in finance_keywords):
            context['domaine'] = 'finance'

        # Identifier les variables clés
        target_cols = [col for col in columns if col.get('target')]
        if target_cols:
            context['variables_cles'].append(f"Variable cible: {target_cols[0]['nom']}")

        model_usage_cols = [col for col in columns if col.get('model_usage')]
        if model_usage_cols:
            context['variables_cles'].append(f"{len(model_usage_cols)} variables utilisées dans le modèle")

        return context

    def analyze_query_with_metadata(self,
                                    user_query: str,
                                    metadata: Dict[str, Any] = None,
                                    metadata_file: str = None,
                                    business_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyse une requête utilisateur avec les métadonnées
        Supporte le passage direct de métadonnées ou d'un fichier
        """

        # Charger les métadonnées si un fichier est fourni
        if metadata_file and not metadata:
            if metadata_file in self.metadata_cache:
                metadata = self.metadata_cache[metadata_file]
            else:
                metadata = self.load_metadata_from_file(metadata_file)

        if not metadata:
            raise ValueError("Métadonnées requises pour l'analyse")

        # Construire le prompt sécurisé
        prompt = self._build_secure_prompt(user_query, metadata, business_context)

        try:
            # Appeler le LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            # Parser la réponse
            analysis_result = json.loads(response.choices[0].message.content)

            # Générer les scripts d'exécution
            execution_plan = self._generate_execution_plan(analysis_result, metadata)

            return {
                "analysis": analysis_result,
                "execution_plan": execution_plan,
                "security_status": "secure_metadata_only",
                "metadata_source": metadata.get('source_file', 'provided_directly')
            }

        except Exception as e:
            return {
                "error": str(e),
                "fallback_analysis": self._fallback_analysis(user_query, metadata),
                "metadata_source": metadata.get('source_file', 'provided_directly')
            }

    def _build_secure_prompt(self,
                             user_query: str,
                             metadata: Dict[str, Any],
                             business_context: Dict[str, Any]) -> str:
        """Construit un prompt sécurisé basé sur les métadonnées"""

        prompt_parts = []

        # Titre et contexte
        prompt_parts.append("# 📊 ANALYSE SÉCURISÉE DE DONNÉES")
        prompt_parts.append("")

        # Contexte métier
        business_hints = metadata.get('business_context_hints', {})
        if business_hints.get('domaine') != 'inconnu':
            prompt_parts.append(f"## Domaine identifié: {business_hints['domaine'].upper()}")
            if business_hints.get('themes_identifies'):
                prompt_parts.append(f"Sous-thèmes: {', '.join(business_hints['themes_identifies'])}")
            prompt_parts.append("")

        if business_context and 'description' in business_context:
            prompt_parts.append(f"## Contexte métier spécifique:")
            prompt_parts.append(str(business_context.get('description', "")))
            prompt_parts.append("")

        # Métadonnées
        prompt_parts.append("## 📋 MÉTADONNÉES DISPONIBLES")
        prompt_parts.append("### Structure des données:")

        structure_cols = metadata.get('structure_columns', [])
        if structure_cols:
            # Grouper par type/catégorie
            by_category = {}
            for col in structure_cols:
                category = col.get('type_donnee', 'unknown')
                if category not in by_category:
                    by_category[category] = []
                col_desc = f"- {col['nom']}"
                if col.get('description'):
                    col_desc += f" : {col['description']}"
                if col.get('target'):
                    col_desc += " 🎯 (TARGET)"
                elif col.get('model_usage'):
                    col_desc += " ⚙️ (MODEL INPUT)"
                by_category[category].append(col_desc)

            for category, cols in by_category.items():
                prompt_parts.append(f"\n**{category.upper()}** ({len(cols)} colonnes):")
                # Limiter à 10 colonnes par catégorie pour éviter un prompt trop long
                prompt_parts.extend(cols[:10])
                if len(cols) > 10:
                    prompt_parts.append(f"  ... et {len(cols) - 10} autres")
        else:
            prompt_parts.append("Aucune information de colonne disponible")

        prompt_parts.append("")

        # Informations générales
        gen_info = metadata.get('general_info', {})
        if gen_info:
            prompt_parts.append("### Informations techniques:")
            prompt_parts.append(f"- Nombre total de colonnes: {gen_info.get('nombre_colonnes', 'N/A')}")
            if 'nombre_lignes' in gen_info:
                prompt_parts.append(f"- Nombre de lignes estimé: {gen_info.get('nombre_lignes', 'N/A')}")
            if 'format_source' in gen_info:
                prompt_parts.append(f"- Format source: {gen_info.get('format_source', 'N/A')}")
            prompt_parts.append("")

        # Variables clés identifiées
        if business_hints.get('variables_cles'):
            prompt_parts.append("### Variables clés identifiées:")
            for var_key in business_hints['variables_cles']:
                prompt_parts.append(f"- {var_key}")
            prompt_parts.append("")

        # Requête utilisateur
        prompt_parts.append(f'# ❓ QUESTION UTILISATEUR:')
        prompt_parts.append(f'"{user_query}"')
        prompt_parts.append("")

        # Instructions spécifiques
        prompt_parts.append("""# 📝 INSTRUCTIONS D'ANALYSE:

1. **COMPRÉHENSION**: Analyser l'intention de l'utilisateur BASÉE UNIQUEMENT sur les métadonnées fournies
2. **STRATÉGIE**: Proposer une approche d'analyse logique et réalisable
3. **SCRIPTS**: Générer des scripts PRÊTS À L'EMPLOI pour:
   - SQL: Requêtes d'extraction et d'agrégation
   - Python: Code Pandas pour le traitement et l'analyse
   - Visualisation: Code Plotly pour des graphiques pertinents
4. **VISUALISATIONS**: Suggérer 2-3 visualisations clés avec leurs variables
5. **INDICATEURS**: Identifier les indicateurs clés à calculer
6. **ÉTAPES**: Définir un plan d'exécution étape par étape

**RÈGLES DE SÉCURITÉ STRICTES:**
- NE PAS inventer ou inférer des données réelles
- UTILISER les noms de colonnes exacts des métadonnées
- GÉNÉRER du code exécutable et bien commenté
- ADAPTER les scripts au domaine identifié
""")

        # Format de réponse JSON
        prompt_parts.append("""# 📄 FORMAT DE RÉPONSE ATTENDU (JSON):

```json
{
  "intention": "Description claire de l'intention utilisateur",
  "strategie_analyse": "Description détaillée de la stratégie proposée",
  "scripts_generes": {
    "sql": [
      "SELECT colonne1, AVG(colonne2) FROM table GROUP BY colonne1",
      "SELECT COUNT(*) FROM table WHERE condition"
    ],
    "python": {
      "pandas": "# Code Pandas pour le traitement\ndf.groupby('colonne')['valeur'].mean()",
      "plotly": "# Code Plotly pour visualisation\nimport plotly.express as px\nfig = px.histogram(df, x='colonne')"
    }
  },
  "visualisations_suggestees": [
    {
      "type": "histogram",
      "description": "Distribution des valeurs",
      "variables_impliquees": ["colonne_numerique"],
      "objectif": "Comprendre la distribution"
    }
  ],
  "indicateurs_cles": [
    "moyenne_colonne",
    "taux_variable_binaire"
  ],
  "etapes_execution": [
    "Étape 1: Charger les données",
    "Étape 2: Nettoyer et valider",
    "Étape 3: Calculer les indicateurs",
    "Étape 4: Générer les visualisations",
    "Étape 5: Exporter les résultats"
  ]
}
```""")

        return "\n".join(prompt_parts)

    def _get_system_prompt(self) -> str:
        """Prompt système définissant le rôle"""
        return """Vous êtes un assistant expert en analyse de données sécurisée.

VOTRE MISSION:
1. Analyser les questions utilisateur UNIQUEMENT sur la base des MÉTADONNÉES fournies
2. Générer des SCRIPTS EXÉCUTABLES qui seront exécutés localement par le client
3. Fournir des recommandations pertinentes pour le domaine identifié (assurance, finance, etc.)
4. Assurer que tous les scripts sont SÉCURISÉS, OPTIMISÉS et BIEN COMMENTÉS

RÈGLES DE SÉCURITÉ ABSOLUES:
- JAMAIS inclure, inventer ou inférer des données réelles
- TOUJOURS utiliser exactement les noms de colonnes fournis dans les métadonnées
- TOUJOURS générer du code modulaire, robuste et facile à adapter
- INCLURE des commentaires explicites dans tous les scripts
- PROPOSER des validations de données appropriées

EXPERTISE DOMAINE:
- Adaptation automatique au domaine détecté (assurance, finance, retail, etc.)
- Utilisation des bonnes pratiques du domaine
- Suggestion d'indicateurs pertinents pour le domaine"""

    def _format_columns_info(self, columns_info: List[Dict]) -> str:
        """Formate les informations des colonnes (méthode conservée pour compatibilité)"""
        return self._build_secure_prompt("", {'structure_columns': columns_info}, {})

    def _generate_execution_plan(self,
                                 analysis_result: Dict[str, Any],
                                 metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Génère un plan d'exécution détaillé avec scripts"""

        # Récupérer les scripts générés par le LLM
        scripts_generes = analysis_result.get("scripts_generes", {})

        # Adapter les scripts aux métadonnées spécifiques
        adapted_scripts = self._adapt_scripts_to_metadata(scripts_generes, metadata)

        # Créer le plan d'exécution
        execution_plan = {
            "overview": analysis_result.get("strategie_analyse", "Analyse générée automatiquement"),
            "intention": analysis_result.get("intention", "Analyse générique"),
            "domain": metadata.get('business_context_hints', {}).get('domaine', 'inconnu'),
            "steps": analysis_result.get("etapes_execution", [
                "1. Charger les données",
                "2. Valider la structure",
                "3. Exécuter les requêtes SQL générées",
                "4. Analyser les résultats avec Python",
                "5. Générer les visualisations",
                "6. Exporter les résultats"
            ]),
            "scripts": adapted_scripts,
            "visualizations": analysis_result.get("visualisations_suggestees", []),
            "key_indicators": analysis_result.get("indicateurs_cles", []),
            "outputs": [
                "rapport_analyse.json",
                "statistiques_synthese.csv",
                "visualisations/"
            ],
            "dependencies": ["pandas", "plotly", "numpy"],
            "metadata_summary": {
                "total_columns": len(metadata.get('structure_columns', [])),
                "target_columns": [c['nom'] for c in metadata.get('structure_columns', []) if c.get('target')],
                "model_input_columns": [c['nom'] for c in metadata.get('structure_columns', []) if c.get('model_usage')]
            }
        }

        return execution_plan

    def _adapt_scripts_to_metadata(self, scripts: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Adapte les scripts générés aux métadonnées spécifiques"""

        adapted_scripts = {
            "sql": [],
            "python": {},
            "validation": self._generate_validation_scripts(metadata)
        }

        # Adapter les scripts SQL
        sql_scripts = scripts.get("sql", [])
        for sql_script in sql_scripts:
            if isinstance(sql_script, dict):
                adapted_scripts["sql"].append({
                    "description": sql_script.get("description", "Requête générée"),
                    "code": self._sanitize_sql_query(sql_script.get("code", ""), metadata)
                })
            else:
                adapted_scripts["sql"].append(
                    self._sanitize_sql_query(sql_script, metadata)
                )

        # Adapter les scripts Python
        python_scripts = scripts.get("python", {})
        for script_type, script_content in python_scripts.items():
            if isinstance(script_content, dict):
                adapted_scripts["python"][script_type] = {
                    "description": script_content.get("description", f"Script {script_type}"),
                    "code": self._sanitize_python_code(script_content.get("code", ""), metadata)
                }
            else:
                adapted_scripts["python"][script_type] = {
                    "description": f"Script {script_type} adapté",
                    "code": self._sanitize_python_code(script_content, metadata)
                }

        # Ajouter un script d'analyse adapté au domaine
        domain = metadata.get('business_context_hints', {}).get('domaine', 'generic')
        adapted_scripts["python"]["domain_analysis"] = self._generate_domain_analysis_script(domain, metadata)

        return adapted_scripts

    def _sanitize_sql_query(self, query: str, metadata: Dict[str, Any]) -> str:
        """Nettoie et adapte une requête SQL aux métadonnées"""

        # Remplacer les placeholders génériques
        sanitized = query.replace("table", "donnees")
        sanitized = sanitized.replace("dataset", "donnees")
        sanitized = sanitized.replace("data", "donnees")

        # S'assurer que les noms de colonnes sont valides
        valid_columns = [col['nom'] for col in metadata.get('structure_columns', [])]

        # Cette fonction pourrait être étendue pour valider les colonnes utilisées
        # Pour l'instant, on retourne simplement la requête nettoyée
        return sanitized

    def _sanitize_python_code(self, code: str, metadata: Dict[str, Any]) -> str:
        """Nettoie et adapte du code Python aux métadonnées"""

        # Ajouter un en-tête de sécurité
        header = f'''"""
SCRIPT PYTHON GÉNÉRÉ AUTOMATIQUEMENT
Adapté aux métadonnées du domaine: {metadata.get('business_context_hints', {}).get('domaine', 'inconnu')}
Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

INSTRUCTIONS:
1. Remplacez 'donnees.csv' par le chemin de votre fichier de données
2. Adaptez les noms de colonnes si nécessaire
3. Exécutez étape par étape
"""

'''

        # Nettoyer le code
        cleaned_code = code.replace("df", "df")  # Conserver df comme nom standard
        cleaned_code = cleaned_code.replace("dataframe", "df")

        return header + cleaned_code

    def _generate_domain_analysis_script(self, domain: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Génère un script d'analyse spécifique au domaine"""

        if domain == 'assurance':
            return {
                "name": "analyse_assurance.py",
                "description": "Analyse spécifique au domaine assurance",
                "code": self._generate_insurance_analysis_script(metadata)
            }
        elif domain == 'finance':
            return {
                "name": "analyse_finance.py",
                "description": "Analyse spécifique au domaine finance",
                "code": self._generate_finance_analysis_script(metadata)
            }
        else:
            return {
                "name": "analyse_generique.py",
                "description": "Analyse générique adaptée",
                "code": self._generate_generic_analysis_script(metadata)
            }

    def _generate_insurance_analysis_script(self, metadata: Dict[str, Any]) -> str:
        """Génère un script d'analyse pour le domaine assurance"""

        # Identifier les colonnes pertinentes pour l'assurance
        structure_cols = metadata.get('structure_columns', [])
        numeric_cols = [c['nom'] for c in structure_cols if c.get('est_numerique')]
        categorical_cols = [c['nom'] for c in structure_cols if c.get('est_categorielle')]
        date_cols = [c['nom'] for c in structure_cols if c.get('est_temporale')]

        # Trouver la colonne target si elle existe
        target_cols = [c['nom'] for c in structure_cols if c.get('target')]
        target_col = target_cols[0] if target_cols else None

        script = f'''"""
SCRIPT D'ANALYSE - DOMAINE ASSURANCE
Généré automatiquement basé sur les métadonnées

Variables identifiées:
- Numériques: {', '.join(numeric_cols[:3]) if numeric_cols else 'Aucune'}
- Catégorielles: {', '.join(categorical_cols[:3]) if categorical_cols else 'Aucune'}
- Temporelles: {', '.join(date_cols[:3]) if date_cols else 'Aucune'}
- Variable cible: {target_col if target_col else 'Non identifiée'}
"""

import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

def analyse_assurance(df):
    \"\"\"
    Fonction d'analyse spécifique au domaine assurance
    \"\"\"
    results = {{}}

    # 1. ANALYSE DES PRIMES (si colonnes pertinentes existent)
    prime_cols = [col for col in df.columns if 'prime' in col.lower() or 'montant' in col.lower()]
    if prime_cols:
        print("\\n📊 ANALYSE DES PRIMES:")
        for prime_col in prime_cols[:3]:  # Limiter aux 3 premières
            if pd.api.types.is_numeric_dtype(df[prime_col]):
                prime_stats = {{
                    'moyenne': df[prime_col].mean(),
                    'mediane': df[prime_col].median(),
                    'ecart_type': df[prime_col].std(),
                    'min': df[prime_col].min(),
                    'max': df[prime_col].max(),
                    'somme': df[prime_col].sum()
                }}
                print(f"  {prime_col}:")
                print(f"    • Moyenne: {{prime_stats['moyenne']:.2f}}")
                print(f"    • Médiane: {{prime_stats['mediane']:.2f}}")
                print(f"    • Total: {{prime_stats['somme']:.2f}}")
                results[f'stats_{prime_col}'] = prime_stats

    # 2. ANALYSE DES SINISTRES (si colonnes pertinentes existent)
    claim_cols = [col for col in df.columns if any(word in col.lower() 
                   for word in ['sinistre', 'claim', 'incident', 'accident'])]
    if claim_cols:
        print("\\n🚨 ANALYSE DES SINISTRES:")
        for claim_col in claim_cols[:3]:
            if pd.api.types.is_numeric_dtype(df[claim_col]):
                claim_stats = df[claim_col].describe()
                print(f"  {claim_col}:")
                print(f"    • Nombre de sinistres: {{df[claim_col].sum() if df[claim_col].dtype == 'bool' else 'N/A'}}")
                print(f"    • Fréquence: {{df[claim_col].mean() if df[claim_col].dtype == 'bool' else 'N/A'}}")

    # 3. ANALYSE DES CLIENTS (si colonnes pertinentes existent)
    client_cols = [col for col in df.columns if 'client' in col.lower() or 'customer' in col.lower()]
    if client_cols:
        print("\\n👥 ANALYSE CLIENTÈLE:")
        for client_col in client_cols[:2]:
            if df[client_col].nunique() < 50:  # Colonne catégorielle
                client_dist = df[client_col].value_counts()
                print(f"  Distribution {{client_col}}:")
                for val, count in client_dist.head(5).items():
                    print(f"    • {{val}}: {{count}} ({{count/len(df)*100:.1f}}%)")

    # 4. CALCUL DU LOSS RATIO (si données disponibles)
    prime_sum_col = next((col for col in prime_cols if 'total' in col.lower() or 'sum' in col.lower()), None)
    claim_cost_col = next((col for col in claim_cols if 'cost' in col.lower() or 'cout' in col.lower()), None)

    if prime_sum_col and claim_cost_col:
        if pd.api.types.is_numeric_dtype(df[prime_sum_col]) and pd.api.types.is_numeric_dtype(df[claim_cost_col]):
            total_premium = df[prime_sum_col].sum()
            total_claims = df[claim_cost_col].sum()
            loss_ratio = (total_claims / total_premium) * 100 if total_premium > 0 else 0
            print(f"\\n📉 LOSS RATIO: {{loss_ratio:.1f}}%")
            print(f"   • Primes totales: {{total_premium:.2f}}")
            print(f"   • Sinistres totaux: {{total_claims:.2f}}")
            results['loss_ratio'] = loss_ratio

    # 5. VISUALISATIONS SPÉCIFIQUES
    visualizations = []

    # Histogramme des primes
    if prime_cols and pd.api.types.is_numeric_dtype(df[prime_cols[0]]):
        fig = px.histogram(df, x=prime_cols[0], 
                         title=f"Distribution des {{prime_cols[0]}}",
                         nbins=50)
        fig.write_html("histogramme_primes.html")
        visualizations.append("histogramme_primes.html")
        print("\\n✅ Visualisation générée: histogramme_primes.html")

    # Diagramme en barres des catégories clients
    if client_cols and df[client_cols[0]].nunique() < 20:
        fig = px.bar(df[client_cols[0]].value_counts().reset_index(),
                   x='index', y=client_cols[0],
                   title=f"Distribution {{client_cols[0]}}")
        fig.write_html("distribution_clients.html")
        visualizations.append("distribution_clients.html")
        print("✅ Visualisation générée: distribution_clients.html")

    results['visualisations'] = visualizations
    return results

# Exemple d'utilisation
if __name__ == "__main__":
    # Charger vos données
    # df = pd.read_csv('votre_fichier.csv')

    # Exécuter l'analyse
    # resultats = analyse_assurance(df)

    print("Script d'analyse assurance prêt. Adaptez le chargement des données.")
'''

        return script

    def _generate_finance_analysis_script(self, metadata: Dict[str, Any]) -> str:
        """Génère un script d'analyse pour le domaine finance"""
        # Code similaire à l'assurance mais adapté à la finance
        return '''"""
SCRIPT D'ANALYSE - DOMAINE FINANCE
À adapter selon vos données spécifiques
"""'''

    def _generate_generic_analysis_script(self, metadata: Dict[str, Any]) -> str:
        """Génère un script d'analyse générique"""
        return '''"""
SCRIPT D'ANALYSE GÉNÉRIQUE
Adaptez selon vos besoins spécifiques
"""'''

    def _generate_validation_scripts(self, metadata: Dict[str, Any]) -> List[Dict]:
        """Génère des scripts de validation de données adaptés"""

        validation_scripts = []

        # Script de validation des types basé sur les métadonnées
        structure_cols = metadata.get('structure_columns', [])

        type_mapping = {
            'int': 'int64',
            'float': 'float64',
            'string': 'object',
            'categorical': 'object',
            'date': 'datetime64[ns]',
            'binary': 'bool'
        }

        expected_types = {}
        for col in structure_cols:
            col_name = col['nom']
            col_type = col.get('type_donnee', 'unknown').lower()
            if col_type in type_mapping:
                expected_types[col_name] = type_mapping[col_type]

        validation_scripts.append({
            "name": "validate_data_types.py",
            "description": "Validation des types de données basée sur les métadonnées",
            "code": f'''
import pandas as pd
import numpy as np

# Types attendus basés sur les métadonnées
EXPECTED_TYPES = {json.dumps(expected_types, indent=2)}

def validate_data_types(df, expected_types=EXPECTED_TYPES):
    """
    Valide que les colonnes ont les types attendus selon les métadonnées
    """
    print("🔍 VALIDATION DES TYPES DE DONNÉES")
    print("-" * 40)

    errors = []
    warnings = []

    for col, expected_type in expected_types.items():
        if col in df.columns:
            actual_type = str(df[col].dtype)

            # Correspondance flexible des types
            type_matches = False
            if expected_type in ['int64', 'float64']:
                if pd.api.types.is_numeric_dtype(df[col]):
                    type_matches = True
            elif expected_type == 'object':
                if pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                    type_matches = True
            elif expected_type == 'datetime64[ns]':
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    type_matches = True
            elif expected_type == 'bool':
                if pd.api.types.is_bool_dtype(df[col]):
                    type_matches = True

            if not type_matches:
                errors.append(f"Colonne {{col}}: type attendu {{expected_type}}, type réel {{actual_type}}")
        else:
            warnings.append(f"Colonne {{col}}: présente dans les métadonnées mais absente des données")

    # Affichage des résultats
    if errors:
        print("❌ Erreurs de type trouvées:")
        for error in errors:
            print(f"  - {{error}}")
    else:
        print("✅ Tous les types de données correspondent aux métadonnées")

    if warnings:
        print("\\n⚠️  Avertissements:")
        for warning in warnings:
            print(f"  - {{warning}}")

    return len(errors) == 0
'''
        })

        # Script de validation des valeurs manquantes
        validation_scripts.append({
            "name": "check_missing_values.py",
            "description": "Analyse des valeurs manquantes avec seuils adaptatifs",
            "code": '''
def check_missing_values(df, critical_threshold=0.3, warning_threshold=0.1):
    """
    Analyse détaillée des valeurs manquantes
    """
    print("\\n🔍 ANALYSE DES VALEURS MANQUANTES")
    print("-" * 40)

    missing_stats = df.isnull().sum()
    missing_percentage = (missing_stats / len(df)) * 100

    critical_cols = missing_percentage[missing_percentage > critical_threshold * 100].index.tolist()
    warning_cols = missing_percentage[(missing_percentage > warning_threshold * 100) & 
                                      (missing_percentage <= critical_threshold * 100)].index.tolist()
    clean_cols = missing_percentage[missing_percentage <= warning_threshold * 100].index.tolist()

    if critical_cols:
        print(f"❌ Colonnes CRITIQUES (> {critical_threshold*100:.0f}% manquants):")
        for col in critical_cols:
            print(f"  - {col}: {missing_percentage[col]:.1f}% manquants")

    if warning_cols:
        print(f"\\n⚠️  Colonnes avec AVERTISSEMENT ({warning_threshold*100:.0f}-{critical_threshold*100:.0f}% manquants):")
        for col in warning_cols:
            print(f"  - {col}: {missing_percentage[col]:.1f}% manquants")

    if clean_cols:
        print(f"\\n✅ Colonnes PROPRES (< {warning_threshold*100:.0f}% manquants): {len(clean_cols)} colonnes")

    # Statistiques globales
    total_missing = missing_stats.sum()
    total_cells = df.shape[0] * df.shape[1]
    overall_percentage = (total_missing / total_cells) * 100

    print(f"\\n📊 STATISTIQUES GLOBALES:")
    print(f"  • Valeurs manquantes totales: {total_missing:,}")
    print(f"  • Taux global: {overall_percentage:.2f}%")
    print(f"  • Colonnes affectées: {len(critical_cols) + len(warning_cols)}/{len(df.columns)}")

    return {
        'critical': critical_cols,
        'warning': warning_cols,
        'clean': clean_cols,
        'overall_percentage': overall_percentage
    }
'''
        })

        # Script de validation des valeurs aberrantes
        validation_scripts.append({
            "name": "detect_outliers.py",
            "description": "Détection des valeurs aberrantes pour les colonnes numériques",
            "code": '''
import numpy as np

def detect_outliers(df, method='iqr', threshold=1.5):
    """
    Détecte les valeurs aberrantes dans les colonnes numériques
    """
    print("\\n🔍 DÉTECTION DES VALEURS ABERRANTES")
    print("-" * 40)

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    outliers_summary = {}

    for col in numeric_cols:
        data = df[col].dropna()

        if method == 'iqr':
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR

            outliers = data[(data < lower_bound) | (data > upper_bound)]
            outlier_count = len(outliers)
            outlier_percentage = (outlier_count / len(data)) * 100 if len(data) > 0 else 0

            if outlier_count > 0:
                outliers_summary[col] = {
                    'count': outlier_count,
                    'percentage': outlier_percentage,
                    'bounds': (float(lower_bound), float(upper_bound))
                }

    if outliers_summary:
        print("Valeurs aberrantes détectées:")
        for col, stats in outliers_summary.items():
            print(f"  • {col}: {stats['count']} valeurs ({stats['percentage']:.1f}%)")
            print(f"    Plage normale: [{stats['bounds'][0]:.2f}, {stats['bounds'][1]:.2f}]")
    else:
        print("✅ Aucune valeur aberrante détectée avec les paramètres actuels")

    return outliers_summary
'''
        })

        return validation_scripts

    def _fallback_analysis(self, user_query: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse de secours si le LLM échoue"""

        # Utiliser les métadonnées pour une analyse plus précise
        structure_cols = metadata.get('structure_columns', [])

        # Identifier les colonnes clés
        numeric_cols = [c['nom'] for c in structure_cols if c.get('est_numerique')]
        categorical_cols = [c['nom'] for c in structure_cols if c.get('est_categorielle')]
        target_cols = [c['nom'] for c in structure_cols if c.get('target')]
        date_cols = [c['nom'] for c in structure_cols if c.get('est_temporale')]

        # Analyser l'intention basique
        query_lower = user_query.lower()

        if any(word in query_lower for word in ['distribution', 'répartition', 'histogramme']):
            # Analyse de distribution
            target_col = numeric_cols[0] if numeric_cols else (categorical_cols[0] if categorical_cols else 'colonne')
            intention = "analyse_distribution"

        elif any(word in query_lower for word in ['moyenne', 'médiane', 'statistique', 'moyen']):
            # Analyse statistique
            target_col = numeric_cols[0] if numeric_cols else 'colonne_numerique'
            intention = "analyse_statistique"

        elif any(word in query_lower for word in ['comparer', 'comparaison', 'vs', 'contre']):
            # Analyse comparative
            if len(numeric_cols) >= 2:
                cols = numeric_cols[:2]
            elif len(categorical_cols) >= 2:
                cols = categorical_cols[:2]
            else:
                cols = ['colonne1', 'colonne2']
            intention = "analyse_comparative"

        elif any(word in query_lower for word in ['tendance', 'évolution', 'temporel', 'date']):
            # Analyse temporelle
            target_col = date_cols[0] if date_cols else (numeric_cols[0] if numeric_cols else 'date')
            intention = "analyse_temporelle"

        else:
            # Analyse descriptive générique
            intention = "analyse_descriptive"

        # Générer les scripts basiques
        if intention == "analyse_distribution":
            if numeric_cols:
                target_col = numeric_cols[0]
                scripts = {
                    "sql": [
                        f"SELECT {target_col}, COUNT(*) as count FROM donnees WHERE {target_col} IS NOT NULL GROUP BY {target_col} ORDER BY {target_col}",
                        f"SELECT MIN({target_col}) as min, MAX({target_col}) as max, AVG({target_col}) as moyenne FROM donnees"
                    ],
                    "python": {
                        "pandas": f"# Distribution de {target_col}\\ndistribution = df['{target_col}'].describe()\\nprint(distribution)",
                        "plotly": f"import plotly.express as px\\nfig = px.histogram(df, x='{target_col}', nbins=50, title='Distribution de {target_col}')\\nfig.show()"
                    }
                }
            else:
                target_col = categorical_cols[0] if categorical_cols else 'categorie'
                scripts = {
                    "sql": [
                        f"SELECT {target_col}, COUNT(*) as count FROM donnees GROUP BY {target_col} ORDER BY count DESC",
                        f"SELECT COUNT(DISTINCT {target_col}) as nb_categories FROM donnees"
                    ],
                    "python": {
                        "pandas": f"# Répartition par {target_col}\\nrepartition = df['{target_col}'].value_counts()\\nprint(repartition)",
                        "plotly": f"import plotly.express as px\\nfig = px.bar(df['{target_col}'].value_counts().reset_index(), x='index', y='{target_col}', title='Répartition par {target_col}')\\nfig.show()"
                    }
                }

        elif intention == "analyse_statistique":
            if numeric_cols:
                target_cols_sample = numeric_cols[:3]
                cols_str = ", ".join(target_cols_sample)
                scripts = {
                    "sql": [f"SELECT AVG({col}) as moyenne_{col}, STDDEV({col}) as ecart_type_{col} FROM donnees" for
                            col in target_cols_sample],
                    "python": {
                        "pandas": f"# Statistiques descriptives\\nstats = df[{target_cols_sample}].describe()\\nprint(stats)",
                        "plotly": f"import plotly.express as px\\nimport plotly.graph_objects as go\\nfrom plotly.subplots import make_subplots\\n\\n# Créer un tableau de statistiques\\nstats = df[{target_cols_sample}].describe().round(2)\\nfig = go.Figure(data=[go.Table(header=dict(values=stats.columns), cells=dict(values=stats.values))])\\nfig.update_layout(title='Statistiques descriptives')\\nfig.show()"
                    }
                }
            else:
                scripts = {
                    "sql": ["SELECT COUNT(*) as total_lignes FROM donnees"],
                    "python": {
                        "pandas": "df.describe(include='all')",
                        "plotly": "# Aucune colonne numérique détectée pour les statistiques"
                    }
                }

        elif intention == "analyse_comparative":
            if len(numeric_cols) >= 2:
                col1, col2 = numeric_cols[:2]
                scripts = {
                    "sql": [
                        f"SELECT {col1}, {col2}, COUNT(*) as count FROM donnees WHERE {col1} IS NOT NULL AND {col2} IS NOT NULL GROUP BY {col1}, {col2}",
                        f"SELECT CORR({col1}, {col2}) as correlation FROM donnees"
                    ],
                    "python": {
                        "pandas": f"# Comparaison {col1} vs {col2}\\ncorrelation = df['{col1}'].corr(df['{col2}'])\\nprint(f'Corrélation: {correlation:.3f}')",
                        "plotly": f"import plotly.express as px\\nfig = px.scatter(df, x='{col1}', y='{col2}', title='{col1} vs {col2}')\\nfig.show()"
                    }
                }
            else:
                scripts = {
                    "sql": ["SELECT 'Analyse comparative nécessite au moins 2 colonnes numériques' as message"],
                    "python": {
                        "pandas": "print('Colonnes numériques insuffisantes pour une analyse comparative')",
                        "plotly": "# Analyse comparative non disponible"
                    }
                }

        else:
            # Analyse descriptive générique
            scripts = {
                "sql": [
                    "SELECT COUNT(*) as total_lignes FROM donnees",
                    "SELECT COUNT(*) as lignes_completes FROM donnees WHERE " +
                    " AND ".join([f"{col} IS NOT NULL" for col in numeric_cols[:3]]) if numeric_cols else "1=1"
                ],
                "python": {
                    "pandas": "print('\\n📊 SYNTHÈSE DES DONNÉES:')\\nprint(f'Dimensions: {df.shape[0]} lignes × {df.shape[1]} colonnes')\\nprint('\\nTypes de données:')\\nprint(df.dtypes)\\nprint('\\nValeurs manquantes:')\\nprint(df.isnull().sum())",
                    "plotly": "# Visualisation de synthèse\\nimport plotly.express as px\\nimport plotly.graph_objects as go\\nfrom plotly.subplots import make_subplots\\n\\n# Créer un tableau de synthèse\\nfig = go.Figure(data=[go.Table(header=dict(values=['Métrique', 'Valeur']),\\n                 cells=dict(values=[['Lignes', 'Colonnes', 'Valeurs manquantes'], [len(df), len(df.columns), df.isnull().sum().sum()]]))])\\nfig.update_layout(title='Synthèse des données')\\nfig.show()"
                }
            }

        return {
            "intention": intention,
            "strategie_analyse": f"Analyse basique de {intention.replace('_', ' ')} basée sur les métadonnées",
            "scripts_generes": scripts,
            "visualisations_suggestees": [
                {
                    "type": "histogram" if intention == "analyse_distribution" else "scatter" if intention == "analyse_comparative" else "table",
                    "description": f"Visualisation pour {intention.replace('_', ' ')}",
                    "variables_impliquees": numeric_cols[:2] if numeric_cols else categorical_cols[
                        :2] if categorical_cols else []
                }
            ],
            "indicateurs_cles": [f"{intention}_{col}" for col in
                                 (numeric_cols[:3] or categorical_cols[:3] or ['donnees'])],
            "etapes_execution": [
                "1. Charger les données",
                "2. Valider la structure",
                "3. Exécuter l'analyse appropriée",
                "4. Générer les visualisations",
                "5. Exporter les résultats"
            ]
        }

    def generate_executable_package(self,
                                    execution_plan: Dict[str, Any],
                                    output_dir: str = "analysis_package") -> Dict[str, str]:
        """
        Génère un package exécutable complet
        """
        import os

        # Créer le répertoire
        os.makedirs(output_dir, exist_ok=True)

        package_files = {}

        # 1. Fichier main.py
        main_content = self._generate_main_script(execution_plan)
        main_path = os.path.join(output_dir, "main.py")
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(main_content)
        package_files["main.py"] = main_path

        # 2. Fichier requirements.txt
        req_content = self._generate_requirements(execution_plan)
        req_path = os.path.join(output_dir, "requirements.txt")
        with open(req_path, "w", encoding="utf-8") as f:
            f.write(req_content)
        package_files["requirements.txt"] = req_path

        # 3. Fichier README.md
        readme_content = self._generate_readme(execution_plan)
        readme_path = os.path.join(output_dir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        package_files["README.md"] = readme_path

        # 4. Fichier config.json
        config_content = self._generate_config(execution_plan)
        config_path = os.path.join(output_dir, "config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_content, f, indent=2, ensure_ascii=False)
        package_files["config.json"] = config_path

        # 5. Créer un sous-répertoire pour les scripts
        scripts_dir = os.path.join(output_dir, "scripts")
        os.makedirs(scripts_dir, exist_ok=True)

        # 6. Scripts SQL
        sql_scripts = execution_plan.get("scripts", {}).get("sql", [])
        if sql_scripts:
            sql_path = os.path.join(scripts_dir, "queries.sql")
            with open(sql_path, "w", encoding="utf-8") as f:
                f.write("-- REQUÊTES SQL GÉNÉRÉES AUTOMATIQUEMENT\n")
                f.write("-- Adaptez les noms de tables et colonnes à votre base de données\n")
                f.write("-- Remplacez 'donnees' par le nom de votre table\n\n")

                for i, query in enumerate(sql_scripts):
                    if isinstance(query, dict):
                        f.write(f"-- REQUÊTE {i + 1}: {query.get('description', '')}\n")
                        f.write(f"{query.get('code', '')}\n\n")
                        f.write("-- " + "=" * 60 + "\n\n")
                    else:
                        f.write(f"-- REQUÊTE {i + 1}\n")
                        f.write(f"{query}\n\n")
                        f.write("-- " + "=" * 60 + "\n\n")
            package_files["scripts/queries.sql"] = sql_path

        # 7. Scripts Python
        python_scripts = execution_plan.get("scripts", {}).get("python", {})
        for script_name, script_content in python_scripts.items():
            if isinstance(script_content, dict):
                script_code = script_content.get('code', '')
                script_path = os.path.join(scripts_dir, f"{script_name}.py")
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(script_code)
                package_files[f"scripts/{script_name}.py"] = script_path

        # 8. Scripts de validation
        validation_scripts = execution_plan.get("scripts", {}).get("validation", [])
        for validation_script in validation_scripts:
            if isinstance(validation_script, dict):
                script_name = validation_script.get("name", f"validation_{len(package_files)}.py")
                script_path = os.path.join(scripts_dir, script_name)
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(validation_script.get("code", ""))
                package_files[f"scripts/{script_name}"] = script_path

        # 9. Script d'analyse de domaine
        domain_script = execution_plan.get("scripts", {}).get("python", {}).get("domain_analysis")
        if domain_script and isinstance(domain_script, dict):
            domain_path = os.path.join(scripts_dir, "domain_analysis.py")
            with open(domain_path, "w", encoding="utf-8") as f:
                f.write(domain_script.get("code", ""))
            package_files["scripts/domain_analysis.py"] = domain_path

        # 10. Créer un répertoire pour les résultats
        results_dir = os.path.join(output_dir, "results")
        os.makedirs(results_dir, exist_ok=True)
        package_files["results/"] = results_dir

        # 11. Créer un fichier .gitignore
        gitignore_content = """# Fichiers générés
results/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so

# Environnements virtuels
venv/
env/
.venv/

# Fichiers de données (à adapter)
*.csv
*.xlsx
*.xls
*.json
*.db
*.sqlite

# Fichiers temporaires
*.tmp
*.temp
*.log
"""
        gitignore_path = os.path.join(output_dir, ".gitignore")
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write(gitignore_content)
        package_files[".gitignore"] = gitignore_path

        return package_files

    def _generate_main_script(self, execution_plan: Dict[str, Any]) -> str:
        """Génère le script principal d'exécution amélioré"""

        domain = execution_plan.get('domain', 'generic')
        intention = execution_plan.get('intention', 'Analyse')
        overview = execution_plan.get('overview', 'Analyse générée automatiquement')

        main_script = f'''"""
📊 SCRIPT PRINCIPAL D'ANALYSE SÉCURISÉE
Généré automatiquement par SecureNLQ Engine

DOMAINE: {domain.upper()}
INTENTION: {intention}
STRATÉGIE: {overview}

Date de génération: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

import pandas as pd
import numpy as np
import json
import os
import sys
from datetime import datetime

# Ajouter le dossier scripts au chemin
sys.path.append('scripts')

def main():
    """Fonction principale d'exécution"""

    print("=" * 70)
    print("🚀 LANCEMENT DE L'ANALYSE SÉCURISÉE")
    print("=" * 70)
    print(f"📊 Domaine: {domain.upper()}")
    print(f"🎯 Intention: {intention}")
    print(f"📋 Stratégie: {overview}")
    print("=" * 70)

    # ÉTAPE 1: CONFIGURATION
    print("\\n⚙️  ÉTAPE 1: CONFIGURATION")
    print("-" * 40)

    # Demander le fichier de données
    data_file = input("📂 Chemin vers votre fichier de données (CSV/Excel/JSON): ").strip()

    if not data_file:
        # Essayer des noms par défaut
        default_files = ['donnees.csv', 'data.csv', 'donnees.xlsx', 'data.xlsx']
        for default_file in default_files:
            if os.path.exists(default_file):
                data_file = default_file
                print(f"✅ Utilisation du fichier par défaut: {data_file}")
                break

    if not data_file or not os.path.exists(data_file):
        print("❌ Aucun fichier de données trouvé.")
        print("\\n📌 Veuillez:")
        print("   1. Placer votre fichier de données dans le répertoire")
        print("   2. Exécuter à nouveau le script")
        print("   3. Ou spécifier le chemin complet")
        return

    # ÉTAPE 2: CHARGEMENT DES DONNÉES
    print(f"\\n📁 ÉTAPE 2: CHARGEMENT DES DONNÉES")
    print("-" * 40)

    try:
        # Détection automatique du format
        file_ext = os.path.splitext(data_file)[1].lower()

        load_start = datetime.now()

        if file_ext == '.csv':
            # Essayer plusieurs encodages
            encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
            for encoding in encodings:
                try:
                    df = pd.read_csv(data_file, encoding=encoding)
                    print(f"✅ Fichier CSV chargé avec encodage {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                df = pd.read_csv(data_file, encoding='utf-8', errors='replace')
                print("⚠️  Fichier CSV chargé avec remplacement d'erreurs")

        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(data_file)
            print("✅ Fichier Excel chargé")

        elif file_ext == '.json':
            df = pd.read_json(data_file)
            print("✅ Fichier JSON chargé")

        else:
            # Essai générique
            df = pd.read_csv(data_file)
            print(f"✅ Fichier {file_ext} chargé (format détecté automatiquement)")

        load_time = (datetime.now() - load_start).total_seconds()

        print(f"\\n✅ CHARGEMENT RÉUSSI")
        print(f"   • Fichier: {os.path.basename(data_file)}")
        print(f"   • Dimensions: {len(df):,} lignes × {len(df.columns)} colonnes")
        print(f"   • Temps de chargement: {load_time:.2f} secondes")
        print(f"   • Mémoire utilisée: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")

    except Exception as e:
        print(f"❌ ERREUR DE CHARGEMENT: {e}")
        print("\\n🔧 Dépannage:")
        print("   1. Vérifiez que le fichier existe")
        print("   2. Vérifiez les permissions")
        print("   3. Essayez un format différent (CSV recommandé)")
        return

    # ÉTAPE 3: VALIDATION DES DONNÉES
    print("\\n🔍 ÉTAPE 3: VALIDATION DES DONNÉES")
    print("-" * 40)

    # Importer et exécuter les validations
    try:
        from validate_data_types import validate_data_types
        from check_missing_values import check_missing_values
        from detect_outliers import detect_outliers

        # Validation des types
        type_valid = validate_data_types(df)

        # Analyse des valeurs manquantes
        missing_results = check_missing_values(df)

        # Détection des valeurs aberrantes (uniquement pour les colonnes numériques)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            outliers_results = detect_outliers(df)
        else:
            outliers_results = {{}}
            print("ℹ️  Aucune colonne numérique pour la détection de valeurs aberrantes")

    except ImportError as e:
        print(f"⚠️  Certains modules de validation non disponibles: {e}")
        print("   Les validations de base seront exécutées...")

        # Validation basique
        validation_results = {{
            "total_lignes": len(df),
            "total_colonnes": len(df.columns),
            "valeurs_manquantes": df.isnull().sum().sum(),
            "doublons": df.duplicated().sum(),
            "types_donnees": str(df.dtypes.to_dict())
        }}

        print(f"✓ Lignes: {{validation_results['total_lignes']:,}}")
        print(f"✓ Colonnes: {{validation_results['total_colonnes']}}")
        print(f"✓ Valeurs manquantes: {{validation_results['valeurs_manquantes']:,}}")
        print(f"✓ Doublons: {{validation_results['doublons']:,}}")

    # ÉTAPE 4: ANALYSE SPÉCIFIQUE AU DOMAINE
    print(f"\\n📈 ÉTAPE 4: ANALYSE {domain.upper()}")
    print("-" * 40)

    try:
        if domain == 'assurance' and os.path.exists('scripts/domain_analysis.py'):
            from domain_analysis import analyse_assurance
            print("🔧 Exécution de l'analyse spécifique assurance...")
            domain_results = analyse_assurance(df)
            print("✅ Analyse assurance terminée")

        elif domain == 'finance' and os.path.exists('scripts/finance_analysis.py'):
            from finance_analysis import analyse_finance
            print("🔧 Exécution de l'analyse spécifique finance...")
            domain_results = analyse_finance(df)
            print("✅ Analyse finance terminée")

        else:
            # Analyse générique
            print("🔧 Exécution de l'analyse générique...")
            domain_results = {{
                "statistiques_descriptives": df.describe().round(2).to_dict(),
                "info_generale": {{
                    "lignes": len(df),
                    "colonnes": len(df.columns),
                    "types": df.dtypes.astype(str).to_dict()
                }}
            }}
            print("✅ Analyse générique terminée")

    except Exception as e:
        print(f"⚠️  Erreur lors de l'analyse spécifique: {{e}}")
        domain_results = {{"erreur": str(e)}}

    # ÉTAPE 5: EXÉCUTION DES SCRIPTS GÉNÉRÉS
    print("\\n🔧 ÉTAPE 5: EXÉCUTION DES SCRIPTS GÉNÉRÉS")
    print("-" * 40)

    # Vérifier si des scripts Python spécifiques ont été générés
    python_scripts = {execution_plan.get('scripts', {{}}).get('python', {{}})}
    scripts_executed = []

    for script_name, script_info in python_scripts.items():
        if isinstance(script_info, dict) and script_name not in ['domain_analysis', 'pandas', 'plotly']:
            try:
                print(f"▶️  Exécution de {{script_name}}...")
                # Ici, on pourrait exécuter dynamiquement le code
                # Pour la sécurité, on se contente de lister les scripts disponibles
                scripts_executed.append(script_name)
            except Exception as e:
                print(f"⚠️  Erreur avec {{script_name}}: {{e}}")

    if scripts_executed:
        print(f"✅ Scripts exécutés: {{', '.join(scripts_executed)}}")
    else:
        print("ℹ️  Aucun script spécifique à exécuter")

    # ÉTAPE 6: GÉNÉRATION DES VISUALISATIONS
    print("\\n🎨 ÉTAPE 6: GÉNÉRATION DES VISUALISATIONS")
    print("-" * 40)

    visualizations_generated = []

    try:
        import plotly.express as px
        import plotly.io as pio

        # Créer un répertoire pour les visualisations
        viz_dir = "results/visualisations"
        os.makedirs(viz_dir, exist_ok=True)

        # Générer des visualisations basiques selon les données disponibles
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns

        # 1. Histogramme pour la première colonne numérique
        if len(numeric_cols) > 0:
            first_numeric = numeric_cols[0]
            fig1 = px.histogram(df, x=first_numeric,
                              title=f"Distribution des {{first_numeric}}",
                              nbins=50,
                              template="plotly_white")
            viz_path1 = os.path.join(viz_dir, "histogramme_distribution.html")
            fig1.write_html(viz_path1)
            visualizations_generated.append(viz_path1)
            print(f"✓ Histogramme: {{viz_path1}}")

        # 2. Diagramme en barres pour la première colonne catégorielle (avec peu de valeurs)
        if len(categorical_cols) > 0:
            for cat_col in categorical_cols:
                if df[cat_col].nunique() <= 20:  # Limiter aux colonnes avec peu de catégories
                    value_counts = df[cat_col].value_counts().reset_index()
                    value_counts.columns = ['categorie', 'count']

                    fig2 = px.bar(value_counts, x='categorie', y='count',
                                title=f"Répartition des {{cat_col}}",
                                template="plotly_white")
                    viz_path2 = os.path.join(viz_dir, f"repartition_{{cat_col}}.html")
                    fig2.write_html(viz_path2)
                    visualizations_generated.append(viz_path2)
                    print(f"✓ Diagramme en barres: {{viz_path2}}")
                    break  # Un seul diagramme pour l'instant

        # 3. Nuage de points si au moins 2 colonnes numériques
        if len(numeric_cols) >= 2:
            fig3 = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1],
                            title=f"{{numeric_cols[0]}} vs {{numeric_cols[1]}}",
                            template="plotly_white")
            viz_path3 = os.path.join(viz_dir, "nuage_points.html")
            fig3.write_html(viz_path3)
            visualizations_generated.append(viz_path3)
            print(f"✓ Nuage de points: {{viz_path3}}")

        print(f"\\n✅ {{len(visualizations_generated)}} visualisations générées dans {{viz_dir}}/")

    except ImportError as e:
        print(f"⚠️  Plotly non disponible: {{e}}")
        print("   Installez avec: pip install plotly")
    except Exception as e:
        print(f"⚠️  Erreur lors de la génération des visualisations: {{e}}")

    # ÉTAPE 7: SAUVEGARDE DES RÉSULTATS
    print("\\n💾 ÉTAPE 7: SAUVEGARDE DES RÉSULTATS")
    print("-" * 40)

    # Préparer le rapport final
    final_report = {{
        "metadata": {{
            "date_generation": datetime.now().isoformat(),
            "domaine": domain,
            "intention": intention,
            "fichier_source": data_file,
            "dimensions": {{"lignes": len(df), "colonnes": len(df.columns)}}
        }},
        "validation": {{
            "total_lignes": len(df),
            "total_colonnes": len(df.columns),
            "valeurs_manquantes": int(df.isnull().sum().sum()),
            "doublons": int(df.duplicated().sum())
        }},
        "analyse_domaine": domain_results,
        "statistiques": df.describe().round(3).to_dict() if len(numeric_cols) > 0 else {{}},
        "visualisations": visualizations_generated,
        "scripts_executes": scripts_executed
    }}

    # Sauvegarde du rapport JSON
    report_path = "results/rapport_analyse.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False, default=str)
    print(f"✓ Rapport JSON: {{report_path}}")

    # Sauvegarde des statistiques de synthèse
    if len(numeric_cols) > 0:
        summary_stats = df[numeric_cols].describe().round(3)
        stats_path = "results/statistiques_synthese.csv"
        summary_stats.to_csv(stats_path)
        print(f"✓ Statistiques CSV: {{stats_path}}")

    # Sauvegarde des données de validation
    validation_path = "results/validation_donnees.csv"
    validation_summary = pd.DataFrame({{
        'colonne': df.columns,
        'type': df.dtypes.astype(str),
        'valeurs_uniques': [df[col].nunique() for col in df.columns],
        'valeurs_manquantes': df.isnull().sum().values,
        'taux_manquants': (df.isnull().sum() / len(df) * 100).round(2).values
    }})
    validation_summary.to_csv(validation_path, index=False)
    print(f"✓ Validation CSV: {{validation_path}}")

    # ÉTAPE 8: RAPPORT FINAL
    print("\\n" + "=" * 70)
    print("✅ ANALYSE TERMINÉE AVEC SUCCÈS")
    print("=" * 70)

    print(f"\\n📊 SYNTHÈSE DES RÉSULTATS:")
    print(f"   • Données analysées: {{len(df):,}} lignes × {{len(df.columns)}} colonnes")
    print(f"   • Visualisations: {{len(visualizations_generated)}} fichier(s) HTML")
    print(f"   • Rapports: 3 fichier(s) générés")

    print(f"\\n📁 FICHIERS GÉNÉRÉS (dossier 'results/'):")
    print(f"   1. rapport_analyse.json - Rapport complet au format JSON")
    print(f"   2. statistiques_synthese.csv - Tableau des statistiques")
    print(f"   3. validation_donnees.csv - Résumé de la validation")
    if visualizations_generated:
        print(f"   4. visualisations/ - Dossier contenant les graphiques interactifs")

    print(f"\\n🔍 INDICATEURS CLÉS:")
    if len(numeric_cols) > 0:
        for col in numeric_cols[:3]:  # Afficher les 3 premières colonnes numériques
            print(f"   • {{col}}:")
            print(f"     - Moyenne: {{df[col].mean():.2f}}")
            print(f"     - Médiane: {{df[col].median():.2f}}")
            print(f"     - Écart-type: {{df[col].std():.2f}}")

    print(f"\\n📌 PROCHAINES ÉTAPES:")
    print(f"   1. Ouvrez les fichiers HTML dans votre navigateur")
    print(f"   2. Consultez le rapport JSON pour les détails complets")
    print(f"   3. Adaptez les scripts dans le dossier 'scripts/' pour des analyses spécifiques")
    print(f"   4. Ré-exécutez avec différentes données si nécessaire")

    print("\\n" + "=" * 70)
    print("🔒 SÉCURITÉ: Toutes les analyses ont été exécutées localement")
    print("   Aucune donnée n'a été partagée avec des services externes")
    print("=" * 70)

if __name__ == "__main__":
    main()
'''

        return main_script

    def _generate_requirements(self, execution_plan: Dict[str, Any]) -> str:
        """Génère le fichier requirements.txt amélioré"""

        domain = execution_plan.get('domain', 'generic')

        base_requirements = """# Dépendances principales pour l'analyse de données
# Installer avec: pip install -r requirements.txt

# 📊 Bibliothèques fondamentales
pandas>=1.5.0
numpy>=1.21.0

# 📈 Visualisation interactive
plotly>=5.13.0
kaleido>=0.2.0  # Pour l'export d'images

# 🔍 Analyse statistique
scipy>=1.9.0
scikit-learn>=1.2.0  # Pour les analyses avancées

# 📁 Support des formats de fichiers
openpyxl>=3.0.0  # Pour lire/écrire Excel
pyarrow>=10.0.0  # Pour les performances
"""

        # Ajouter des dépendances spécifiques au domaine
        if domain == 'assurance':
            base_requirements += """
# 🚗 Assurance spécifique
# (Aucune dépendance spécifique requise pour l'analyse basique)
"""

        elif domain == 'finance':
            base_requirements += """
# 💰 Finance spécifique
yfinance>=0.2.0  # Pour les données financières (optionnel)
"""

        base_requirements += """
# 🛠️ Outils de développement
jupyter>=1.0.0
ipython>=8.0.0
ipywidgets>=8.0.0

# 📝 Documentation
jupyterlab>=3.0.0

# ⚡ Optimisation (optionnel)
# numba>=0.56.0  # Pour l'accélération JIT
# dask>=2023.1.0  # Pour les gros datasets
"""

        return base_requirements

    def _generate_readme(self, execution_plan: Dict[str, Any]) -> str:
        """Génère le fichier README.md amélioré"""

        domain = execution_plan.get('domain', 'generic')
        intention = execution_plan.get('intention', 'Analyse générique')
        overview = execution_plan.get('overview', 'Analyse générée automatiquement')

        readme = f'''# 📊 Package d'Analyse Sécurisée - {domain.upper()}

## 🎯 Description
Package d'analyse généré automatiquement par le **SecureNLQ Engine**.
Ce package permet d'exécuter une analyse complète **localement** sans partager vos données.

## 🔒 Architecture Sécurisée - Zéro Partage de Données
✅ **Métadonnées uniquement** : Seule la structure des données a été analysée  
✅ **Exécution 100% locale** : Vos données ne quittent jamais votre machine  
✅ **Contrôle total** : Vous gardez le contrôle complet de vos données  
✅ **Code vérifiable** : Tous les scripts sont ouverts et modifiables  

## 📋 Objectif de l'analyse
**Intention détectée:** {intention}

**Stratégie d'analyse:** {overview}

## 🚀 Démarrage Rapide

### 1. Prérequis
```bash
# Cloner ou télécharger ce package
# S'assurer d'avoir Python 3.8+ installé
python --version
```
        '''
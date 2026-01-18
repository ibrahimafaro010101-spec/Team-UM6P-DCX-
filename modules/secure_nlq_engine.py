# modules/secure_nlq_engine.py - Version corrigée et simplifiée
import json
from typing import Dict, Any, List
from openai import OpenAI
import os
import pandas as pd
from datetime import datetime


class SecureNLQEngine:
    """
    Moteur NLQ sécurisé simplifié
    """

    def __init__(self, api_key: str, model: str = "gpt-4.1"):
        if not api_key:
            raise ValueError("Clé API OpenAI requise")

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.metadata_cache = {}  # Ajout de l'attribut manquant

    def load_metadata_from_file(self, file_path: str, sheet_name: str = None) -> Dict[str, Any]:
        """
        Charge les métadonnées à partir d'un fichier Excel ou CSV
        """
        try:
            if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                if sheet_name:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                else:
                    df = pd.read_excel(file_path, sheet_name=0)
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8')
            else:
                raise ValueError(f"Format non supporté: {file_path}")

            # Vérifier si c'est un dictionnaire de métadonnées
            if 'nom_colonne' in df.columns:
                column_name_col = 'nom_colonne'
            elif 'variable' in df.columns:
                column_name_col = 'variable'
            else:
                column_name_col = df.columns[0]

            # Construire la structure de métadonnées
            structure_columns = []
            for _, row in df.iterrows():
                col_info = {
                    'nom': str(row[column_name_col]).strip(),
                    'type_donnee': str(row.get('type', 'unknown')).lower() if 'type' in df.columns else 'unknown',
                    'description': str(row.get('description', '')).strip() if 'description' in df.columns else ''
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

        col_names = [col['nom'].lower() for col in columns]

        # Détection du domaine assurance
        insurance_keywords = ['prime', 'assure', 'contrat', 'sinistre', 'client', 'police', 'risque']
        if any(keyword in ' '.join(col_names) for keyword in insurance_keywords):
            context['domaine'] = 'assurance'

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

        return context

    def analyze_query_with_metadata(self,
                                    user_query: str,
                                    metadata: Dict[str, Any] = None,
                                    metadata_file: str = None) -> Dict[str, Any]:
        """
        Analyse une requête utilisateur avec les métadonnées
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
        prompt = self._build_secure_prompt(user_query, metadata)

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
                max_tokens=2000
            )

            # Essayer de parser la réponse
            result_text = response.choices[0].message.content

            try:
                analysis_result = json.loads(result_text)
            except json.JSONDecodeError:
                analysis_result = {
                    "intention": "Analyse générée",
                    "strategie_analyse": "Analyse basée sur les métadonnées",
                    "reponse_detaillee": result_text
                }

            return {
                "analysis": analysis_result,
                "security_status": "secure_metadata_only",
                "metadata_source": metadata.get('source_file', 'provided_directly')
            }

        except Exception as e:
            return {
                "error": str(e),
                "metadata_source": metadata.get('source_file', 'provided_directly')
            }

    def _build_secure_prompt(self, user_query: str, metadata: Dict[str, Any]) -> str:
        """Construit un prompt sécurisé basé sur les métadonnées"""

        structure_cols = metadata.get('structure_columns', [])

        prompt_parts = []
        prompt_parts.append("# ANALYSE SÉCURISÉE DE DONNÉES")
        prompt_parts.append("")

        # Métadonnées
        prompt_parts.append("##  MÉTADONNÉES DISPONIBLES")
        prompt_parts.append("### Structure des données:")

        if structure_cols:
            for col in structure_cols[:15]:  # Limiter à 15 colonnes
                col_desc = f"- {col['nom']}"
                if col.get('description'):
                    col_desc += f" : {col['description']}"
                if col.get('type_donnee'):
                    col_desc += f" ({col['type_donnee']})"
                prompt_parts.append(col_desc)
        else:
            prompt_parts.append("Aucune information de colonne disponible")

        prompt_parts.append("")

        # Informations générales
        gen_info = metadata.get('general_info', {})
        if gen_info:
            prompt_parts.append("### Informations techniques:")
            prompt_parts.append(f"- Nombre total de colonnes: {gen_info.get('nombre_colonnes', 'N/A')}")
            prompt_parts.append("")

        # Requête utilisateur
        prompt_parts.append(f'#  QUESTION UTILISATEUR:')
        prompt_parts.append(f'"{user_query}"')
        prompt_parts.append("")

        prompt_parts.append("""#  INSTRUCTIONS:
Analysez cette question en utilisant UNIQUEMENT les métadonnées fournies.
Proposez une méthodologie d'analyse, des indicateurs clés à calculer,
et des visualisations pertinentes.

Répondez en JSON avec cette structure:
{
  "intention": "Description de l'intention",
  "strategie_analyse": "Description de la stratégie",
  "indicateurs_cles": ["indicateur1", "indicateur2"],
  "visualisations_suggestees": [
    {
      "type": "type de graphique",
      "description": "description",
      "variables_impliquees": ["variable1", "variable2"]
    }
  ],
  "reponse_detaillee": "Réponse complète en français"
}
""")

        return "\n".join(prompt_parts)

    def _get_system_prompt(self) -> str:
        """Prompt système définissant le rôle"""
        return """Vous êtes un assistant expert en analyse de données sécurisée.

RÈGLES DE SÉCURITÉ:
- N'inventez JAMAIS de données réelles
- Utilisez UNIQUEMENT les noms de colonnes fournis dans les métadonnées
- Proposez des analyses réalisables avec les informations disponibles
- Adaptez vos recommandations au domaine identifié

Répondez toujours en français."""

    # Méthodes simplifiées pour réduire la taille du code
    def _generate_execution_plan(self, analysis_result: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Génère un plan d'exécution simplifié"""
        return {
            "overview": analysis_result.get("strategie_analyse", "Analyse générée"),
            "intention": analysis_result.get("intention", "Analyse"),
            "domain": metadata.get('business_context_hints', {}).get('domaine', 'inconnu'),
            "steps": ["1. Charger les données", "2. Valider", "3. Analyser", "4. Visualiser", "5. Exporter"],
            "outputs": ["rapport_analyse.json", "statistiques.csv"]
        }

    def _adapt_scripts_to_metadata(self, scripts: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Adapte les scripts générés aux métadonnées"""
        return {
            "sql": [],
            "python": {},
            "validation": []
        }

    def _generate_insurance_analysis_script(self, metadata: Dict[str, Any]) -> str:
        """Génère un script d'analyse pour le domaine assurance simplifié"""
        return '''"""
SCRIPT D'ANALYSE - DOMAINE ASSURANCE
Généré automatiquement
"""

import pandas as pd
import numpy as np

def analyse_assurance(df):
    """
    Fonction d'analyse spécifique au domaine assurance
    """
    print(" Analyse assurance démarrée")

    results = {}

    # Analyse des primes
    prime_cols = [col for col in df.columns if 'prime' in col.lower()]
    if prime_cols:
        for col in prime_cols[:2]:
            if pd.api.types.is_numeric_dtype(df[col]):
                print(f"Prime {col}: moyenne = {df[col].mean():.2f}")
                results[f'moyenne_{col}'] = df[col].mean()

    # Analyse des clients
    client_cols = [col for col in df.columns if 'client' in col.lower()]
    if client_cols:
        for col in client_cols[:2]:
            if df[col].nunique() < 20:
                print(f"Distribution {col}: {df[col].value_counts().head(3).to_dict()}")

    return results

if __name__ == "__main__":
    print("Script d'analyse assurance prêt.")
    print("Utilisation: analyse_assurance(df)")
'''

    def generate_sql_query(self, analysis_result: Dict[str, Any]) -> str:
        """Génère une requête SQL basée sur l'analyse"""
        intention = analysis_result.get("intention", "")
        indicateurs = analysis_result.get("indicateurs_cles", [])

        sql_template = f"""-- Requête SQL générée automatiquement
-- Intention: {intention}

SELECT 
    -- Sélectionnez les colonnes appropriées
    COUNT(*) as total_clients,
    AVG(prime) as prime_moyenne,
    -- Ajoutez d'autres indicateurs

FROM votre_table
WHERE 1=1
    -- Ajoutez des filtres selon le besoin
GROUP BY 
    -- Groupement selon l'analyse

ORDER BY prime_moyenne DESC;
"""
        return sql_template

    def validate_columns_exist(self, required_cols: List[str], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Vérifie si les colonnes requises existent dans les métadonnées"""
        structure_cols = metadata.get('structure_columns', [])
        available_cols = [col['nom'] for col in structure_cols]

        missing_cols = []
        available = []

        for col in required_cols:
            if col in available_cols:
                available.append(col)
            else:
                missing_cols.append(col)

        return {
            "available": available,
            "missing": missing_cols,
            "all_available": len(missing_cols) == 0
        }

# Classe simplifiée pour compatibilité
class NLPEngine:
    """Alias pour compatibilité"""

    def __init__(self, api_key: str):
        self.engine = SecureNLQEngine(api_key=api_key)

    def analyze(self, query: str, metadata=None, metadata_file=None):
        """Analyse une requête"""
        return self.engine.analyze_query_with_metadata(query, metadata, metadata_file)


# Classe pour les résultats
class QueryResult:
    """Classe pour les résultats de requête"""

    def __init__(self, success: bool, data: Dict[str, Any], message: str = ""):
        self.success = success
        self.data = data
        self.message = message

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Crée un QueryResult depuis un dictionnaire"""
        success = "error" not in data
        message = data.get("error", "") if not success else "Analyse réussie"
        return cls(success, data, message)

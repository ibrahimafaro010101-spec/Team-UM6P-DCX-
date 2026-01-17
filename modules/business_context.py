# modules/business_context.py
import json
from typing import Dict, Any


class BusinessContextProvider:
    """
    Fournit le contexte métier pour l'analyse
    Sans exposer de données spécifiques
    """

    # Templates de contexte par domaine
    CONTEXT_TEMPLATES = {
        "assurance_automobile": {
            "domaine": "assurance_automobile",
            "description": "Analyse de données d'assurance automobile avec focus sur la sinistralité, la tarification et la rétention client.",
            "concepts_cles": [
                "prime_assurance",
                "sinistralite",
                "risque_client",
                "fidelisation",
                "tarification"
            ],
            "indicateurs_typiques": [
                {"nom": "loss_ratio", "description": "Ratio sinistres/primes"},
                {"nom": "frequence_sinistres", "description": "Nombre de sinistres par contrat"},
                {"nom": "cout_moyen_sinistre", "description": "Coût moyen des sinistres"},
                {"nom": "taux_renouvellement", "description": "Pourcentage de contrats renouvelés"}
            ],
            "analyses_courantes": [
                "Analyse de la sinistralité par segment",
                "Segmentation des clients par risque",
                "Analyse de la rentabilité des contrats",
                "Prédiction des risques de résiliation"
            ],
            "visualisations_pertinentes": [
                {"type": "histogram", "usage": "Distribution des primes"},
                {"type": "scatter", "usage": "Corrélation âge/sinistres"},
                {"type": "bar", "usage": "Sinistralité par région"},
                {"type": "box", "usage": "Distribution des coûts de sinistres"}
            ],
            "requetes_sql_typiques": [
                "SELECT region, AVG(prime) as prime_moyenne, COUNT(*) as nb_contrats FROM contrats GROUP BY region",
                "SELECT type_vehicule, SUM(cout_sinistre) as total_sinistres, COUNT(DISTINCT client_id) as clients FROM sinistres GROUP BY type_vehicule",
                "SELECT EXTRACT(YEAR FROM date_sinistre) as annee, COUNT(*) as nb_sinistres FROM sinistres GROUP BY annee ORDER BY annee"
            ],
            "transformations_courantes": [
                {"action": "calculer_age", "colonne_base": "date_naissance"},
                {"action": "categoriser_risque", "colonne_base": "score_risque"},
                {"action": "normaliser_prime", "colonne_base": "prime_annuelle"}
            ]
        },

        "assurance_sante": {
            "domaine": "assurance_sante",
            "description": "Analyse de données d'assurance santé avec focus sur les dépenses médicales et la prévention.",
            "concepts_cles": [
                "remboursement",
                "prevention",
                "pathologie",
                "depense_medicale",
                "taux_remboursement"
            ],
            "indicateurs_typiques": [
                {"nom": "cout_moyen_consultation", "description": "Coût moyen des consultations"},
                {"nom": "taux_remboursement", "description": "Pourcentage des dépenses remboursées"},
                {"nom": "frequence_pathologie", "description": "Prévalence des pathologies"}
            ]
        },

        "banque_finance": {
            "domaine": "banque_finance",
            "description": "Analyse de données bancaires et financières avec focus sur le risque crédit et la rentabilité.",
            "concepts_cles": [
                "risque_credit",
                "profitabilite",
                "defaut_paiement",
                "scoring_client",
                "marge_interet"
            ]
        }
    }

    @classmethod
    def get_context(cls, domain: str = "assurance_automobile") -> Dict[str, Any]:
        """
        Retourne le contexte métier pour un domaine spécifique
        """
        context = cls.CONTEXT_TEMPLATES.get(domain, cls.CONTEXT_TEMPLATES["assurance_automobile"])

        # Ajouter des conseils génériques
        context["conseils_generiques"] = [
            "Toujours valider la qualité des données avant l'analyse",
            "Considérer les biais potentiels dans les données",
            "Documenter toutes les transformations appliquées",
            "Vérifier la cohérence des résultats avec le bon sens métier"
        ]

        return context

    @classmethod
    def infer_domain_from_columns(cls, columns: list) -> str:
        """
        Infère le domaine métier basé sur les noms de colonnes
        """
        column_names = [str(col).lower() for col in columns]

        # Détection assurance automobile
        auto_keywords = ['prime', 'assur', 'sinistr', 'vehicule', 'conducteur', 'permis']
        if any(any(keyword in col for keyword in auto_keywords) for col in column_names):
            return "assurance_automobile"

        # Détection assurance santé
        sante_keywords = ['sante', 'medical', 'hopital', 'consultation', 'medecin', 'pathologie']
        if any(any(keyword in col for keyword in sante_keywords) for col in column_names):
            return "assurance_sante"

        # Détection banque/finance
        finance_keywords = ['credit', 'pret', 'compte', 'banque', 'interet', 'solde']
        if any(any(keyword in col for keyword in finance_keywords) for col in column_names):
            return "banque_finance"

        return "assurance_automobile"  # Par défaut
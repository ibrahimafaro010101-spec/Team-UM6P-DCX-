# =====================================================
# indicators_config.py
# Insurance Automobile - Risk & Decision Indicators
# =====================================================

"""
Ce fichier contient les métadonnées des indicateurs utilisés par l'IA
pour l'analyse du risque, du comportement client et de la performance
financière en assurance automobile.

Objectif :
- Guider l'IA avec un contexte métier clair
- Garantir des analyses explicables et actionnables
- Servir de référence unique (single source of truth)
"""

INSURANCE_INDICATORS = {

    # =================================================
    # 1. Indicateurs de risque et de sinistralité
    # =================================================
    "risk_and_claims": {
        "description": "Indicateurs de risque et de sinistralité automobile",
        "priority": "high",
        "indicators": {

            "claim_frequency": {
                "label": "Fréquence de sinistre",
                "definition": "Nombre de sinistres rapporté à la durée d’exposition",
                "business_meaning": "Mesure directe du niveau de risque du véhicule assuré",
                "type": "quantitative",
                "direction_of_risk": "positive",
                "usage": ["risk_scoring", "pricing"]
            },

            "average_claim_cost": {
                "label": "Coût moyen de sinistre",
                "definition": "Coût total des sinistres divisé par leur nombre",
                "business_meaning": "Évalue la gravité financière des sinistres",
                "type": "monetary",
                "direction_of_risk": "positive",
                "usage": ["risk_scoring"]
            },

            "loss_ratio": {
                "label": "Sinistralité (Loss Ratio)",
                "definition": "Rapport entre charges de sinistres et primes encaissées",
                "business_meaning": "Indicateur clé de rentabilité technique",
                "type": "ratio",
                "direction_of_risk": "positive",
                "usage": ["profitability_analysis"]
            },

            "severity_rate": {
                "label": "Taux de gravité",
                "definition": "Coût moyen conditionnel des sinistres",
                "business_meaning": "Mesure l’impact financier potentiel d’un sinistre",
                "type": "quantitative",
                "direction_of_risk": "positive",
                "usage": ["risk_assessment"]
            },

            "client_risk_score": {
                "label": "Score de risque client",
                "definition": "Score agrégé issu de règles métier et d’IA",
                "business_meaning": "Synthèse du niveau de risque global du client",
                "type": "score",
                "direction_of_risk": "positive",
                "usage": ["decision_support"]
            }
        }
    },

    # =================================================
    # 2. Indicateurs de comportement client
    # =================================================
    "client_behavior": {
        "description": "Indicateurs de comportement et de stabilité du client",
        "priority": "high",
        "indicators": {

            "payment_delay_days": {
                "label": "Retard de paiement (jours)",
                "definition": "Nombre de jours de retard par rapport à l’échéance",
                "business_meaning": "Signal précoce de risque financier et de résiliation",
                "type": "quantitative",
                "direction_of_risk": "positive",
                "usage": ["lapse_prediction"]
            },

            "unpaid_count": {
                "label": "Nombre d’impayés",
                "definition": "Nombre total de factures non réglées",
                "business_meaning": "Mesure la fragilité financière du client",
                "type": "count",
                "direction_of_risk": "positive",
                "usage": ["credit_risk"]
            },

            "contract_tenure_days": {
                "label": "Ancienneté du contrat",
                "definition": "Durée écoulée depuis la date de souscription",
                "business_meaning": "Proxy de fidélité et de stabilité client",
                "type": "quantitative",
                "direction_of_risk": "negative",
                "usage": ["loyalty_analysis"]
            },

            "renewal_count": {
                "label": "Nombre de renouvellements",
                "definition": "Nombre de renouvellements successifs du contrat",
                "business_meaning": "Indicateur fort de fidélisation",
                "type": "count",
                "direction_of_risk": "negative",
                "usage": ["retention_analysis"]
            },

            "lapse_rate": {
                "label": "Taux de résiliation",
                "definition": "Probabilité estimée de résiliation du contrat",
                "business_meaning": "Mesure le risque de sortie du portefeuille",
                "type": "probability",
                "direction_of_risk": "positive",
                "usage": ["churn_prediction"]
            }
        }
    },

    # =================================================
    # 3. Indicateurs financiers
    # =================================================
    "financial_indicators": {
        "description": "Indicateurs financiers et de performance économique",
        "priority": "high",
        "indicators": {

            "annual_premium": {
                "label": "Prime annuelle",
                "definition": "Montant annuel payé par l’assuré",
                "business_meaning": "Source principale de revenu pour l’assureur",
                "type": "monetary",
                "direction_of_risk": "neutral",
                "usage": ["revenue_analysis"]
            },

            "client_profitability": {
                "label": "Rentabilité client",
                "definition": "Prime encaissée moins coût attendu du risque",
                "business_meaning": "Évalue la valeur économique du client",
                "type": "monetary",
                "direction_of_risk": "negative",
                "usage": ["portfolio_optimization"]
            },

            "technical_margin": {
                "label": "Marge technique",
                "definition": "Prime nette moins charges de sinistres",
                "business_meaning": "Indicateur clé de performance technique",
                "type": "monetary",
                "direction_of_risk": "negative",
                "usage": ["performance_monitoring"]
            },

            "customer_lifetime_value": {
                "label": "Valeur vie client (CLV)",
                "definition": "Valeur actualisée des flux futurs attendus",
                "business_meaning": "Vision long terme de la relation client",
                "type": "monetary",
                "direction_of_risk": "negative",
                "usage": ["strategic_decision"]
            }
        }
    },

    # =================================================
    # 4. Indicateurs de fraude potentielle
    # =================================================
    "fraud_indicators": {
        "description": "Indicateurs de suspicion de fraude",
        "priority": "medium",
        "indicators": {

            "temporal_claim_clustering": {
                "label": "Sinistres rapprochés dans le temps",
                "definition": "Multiples sinistres sur une courte période",
                "business_meaning": "Signal potentiel de fraude ou de comportement anormal",
                "type": "binary_flag",
                "direction_of_risk": "positive",
                "usage": ["fraud_detection"]
            },

            "early_claim_declaration": {
                "label": "Déclaration rapide après souscription",
                "definition": "Sinistre déclaré peu après la souscription",
                "business_meaning": "Comportement suspect nécessitant investigation",
                "type": "binary_flag",
                "direction_of_risk": "positive",
                "usage": ["fraud_detection"]
            },

            "abnormally_high_amount": {
                "label": "Montant anormalement élevé",
                "definition": "Sinistre dépassant un seuil statistique",
                "business_meaning": "Anomalie financière potentielle",
                "type": "outlier_flag",
                "direction_of_risk": "positive",
                "usage": ["fraud_detection"]
            },

            "repetitive_damage_type": {
                "label": "Répétition du même type de dommage",
                "definition": "Sinistres similaires répétés",
                "business_meaning": "Pattern suspect de déclaration",
                "type": "pattern_flag",
                "direction_of_risk": "positive",
                "usage": ["fraud_detection"]
            }
        }
    }


}



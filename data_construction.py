# ============================================================
# indicators_config.py
# Référentiel métier – Assurance Automobile (Hackathon DXC)
# ============================================================
# Rôle :
# - Décrire TOUS les indicateurs utilisés par l’IA
# - Distinguer observables / proxies / latents (IA)
# - Servir de base au moteur NLQ, scoring et insights
# ============================================================

INSURANCE_INDICATORS = {

    # ========================================================
    # 1. INDICATEURS DE RISQUE & SINISTRALITÉ
    # ========================================================
    "risk_and_claims": {
        "label": "Risque et sinistralité",
        "description": "Mesure de l’exposition au risque et du coût attendu des sinistres",
        "indicators": {

            "claim_frequency": {
                "label": "Fréquence de sinistre",
                "type": "latent",
                "unit": "sinistres / an",
                "definition": "Nombre moyen de sinistres par contrat",
                "source": "IA (modèle prédictif)",
                "usage": "Évaluation du risque, tarification"
            },

            "average_claim_cost": {
                "label": "Coût moyen de sinistre",
                "type": "latent",
                "unit": "MAD",
                "definition": "Montant moyen des sinistres déclarés",
                "source": "IA / Données sinistres futures",
                "usage": "Calcul du loss ratio"
            },

            "loss_ratio": {
                "label": "Sinistralité (Loss Ratio)",
                "type": "latent",
                "unit": "%",
                "definition": "Sinistres / Primes",
                "source": "IA",
                "usage": "Rentabilité technique"
            },

            "severity_rate": {
                "label": "Taux de gravité",
                "type": "latent",
                "unit": "%",
                "definition": "Part des sinistres graves",
                "source": "IA",
                "usage": "Détection des profils à risque élevé"
            },

            "client_risk_score": {
                "label": "Score de risque client",
                "type": "score",
                "unit": "0–1",
                "definition": "Score global de risque du client",
                "source": "IA (RandomForest / Logit)",
                "usage": "Décision métier, priorisation"
            }
        }
    },

    # ========================================================
    # 2. INDICATEURS DE COMPORTEMENT CLIENT
    # ========================================================
    "client_behavior": {
        "label": "Comportement client",
        "description": "Analyse de la fidélité, du paiement et du risque de départ",
        "indicators": {

            "payment_delay_days": {
                "label": "Retard de paiement",
                "type": "latent",
                "unit": "jours",
                "definition": "Durée moyenne de retard de paiement",
                "source": "Données financières futures",
                "usage": "Risque de résiliation"
            },

            "unpaid_count": {
                "label": "Nombre d’impayés",
                "type": "latent",
                "unit": "comptage",
                "definition": "Nombre d’échéances non payées",
                "source": "Système de paiement",
                "usage": "Scoring client"
            },

            "contract_tenure_days": {
                "label": "Ancienneté du contrat",
                "type": "observable",
                "unit": "jours",
                "definition": "Durée depuis la souscription",
                "source": "datedeb",
                "usage": "Fidélité"
            },

            "renewal_count": {
                "label": "Nombre de renouvellements",
                "type": "proxy",
                "unit": "comptage",
                "definition": "Nombre d’avenants successifs",
                "source": "libop",
                "usage": "Fidélisation"
            },

            "lapse_rate": {
                "label": "Taux de résiliation",
                "type": "proxy",
                "unit": "%",
                "definition": "Probabilité de non-renouvellement",
                "source": "renewed",
                "usage": "Prévention churn"
            }
        }
    },

    # ========================================================
    # 3. INDICATEURS FINANCIERS
    # ========================================================
    "financial_indicators": {
        "label": "Indicateurs financiers",
        "description": "Analyse de la valeur et de la rentabilité client",
        "indicators": {

            "annual_premium": {
                "label": "Prime annuelle",
                "type": "observable",
                "unit": "MAD",
                "definition": "Prime normalisée sur 12 mois",
                "source": "prime_par_jour",
                "usage": "Comparabilité des contrats"
            },

            "net_premium": {
                "label": "Prime nette",
                "type": "proxy",
                "unit": "MAD",
                "definition": "Prime hors frais et taxes",
                "source": "Prime",
                "usage": "Rentabilité"
            },

            "client_profitability": {
                "label": "Rentabilité client",
                "type": "latent",
                "unit": "MAD",
                "definition": "Prime – coût attendu",
                "source": "IA",
                "usage": "Décision commerciale"
            },

            "technical_margin": {
                "label": "Marge technique",
                "type": "latent",
                "unit": "MAD",
                "definition": "Résultat technique du contrat",
                "source": "IA",
                "usage": "Pilotage portefeuille"
            },

            "customer_lifetime_value": {
                "label": "Valeur vie client (CLV)",
                "type": "latent",
                "unit": "MAD",
                "definition": "Valeur actualisée du client",
                "source": "IA",
                "usage": "Stratégie long terme"
            }
        }
    },

    # ========================================================
    # 4. INDICATEURS DE FRAUDE
    # ========================================================
    "fraud_indicators": {
        "label": "Détection de fraude",
        "description": "Identification des comportements anormaux",
        "indicators": {

            "temporal_claim_clustering": {
                "label": "Sinistres rapprochés",
                "type": "latent",
                "unit": "score",
                "definition": "Sinistres concentrés dans le temps",
                "source": "IA",
                "usage": "Fraude potentielle"
            },

            "early_claim_declaration": {
                "label": "Déclaration rapide après souscription",
                "type": "latent",
                "unit": "binaire",
                "definition": "Sinistre peu après la souscription",
                "source": "IA",
                "usage": "Suspicion fraude"
            },

            "abnormally_high_amount": {
                "label": "Montant anormalement élevé",
                "type": "latent",
                "unit": "score",
                "definition": "Montant hors distribution normale",
                "source": "IA (outliers)",
                "usage": "Audit sinistre"
            },

            "repeated_claim_pattern": {
                "label": "Répétition même type de dommage",
                "type": "latent",
                "unit": "score",
                "definition": "Patterns répétitifs suspects",
                "source": "IA",
                "usage": "Détection comportementale"
            }
        }
    }
}

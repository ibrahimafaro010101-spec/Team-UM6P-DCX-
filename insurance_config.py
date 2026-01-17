# ============================================================
# insurance_config.py
# Configuration experte pour le traitement des données d'assurance
# ============================================================

INSURANCE_DOMAIN_CONFIG = {
    # Catégories de risque
    'RISK_CATEGORIES': {
        'Faible': {
            'score_range': (0, 30),
            'color': '#2ECC71',
            'actions': ['Fidélisation', 'Cross-selling', 'Recommandation']
        },
        'Moyen': {
            'score_range': (31, 60),
            'color': '#F39C12',
            'actions': ['Surveillance', 'Optimisation prime', 'Éducation']
        },
        'Élevé': {
            'score_range': (61, 80),
            'color': '#E74C3C',
            'actions': ['Réévaluation', 'Augmentation prime', 'Limitation couverture']
        },
        'Très élevé': {
            'score_range': (81, 100),
            'color': '#8B0000',
            'actions': ['Résiliation', 'Transfert réassurance', 'Exclusion']
        }
    },

    # Brackets de prime (MAD)
    'PRIME_BRACKETS': {
        'Très basse': (0, 1000),
        'Basse': (1001, 3000),
        'Moyenne': (3001, 7000),
        'Haute': (7001, 15000),
        'Très haute': (15001, float('inf'))
    },

    # Groupes d'âge pour l'assurance
    'AGE_GROUPS': {
        '<25': {'risk_factor': 1.8, 'description': 'Jeune conducteur'},
        '25-35': {'risk_factor': 1.3, 'description': 'Jeune adulte'},
        '35-45': {'risk_factor': 1.0, 'description': 'Adulte'},
        '45-55': {'risk_factor': 0.9, 'description': 'Adulte mature'},
        '55-65': {'risk_factor': 1.1, 'description': 'Senior'},
        '>65': {'risk_factor': 1.5, 'description': 'Âge avancé'}
    },

    # Catégories de véhicules
    'VEHICLE_CATEGORIES': {
        'Citadine': {
            'risk_factor': 0.9,
            'prime_multiplier': 1.0,
            'examples': ['Clio', '208', 'C3', 'Fiesta']
        },
        'Berline': {
            'risk_factor': 1.1,
            'prime_multiplier': 1.2,
            'examples': ['308', 'C5', 'Passat', 'C-Class']
        },
        'SUV': {
            'risk_factor': 1.3,
            'prime_multiplier': 1.5,
            'examples': ['3008', 'Tiguan', 'Q5', 'X3']
        },
        'Utilitaire': {
            'risk_factor': 1.4,
            'prime_multiplier': 1.3,
            'examples': ['Kangoo', 'Partner', 'Transit']
        },
        'Sportive': {
            'risk_factor': 1.8,
            'prime_multiplier': 2.0,
            'examples': ['911', 'R8', 'AMG', 'M3']
        },
        'Luxe': {
            'risk_factor': 1.6,
            'prime_multiplier': 2.5,
            'examples': ['S-Class', '7 Series', 'A8', 'Phantom']
        }
    },

    # Types de couverture
    'COVERAGE_TYPES': {
        'Tiers': {
            'coverage': 'Responsabilité civile uniquement',
            'prime_factor': 1.0,
            'risk_profile': 'Basique'
        },
        'Tiers étendu': {
            'coverage': 'RC + Incendie, Vol, Bris de glace',
            'prime_factor': 1.5,
            'risk_profile': 'Standard'
        },
        'Tous risques': {
            'coverage': 'Couverture complète avec franchise',
            'prime_factor': 2.0,
            'risk_profile': 'Premium'
        }
    },

    # Mapping des marques vers catégories
    'BRAND_CATEGORIES': {
        # Citadines
        'renault': 'Citadine',
        'peugeot': 'Citadine',
        'citroen': 'Citadine',
        'fiat': 'Citadine',
        'toyota': 'Citadine',
        'hyundai': 'Citadine',
        'kia': 'Citadine',
        'dacia': 'Citadine',

        # Berlines
        'bmw': 'Berline',
        'mercedes': 'Berline',
        'audi': 'Berline',
        'volkswagen': 'Berline',
        'ford': 'Berline',
        'opel': 'Berline',
        'skoda': 'Berline',
        'seat': 'Berline',

        # SUV
        'land rover': 'SUV',
        'jeep': 'SUV',
        'porsche': 'SUV',
        'volvo': 'SUV',
        'mazda': 'SUV',
        'nissan': 'SUV',
        'mitsubishi': 'SUV',

        # Sportives
        'ferrari': 'Sportive',
        'lamborghini': 'Sportive',
        'mclaren': 'Sportive',
        'maserati': 'Sportive',
        'aston martin': 'Sportive',

        # Luxe
        'bentley': 'Luxe',
        'rolls royce': 'Luxe',
        'tesla': 'Luxe'
    },

    # Facteurs de risque par région (exemple Maroc)
    'REGION_RISK_FACTORS': {
        'Casablanca': 1.5,
        'Rabat': 1.3,
        'Marrakech': 1.4,
        'Fès': 1.2,
        'Tanger': 1.3,
        'Agadir': 1.1,
        'Meknès': 1.2,
        'Oujda': 1.1,
        'Kenitra': 1.2,
        'Tétouan': 1.1
    },

    # Saisons et risques associés
    'SEASONAL_RISK_FACTORS': {
        'Hiver': {'months': [12, 1, 2], 'risk_factor': 1.4, 'reasons': ['Verglas', 'Pluie', 'Visibilité réduite']},
        'Printemps': {'months': [3, 4, 5], 'risk_factor': 1.1, 'reasons': ['Trafic touristique']},
        'Été': {'months': [6, 7, 8], 'risk_factor': 1.3, 'reasons': ['Trafic dense', 'Conducteurs fatigués']},
        'Automne': {'months': [9, 10, 11], 'risk_factor': 1.2, 'reasons': ['Feuilles mortes', 'Pluie']}
    },

    # Seuils métier
    'BUSINESS_THRESHOLDS': {
        'prime_min': 500,  # MAD
        'prime_max': 50000,  # MAD
        'age_min': 18,
        'age_max': 85,
        'vehicle_age_max': 30,  # ans
        'claim_frequency_high': 3,  # sinistres/an
        'claim_amount_high': 50000  # MAD
    }
}
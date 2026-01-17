# modules/execution_engine.py
import pandas as pd
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class LocalExecutionEngine:
    """
    Moteur d'exécution local pour les scripts générés
    """

    def __init__(self, working_dir: str = "."):
        self.working_dir = Path(working_dir)
        self.results = {}

    def execute_analysis_package(self, package_dir: str, data_path: str) -> Dict[str, Any]:
        """
        Exécute un package d'analyse complet
        """
        package_path = Path(package_dir)

        # Vérifier les prérequis
        self._check_prerequisites(package_path)

        # Installer les dépendances
        self._install_dependencies(package_path)

        # Mettre à jour le chemin des données dans main.py
        self._update_data_path(package_path / "main.py", data_path)

        # Exécuter l'analyse
        execution_result = self._run_analysis(package_path)

        # Collecter les résultats
        results = self._collect_results(package_path)

        return {
            "execution_status": execution_result,
            "results": results,
            "output_files": list(self._find_output_files(package_path))
        }

    def _check_prerequisites(self, package_path: Path):
        """Vérifie les prérequis"""
        required_files = ["main.py", "requirements.txt"]

        for file in required_files:
            if not (package_path / file).exists():
                raise FileNotFoundError(f"Fichier requis manquant: {file}")

    def _install_dependencies(self, package_path: Path):
        """Installe les dépendances Python"""
        requirements_file = package_path / "requirements.txt"

        if requirements_file.exists():
            print(f"Installation des dépendances depuis {requirements_file}...")

            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install",
                    "-r", str(requirements_file)
                ], check=True)
                print("✓ Dépendances installées avec succès")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Erreur lors de l'installation des dépendances: {e}")
                print("Vous devrez peut-être installer manuellement les packages")

    def _update_data_path(self, main_script: Path, data_path: str):
        """Met à jour le chemin des données dans le script principal"""
        if not main_script.exists():
            return

        # Lire le contenu
        with open(main_script, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remplacer le chemin des données
        new_content = content.replace(
            'DATA_PATH = "votre_fichier_donnees.csv"',
            f'DATA_PATH = "{data_path}"'
        )

        # Sauvegarder
        with open(main_script, 'w', encoding='utf-8') as f:
            f.write(new_content)

    def _run_analysis(self, package_path: Path) -> Dict[str, Any]:
        """Exécute l'analyse principale"""
        main_script = package_path / "main.py"

        try:
            print(f"Exécution de l'analyse: {main_script}")

            # Exécuter le script
            result = subprocess.run(
                [sys.executable, str(main_script)],
                capture_output=True,
                text=True,
                cwd=str(package_path)
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _collect_results(self, package_path: Path) -> Dict[str, Any]:
        """Collecte les résultats de l'analyse"""
        results = {}

        # Chercher les fichiers de résultats
        result_patterns = ["*.json", "*.csv", "*.html"]

        for pattern in result_patterns:
            for file in package_path.glob(pattern):
                if file.name not in ["config.json", "requirements.txt"]:
                    # Essayer de charger les fichiers JSON
                    if file.suffix == ".json":
                        try:
                            with open(file, 'r', encoding='utf-8') as f:
                                results[file.name] = json.load(f)
                        except:
                            results[file.name] = str(file)
                    else:
                        results[file.name] = str(file)

        return results

    def _find_output_files(self, package_path: Path) -> list:
        """Trouve tous les fichiers de sortie"""
        output_files = []

        for file in package_path.glob("*"):
            if file.is_file() and file.suffix in [".json", ".csv", ".html", ".png", ".pdf"]:
                output_files.append(str(file.name))

        return output_files

    def generate_execution_report(self, execution_result: Dict[str, Any]) -> str:
        """Génère un rapport d'exécution"""

        report = f"""# Rapport d'Exécution

## 📊 Statut d'Exécution
{'✅ Succès' if execution_result.get('execution_status', {}).get('success') else '❌ Échec'}

## 📁 Fichiers de Sortie
"""

        output_files = execution_result.get("output_files", [])
        for file in output_files:
            report += f"- {file}\n"

        if output_files:
            report += f"\nTotal: {len(output_files)} fichiers générés\n"

        # Ajouter les résultats JSON
        results = execution_result.get("results", {})
        if results:
            report += "\n## 📈 Résultats d'Analyse\n"

            for file_name, content in results.items():
                if isinstance(content, dict):
                    # C'est un fichier JSON chargé
                    report += f"\n### {file_name}\n"

                    # Ajouter quelques métriques clés
                    if 'metadata' in content:
                        metadata = content['metadata']
                        report += f"- Lignes analysées: {metadata.get('lignes', 'N/A')}\n"
                        report += f"- Colonnes analysées: {metadata.get('colonnes', 'N/A')}\n"

        return report
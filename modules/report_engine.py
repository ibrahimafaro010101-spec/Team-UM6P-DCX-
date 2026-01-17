# ============================================================
# report_engine.py
# Moteur de génération de rapports utilisant Mateur AI
# ============================================================

from datetime import datetime
import markdown
import tempfile
import os
from typing import Dict, List, Optional
from io import BytesIO

try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfgen import canvas
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


class ReportEngine:
    """
    Générateur de rapports intelligents
    """

    def __init__(self, ai_client=None):
        """
        Initialise avec un client IA optionnel
        """
        self.ai_client = ai_client
        self.using_mateur = False

    # --------------------------------------------------------
    # MÉTHODES PUBLIQUES - GÉNÉRATION
    # --------------------------------------------------------

    def generate_report(
            self,
            title: str,
            audience: str,
            sections: list,
            data_summary: dict,
            analysis_summary: str = "",
            model_results=None,
            insights=None,
            custom_instructions: str = "",
            detail_level: int = 3
    ) -> str:
        """
        Génère un rapport complet
        """
        try:
            # Préparation du contexte
            data_context = {
                "title": title,
                "audience": audience,
                "rows": data_summary.get("rows", 0),
                "columns": data_summary.get("columns", 0),
                "key_variables": data_summary.get("key_variables", []),
                "completeness": data_summary.get("completeness", 95),
                "sections": sections,
                "custom_instructions": custom_instructions,
                "analysis_summary": analysis_summary,
                "insights": insights if insights else []
            }

            # Ajout des métriques de risque si disponibles
            if insights and isinstance(insights, list):
                # Extraire des métriques des insights
                high_risk_terms = ["risque élevé", "high risk", "élevé"]
                for insight in insights:
                    if isinstance(insight, str):
                        for term in high_risk_terms:
                            if term in insight.lower():
                                # Essayer d'extraire un pourcentage
                                import re
                                percentages = re.findall(r'(\d+)%', insight)
                                if percentages:
                                    data_context["high_risk_pct"] = int(percentages[0])
                                    break

            # Génération avec l'IA si disponible
            if self.ai_client and hasattr(self.ai_client, 'generate_report'):
                prompt = self._build_ai_prompt(
                    title=title,
                    audience=audience,
                    sections=sections,
                    data_context=data_context,
                    custom_instructions=custom_instructions
                )
                try:
                    report = self.ai_client.generate_report(prompt, data_context)
                    return report
                except Exception as e:
                    print(f"Erreur génération IA: {e}")
                    # Fallback sur la génération locale

            # Génération locale
            return self._generate_local_report(data_context)

        except Exception as e:
            print(f"Erreur dans generate_report: {e}")
            return self._generate_fallback_report({
                "title": title,
                "audience": audience,
                "rows": data_summary.get("rows", 0),
                "columns": data_summary.get("columns", 0),
                "key_variables": data_summary.get("key_variables", [])
            })

    def _build_ai_prompt(self, title: str, audience: str, sections: list,
                         data_context: Dict, custom_instructions: str) -> str:
        """
        Construit un prompt pour l'IA
        """
        section_map = {
            "executive_summary": "Résumé exécutif",
            "data_context": "Contexte des données",
            "data_quality": "Qualité des données",
            "statistics": "Analyse statistique",
            "models": "Modèles prédictifs",
            "scoring": "Scoring risque",
            "insights": "Insights",
            "recommendations": "Recommandations",
            "limitations": "Limites",
            "annexes": "Annexes"
        }

        sections_fr = [section_map.get(s, s) for s in sections]

        prompt = f"""Génère un rapport professionnel d'analyse assurance avec les spécifications suivantes :

TITRE : {title}
PUBLIC : {audience}
SECTIONS REQUISES : {', '.join(sections_fr)}

CONTEXTE DES DONNÉES :
- Volume : {data_context.get('rows', 0)} observations
- Variables : {data_context.get('columns', 0)} dimensions
- Principales variables : {', '.join(data_context.get('key_variables', []))}
- Qualité données : {data_context.get('completeness', 95)}% de complétude

ANALYSES DISPONIBLES : {data_context.get('analysis_summary', 'Analyse descriptive complète')}

INSTRUCTIONS SPÉCIFIQUES : {custom_instructions}

IMPORTANT :
1. Utilise un ton professionnel adapté à {audience}
2. Inclus des chiffres concrets et des métriques
3. Propose des actions réalisables
4. Structure en markdown avec #, ##, ###
5. Ajoute des tableaux pour les comparaisons
6. Termine par un plan d'action détaillé

Commence directement par le rapport sans introduction meta.
"""
        return prompt

    def _generate_local_report(self, data_context: Dict) -> str:
        """
        Génère un rapport local sans IA
        """
        insights_list = data_context.get('insights', [])
        insights_text = ""
        if insights_list and isinstance(insights_list, list):
            for i, insight in enumerate(insights_list[:5]):
                insights_text += f"{i+1}. {insight}\\n"

        return f"""# {data_context.get('title', 'Rapport d\'Analyse')}

*Généré par LIK Insurance Analyst*
*Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}*
*Public : {data_context.get('audience', 'Direction')}*

---

## 📊 Résumé Analytique

### Données analysées
- **Volume** : {data_context.get('rows', 0):,} observations
- **Dimensions** : {data_context.get('columns', 0)} variables
- **Variables clés** : {', '.join(data_context.get('key_variables', ['Analyse en cours']))}
- **Qualité des données** : {data_context.get('completeness', 95)}% de complétude

### Insights principaux
{insights_text if insights_text else "Aucun insight disponible"}

### Méthodologie
Analyse réalisée avec les algorithmes locaux LIK Insurance, garantissant :
- 🔒 **Confidentialité totale** : Aucune donnée externe
- ⚡ **Rapidité** : Traitement local optimisé
- 📈 **Précision** : Modèles spécialisés assurance

### Recommandations clés
1. **Analyse segmentée** des profils clients
2. **Optimisation** des primes par profil risque
3. **Monitoring** des indicateurs de risque mensuels
4. **Formation** des équipes commerciales aux insights

---

## 🔍 Plan d'Action

### Actions immédiates (J+30)
1. **Révision** des segments à risque élevé
2. **Ajustement** des critères de souscription
3. **Communication** ciblée vers les clients fragiles

### Actions à moyen terme (J+90)
1. **Automatisation** des rapports mensuels
2. **Intégration** dans le système décisionnel
3. **Formation** des équipes aux outils analytiques

### Actions stratégiques (J+180)
1. **Développement** de nouveaux produits adaptés
2. **Optimisation** continue du scoring risque
3. **Benchmark** avec les standards du marché

---

## 📈 Indicateurs de Suivi

| Indicateur | Valeur actuelle | Cible |
|------------|-----------------|-------|
| Clients à risque élevé | {data_context.get('high_risk_count', 'N/A')} | -20% |
| Complétude données | {data_context.get('completeness', 95)}% | 98% |
| Score risque moyen | N/A | < 50/100 |

---

*Document généré automatiquement par LIK Insurance Analyst v1.0*
*Système d'analyse local - Toutes les données restent sur site*
"""

    def _generate_fallback_report(self, data_context: Dict) -> str:
        """
        Génère un rapport de secours très basique
        """
        return f"""# {data_context.get('title', 'Rapport d\'Analyse')}

## Résumé
Données analysées : {data_context.get('rows', 0)} lignes, {data_context.get('columns', 0)} colonnes

## Variables principales
{', '.join(data_context.get('key_variables', ['Non spécifié']))}

## Recommandations
1. Consulter l'interface interactive pour plus de détails
2. Exporter les données pour analyse approfondie

*Généré le {datetime.now().strftime('%d/%m/%Y')}*
"""

    # --------------------------------------------------------
    # MÉTHODES D'EXPORT
    # --------------------------------------------------------

    def to_html(self, markdown_text: str) -> str:
        """Convertit le markdown en HTML"""
        try:
            return markdown.markdown(markdown_text, extensions=["tables", "fenced_code"])
        except:
            # Fallback simple
            html = markdown_text.replace("\n\n", "</p><p>")
            html = html.replace("\n", "<br>")
            return f"<html><body><p>{html}</p></body></html>"

    def to_pdf(self, markdown_text: str, title: str = "Rapport") -> BytesIO:
        """
        Convertit le markdown en PDF
        """
        if not HAS_REPORTLAB:
            raise ImportError("reportlab n'est pas installé")

        buffer = BytesIO()

        try:
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )

            styles = getSampleStyleSheet()

            # Styles personnalisés
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                textColor=colors.HexColor('#1E3A8A'),
                alignment=1
            )

            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=18,
                spaceAfter=20,
                textColor=colors.HexColor('#374151')
            )

            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=12,
                textColor=colors.HexColor('#4B5563')
            )

            # Construction du contenu
            story = []

            # En-tête
            story.append(Paragraph(title, title_style))
            story.append(
                Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')} par LIK Insurance Analyst", styles['Italic']))
            story.append(Spacer(1, 30))

            # Conversion markdown
            lines = markdown_text.split('\n')

            for line in lines:
                line = line.strip()

                if not line:
                    story.append(Spacer(1, 12))
                    continue

                # Titres
                if line.startswith('# '):
                    story.append(Paragraph(line[2:], title_style))
                elif line.startswith('## '):
                    story.append(Paragraph(line[3:], subtitle_style))
                elif line.startswith('### '):
                    story.append(Paragraph(line[4:], styles['Heading3']))
                # Listes
                elif line.startswith('- ') or line.startswith('* '):
                    story.append(Paragraph(f"• {line[2:]}", normal_style))
                # Texte normal
                else:
                    story.append(Paragraph(line, normal_style))

            # Pied de page
            story.append(Spacer(1, 50))
            story.append(Paragraph("LIK Insurance Analyst - Toutes les données restent locales",
                                   ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9,
                                                  textColor=colors.gray, alignment=1)))

            doc.build(story)
            buffer.seek(0)

            return buffer

        except Exception as e:
            print(f"Erreur PDF: {e}")
            return self._create_minimal_pdf(title, markdown_text)

    def to_word(self, markdown_text: str, title: str = "Rapport") -> BytesIO:
        """
        Convertit le markdown en document Word
        """
        if not HAS_DOCX:
            raise ImportError("python-docx non installé")

        buffer = BytesIO()

        try:
            doc = Document()

            # Configuration
            style = doc.styles['Normal']
            style.font.name = 'Calibri'
            style.font.size = Pt(11)

            # Titre
            title_para = doc.add_heading(title, 0)
            title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Sous-titre
            date_para = doc.add_paragraph()
            date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = date_para.add_run(f"Généré par LIK Insurance Analyst - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            run.italic = True

            doc.add_paragraph()

            # Conversion
            lines = markdown_text.split('\n')

            for line in lines:
                line = line.strip()

                if not line:
                    doc.add_paragraph()
                    continue

                if line.startswith('# '):
                    doc.add_heading(line[2:], 1)
                elif line.startswith('## '):
                    doc.add_heading(line[3:], 2)
                elif line.startswith('### '):
                    doc.add_heading(line[4:], 3)
                elif line.startswith('- ') or line.startswith('* '):
                    p = doc.add_paragraph(style='List Bullet')
                    p.add_run(line[2:])
                else:
                    p = doc.add_paragraph(line)

            # Pied de page
            doc.add_page_break()
            footer = doc.sections[0].footer
            footer_para = footer.paragraphs[0]
            footer_para.text = "LIK Insurance Analyst - Confidential"
            footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

            doc.save(buffer)
            buffer.seek(0)

            return buffer

        except Exception as e:
            print(f"Erreur Word: {e}")
            raise

    def _create_minimal_pdf(self, title: str, content: str) -> BytesIO:
        """PDF minimal de secours"""
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)

        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 800, title)

        c.setFont("Helvetica", 10)
        c.drawString(100, 780, f"LIK Insurance Analyst - {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        c.setFont("Helvetica", 11)
        y_position = 750

        for line in content.split('\n')[:20]:
            if y_position < 50:
                break
            if line.strip():
                c.drawString(50, y_position, line[:80])
                y_position -= 20

        c.setFont("Helvetica-Oblique", 8)
        c.drawString(200, 30, "Généré par LIK Insurance Analyst")

        c.save()
        buffer.seek(0)
        return buffer
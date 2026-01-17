# modules/insight_engine.py

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import io
from typing import Dict, List, Any, Optional, Union
from scipy import stats


class CustomerAdapter:

    @staticmethod
    def adapt_for_powerbi(df: pd.DataFrame) -> pd.DataFrame:
        df_export = df.copy()

        if "niveau_risque" in df_export.columns:
            df_export["risk_color"] = df_export["niveau_risque"].map({
                "Faible": "#2ECC71",
                "Moyen": "#F39C12",
                "Élevé": "#E74C3C"
            })

        if "score_risque" in df_export.columns:
            df_export["priority"] = df_export["score_risque"].apply(
                lambda x: "Haute" if x > 70 else "Moyenne" if x > 30 else "Basse"
            )

        num_cols = df_export.select_dtypes(include=[np.number]).columns
        for col in num_cols:
            df_export[col] = df_export[col].round(2)

        return df_export

    @staticmethod
    def to_csv_string(df: pd.DataFrame) -> str:
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, sep=';', encoding='utf-8-sig')
        return csv_buffer.getvalue()

    @staticmethod
    def to_json_api(data: Union[pd.DataFrame, Dict, List]) -> str:
        if isinstance(data, pd.DataFrame):
            json_data = {
                "metadata": {
                    "row_count": len(data),
                    "column_count": len(data.columns),
                    "generated_at": pd.Timestamp.now().isoformat()
                },
                "data": data.to_dict(orient='records')
            }
        else:
            json_data = data
        return json.dumps(json_data, ensure_ascii=False, indent=2, default=str)


class InsightEngine:

    def __init__(self):
        self.insights = []
        self.adapter = CustomerAdapter()

    def build_client_risk_table(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()

        data["Prime"] = pd.to_numeric(data["Prime"], errors="coerce")
        data["nb_jour_couv"] = pd.to_numeric(data["nb_jour_couv"], errors="coerce")

        data["prime_par_jour"] = data["Prime"] / data["nb_jour_couv"].replace(0, np.nan)

        data["is_avenant"] = (
            data["libop"].astype(str).str.lower().str.contains("avenant")
        ).astype(int)

        client = (
            data.groupby(["ncli", "nomncli"], dropna=False)
            .agg(
                prime_totale=("Prime", "sum"),
                prime_moyenne=("Prime", "mean"),
                prime_par_jour_moy=("prime_par_jour", "mean"),
                duree_moyenne=("nb_jour_couv", "mean"),
                duree_min=("nb_jour_couv", "min"),
                duree_max=("nb_jour_couv", "max"),
                nb_avenants=("is_avenant", "sum"),
                nb_operations=("ncli", "count"),
                dernier_prime=("Prime", "last"),
                dernier_duree=("nb_jour_couv", "last")
            )
            .reset_index()
        )

        if 'sinistre' in data.columns:
            sinistres = data.groupby("ncli")["sinistre"].sum()
            client = client.merge(sinistres.rename('frequence_sinistre'),
                                  left_on='ncli', right_index=True, how='left')

        if 'montant_sinistre' in data.columns:
            cout_moyen = data.groupby("ncli")["montant_sinistre"].mean()
            cout_total = data.groupby("ncli")["montant_sinistre"].sum()
            client = client.merge(cout_moyen.rename('cout_moyen_sinistre'),
                                  left_on='ncli', right_index=True, how='left')
            client = client.merge(cout_total.rename('cout_total_sinistres'),
                                  left_on='ncli', right_index=True, how='left')

        if 'retard_jours' in data.columns:
            retard_moyen = data.groupby("ncli")["retard_jours"].mean()
            nb_retards = (data["retard_jours"] > 0).groupby(data["ncli"]).sum()
            client = client.merge(retard_moyen.rename('retard_paiement_moyen'),
                                  left_on='ncli', right_index=True, how='left')
            client = client.merge(nb_retards.rename('nb_retards'),
                                  left_on='ncli', right_index=True, how='left')

        if 'impaye' in data.columns:
            impayes = data.groupby("ncli")["impaye"].sum()
            client = client.merge(impayes.rename('nb_impayes'),
                                  left_on='ncli', right_index=True, how='left')

        if 'statut' in data.columns:
            taux_resil = (data["statut"] == "résilié").groupby(data["ncli"]).mean()
            statut_actuel = data.groupby("ncli")["statut"].last()
            client = client.merge(taux_resil.rename('taux_resiliation'),
                                  left_on='ncli', right_index=True, how='left')
            client = client.merge(statut_actuel.rename('statut_actuel'),
                                  left_on='ncli', right_index=True, how='left')

        if 'cout_sinistres' in data.columns:
            cout_sinistres_total = data.groupby("ncli")["cout_sinistres"].sum()
            client = client.merge(cout_sinistres_total.rename('cout_sinistres_total'),
                                  left_on='ncli', right_index=True, how='left')
            client['marge_technique'] = client['prime_totale'] - client['cout_sinistres_total']
            client['loss_ratio'] = client['cout_sinistres_total'] / client['prime_totale'].replace(0, np.nan)

        if 'date_souscription' in data.columns:
            try:
                data['date_souscription'] = pd.to_datetime(data['date_souscription'], errors='coerce')
                anciennete = (pd.Timestamp.now() - data.groupby('ncli')['date_souscription'].min()).dt.days
                client = client.merge(anciennete.rename('anciennete_jours'),
                                      left_on='ncli', right_index=True, how='left')
                client['anciennete_mois'] = client['anciennete_jours'] / 30.44
            except:
                pass

        if 'date_contrat' in data.columns:
            try:
                dates_contrat = pd.to_datetime(data['date_contrat'], errors='coerce')
                nb_renouvellements = data.groupby('ncli')['date_contrat'].nunique() - 1
                client = client.merge(nb_renouvellements.rename('nb_renouvellements'),
                                      left_on='ncli', right_index=True, how='left')
            except:
                pass

        client["prime_75_percentile"] = client["prime_totale"] > client["prime_totale"].quantile(0.75)
        client["variabilite_duree"] = client["duree_max"] - client["duree_min"]

        client = client.replace([np.inf, -np.inf], np.nan)

        fill_defaults = {
            'prime_par_jour_moy': client['prime_par_jour_moy'].median(),
            'duree_moyenne': client['duree_moyenne'].median(),
            'prime_totale': 0,
            'nb_avenants': 0,
            'frequence_sinistre': 0,
            'cout_moyen_sinistre': 0,
            'cout_total_sinistres': 0,
            'retard_paiement_moyen': 0,
            'nb_retards': 0,
            'nb_impayes': 0,
            'taux_resiliation': 0,
            'cout_sinistres_total': 0,
            'marge_technique': client['prime_totale'],
            'loss_ratio': 0,
            'anciennete_jours': client['duree_moyenne'].median() * 2,
            'nb_renouvellements': 0
        }

        for col, default_val in fill_defaults.items():
            if col in client.columns:
                client[col] = client[col].fillna(default_val)

        numeric_cols = client.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col not in fill_defaults and col != 'ncli':
                client[col] = client[col].fillna(0)

        return client

    def compute_risk_score(self, client_df: pd.DataFrame) -> pd.DataFrame:
        df = client_df.copy()

        def normalize(col):
            min_val = col.min()
            max_val = col.max()
            if max_val - min_val < 1e-9:
                return pd.Series([0.5] * len(col), index=col.index)
            return (col - min_val) / (max_val - min_val)

        df["ppj_norm"] = normalize(df["prime_par_jour_moy"])
        df["avenants_norm"] = normalize(df["nb_avenants"])
        df["duree_risque"] = 1 - normalize(df["duree_moyenne"])

        indicators = {
            "ppj_norm": 0.25,
            "avenants_norm": 0.15,
            "duree_risque": 0.10
        }

        if 'frequence_sinistre' in df.columns:
            df["freq_sinistre_norm"] = normalize(df["frequence_sinistre"])
            indicators["freq_sinistre_norm"] = 0.20

        if 'cout_moyen_sinistre' in df.columns:
            df["cout_sinistre_norm"] = normalize(df["cout_moyen_sinistre"])
            indicators["cout_sinistre_norm"] = 0.15

        if 'retard_paiement_moyen' in df.columns:
            df["retard_norm"] = normalize(df["retard_paiement_moyen"])
            indicators["retard_norm"] = 0.10

        if 'nb_impayes' in df.columns:
            df["impayes_norm"] = normalize(df["nb_impayes"])
            indicators["impayes_norm"] = 0.08

        if 'taux_resiliation' in df.columns:
            df["resiliation_norm"] = normalize(df["taux_resiliation"])
            indicators["resiliation_norm"] = 0.07

        if 'loss_ratio' in df.columns:
            df["loss_ratio_norm"] = normalize(df["loss_ratio"])
            indicators["loss_ratio_norm"] = 0.05

        df["score_risque"] = 0

        total_weight = sum(indicators.values())

        for indicator, weight in indicators.items():
            if indicator in df.columns:
                df["score_risque"] += (weight / total_weight) * df[indicator]

        df["score_risque"] = df["score_risque"] * 100
        df["score_risque"] = df["score_risque"].clip(0, 100).round(1)

        df["niveau_risque"] = pd.cut(
            df["score_risque"],
            bins=[-1, 30, 70, 100],
            labels=["Faible", "Moyen", "Élevé"]
        )

        df["decision_assurance"] = df["niveau_risque"].map({
            "Faible": "Maintien des conditions - Programme fidélité",
            "Moyen": "Surveillance renforcée - Revue trimestrielle",
            "Élevé": "Révision de la prime + Entretien conseil + Contrôle"
        })

        df["priorite_action"] = df["score_risque"].apply(
            lambda x: "Haute" if x > 70 else "Moyenne" if x > 30 else "Basse"
        )

        return df

    def generate_client_insight(self, row: pd.Series, ppj_median: float) -> str:
        reasons = []

        if pd.notna(row.get("prime_par_jour_moy")) and row["prime_par_jour_moy"] > ppj_median * 1.2:
            reasons.append("prime par jour élevée")

        if pd.notna(row.get("duree_moyenne")) and row["duree_moyenne"] < 180:
            reasons.append("durée de couverture courte")

        if pd.notna(row.get("nb_avenants")) and row["nb_avenants"] >= 2:
            reasons.append("instabilité contractuelle")

        if 'frequence_sinistre' in row and row.get("frequence_sinistre", 0) > 1:
            reasons.append("fréquence sinistres élevée")

        if 'retard_paiement_moyen' in row and row.get("retard_paiement_moyen", 0) > 15:
            reasons.append("retards de paiement fréquents")

        if 'loss_ratio' in row and row.get("loss_ratio", 0) > 0.7:
            reasons.append("loss ratio défavorable")

        if not reasons:
            return "Client stable, bon profil risque"

        return f"Client à risque {row.get('niveau_risque', 'inconnu')} : " + ", ".join(reasons) + "."

    def generate_insights(self, scored_df: pd.DataFrame) -> List[str]:
        insights = []

        insights.append(f"Clients analysés : {len(scored_df):,}")

        risk_dist = scored_df["niveau_risque"].value_counts(normalize=True)
        for niveau, pct in risk_dist.items():
            insights.append(f"{niveau} risque : {pct:.1%}")

        insights.append(f"Score de risque moyen : {scored_df['score_risque'].mean():.1f}/100")

        if 'frequence_sinistre' in scored_df.columns:
            high_claim = (scored_df['frequence_sinistre'] > 1).mean()
            if high_claim > 0:
                insights.append(f"Clients multi-sinistres : {high_claim:.1%}")

        if 'retard_paiement_moyen' in scored_df.columns:
            late_payers = (scored_df['retard_paiement_moyen'] > 15).mean()
            if late_payers > 0:
                insights.append(f"Retards paiement (>15j) : {late_payers:.1%}")

        if 'loss_ratio' in scored_df.columns:
            bad_loss_ratio = (scored_df['loss_ratio'] > 0.7).mean()
            if bad_loss_ratio > 0:
                insights.append(f"Loss ratio >70% : {bad_loss_ratio:.1%}")

        self.insights = insights
        return insights

    def portfolio_risk_summary(self, scored_df: pd.DataFrame) -> Dict[str, float]:
        summary = {
            "clients_total": len(scored_df),
            "pct_risque_eleve": round((scored_df["niveau_risque"] == "Élevé").mean() * 100, 1),
            "pct_risque_moyen": round((scored_df["niveau_risque"] == "Moyen").mean() * 100, 1),
            "pct_risque_faible": round((scored_df["niveau_risque"] == "Faible").mean() * 100, 1),
            "score_moyen": round(scored_df["score_risque"].mean(), 1),
            "prime_totale_portefeuille": round(scored_df["prime_totale"].sum(), 0)
        }

        if 'frequence_sinistre' in scored_df.columns:
            summary["sinistres_total"] = int(scored_df["frequence_sinistre"].sum())
            summary["freq_sinistre_moy"] = round(scored_df["frequence_sinistre"].mean(), 2)

        if 'cout_total_sinistres' in scored_df.columns:
            summary["cout_sinistres_total"] = round(scored_df["cout_total_sinistres"].sum(), 0)

        if 'marge_technique' in scored_df.columns:
            summary["marge_technique_totale"] = round(scored_df["marge_technique"].sum(), 0)
            summary["marge_moyenne"] = round(scored_df["marge_technique"].mean(), 0)

        return summary

    def create_dashboard_visualizations(self, scored_df: pd.DataFrame) -> Dict[str, go.Figure]:
        figs = {}

        if "score_risque" in scored_df.columns:
            figs["hist_score"] = px.histogram(
                scored_df,
                x="score_risque",
                nbins=20,
                title="Distribution du score de risque",
                labels={"score_risque": "Score de risque", "count": "Nombre de clients"}
            )

        if all(col in scored_df.columns for col in ["prime_par_jour_moy", "score_risque", "niveau_risque"]):
            figs["ppj_vs_score"] = px.scatter(
                scored_df,
                x="prime_par_jour_moy",
                y="score_risque",
                color="niveau_risque",
                title="Prime par jour vs Score de risque",
                hover_data=["nomncli", "nb_avenants",
                            "frequence_sinistre"] if 'frequence_sinistre' in scored_df.columns else ["nomncli",
                                                                                                     "nb_avenants"]
            )

        if 'frequence_sinistre' in scored_df.columns:
            figs["sinistres_vs_risque"] = px.scatter(
                scored_df,
                x="frequence_sinistre",
                y="score_risque",
                color="niveau_risque",
                title="Fréquence sinistres vs Score de risque",
                size="prime_totale" if 'prime_totale' in scored_df.columns else None
            )

        numeric_cols = scored_df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) > 2:
            important_cols = ['score_risque', 'prime_par_jour_moy', 'frequence_sinistre',
                              'retard_paiement_moyen', 'loss_ratio', 'nb_avenants',
                              'duree_moyenne', 'prime_totale']
            available_cols = [col for col in important_cols if col in numeric_cols]

            if len(available_cols) >= 3:
                corr_matrix = scored_df[available_cols].corr().round(2)
                figs["heatmap"] = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    colorscale='RdBu',
                    zmin=-1,
                    zmax=1,
                    text=corr_matrix.values,
                    texttemplate='%{text:.2f}'
                ))
                figs["heatmap"].update_layout(title="Corrélation entre indicateurs")

        return figs

    def dashboard_summary_table(self, scored_df: pd.DataFrame) -> pd.DataFrame:
        columns_to_show = ["nomncli", "score_risque", "niveau_risque", "decision_assurance", "priorite_action"]

        if 'frequence_sinistre' in scored_df.columns:
            columns_to_show.append("frequence_sinistre")

        if 'retard_paiement_moyen' in scored_df.columns:
            columns_to_show.append("retard_paiement_moyen")

        if 'marge_technique' in scored_df.columns:
            columns_to_show.append("marge_technique")

        return (
            scored_df[columns_to_show]
            .sort_values("score_risque", ascending=False)
            .head(15)
        )

    def generate_narrative_report(self, scored_df: pd.DataFrame) -> str:
        summary = self.portfolio_risk_summary(scored_df)

        report = []
        report.append("Rapport d'Analyse - Assurance LIK")
        report.append("\nSynthèse portefeuille")
        report.append(f"- Clients analysés : {summary['clients_total']:,}")
        report.append(f"- Score de risque moyen : {summary['score_moyen']}/100")
        report.append(f"- Clients à risque élevé : {summary['pct_risque_eleve']}%")
        report.append(f"- Prime totale portefeuille : {summary['prime_totale_portefeuille']:,} MAD")

        if 'sinistres_total' in summary:
            report.append(f"- Nombre total sinistres : {summary['sinistres_total']}")

        if 'cout_sinistres_total' in summary:
            report.append(f"- Coût total sinistres : {summary['cout_sinistres_total']:,} MAD")

        if 'marge_technique_totale' in summary:
            report.append(f"- Marge technique totale : {summary['marge_technique_totale']:,} MAD")

        report.append("\nFacteurs clés de risque")
        report.append("- Prime par jour élevée (>120% médiane)")
        report.append("- Fréquence sinistres élevée (>1 par an)")
        report.append("- Retards de paiement fréquents (>15 jours)")
        report.append("- Instabilité contractuelle (≥2 avenants)")
        report.append("- Durée couverture courte (<180 jours)")

        report.append("\nRecommandations stratégiques")
        report.append("1. Tarification dynamique : Ajuster primes selon score risque")
        report.append("2. Programme fidélisation : Clients stables à faible risque")
        report.append("3. Surveillance renforcée : Clients risque moyen (revue trimestrielle)")
        report.append("4. Actions correctives : Clients risque élevé (entretien conseil)")
        report.append("5. Prévention sinistres : Cibler clients multi-sinistrés")

        report.append("\nIndicateurs de performance")
        report.append("- Objectif : Réduction résiliation 15% dans 12 mois")
        report.append("- Suivi : Score risque moyen < 40/100")
        report.append("- Rentabilité : Marge technique > 25% prime totale")
        report.append("- Satisfaction : Taux renouvellement > 85%")

        return "\n".join(report)

    def create_univariate_histogram(self, df: pd.DataFrame, column: str, bins: int = 30) -> go.Figure:
        fig = px.histogram(
            df,
            x=column,
            nbins=bins,
            title=f"Distribution de {column}",
            labels={column: column, "count": "Fréquence"},
            marginal="box",
            opacity=0.7
        )
        return fig

    def create_univariate_boxplot(self, df: pd.DataFrame, column: str) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Box(y=df[column], name=column))
        fig.update_layout(title=f"Boîte à moustaches de {column}")
        return fig

    def create_bivariate_scatter(self, df: pd.DataFrame, x_col: str, y_col: str,
                                 color_col: Optional[str] = None) -> go.Figure:
        if color_col and color_col in df.columns:
            fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=f"{x_col} vs {y_col}")
        else:
            fig = px.scatter(df, x=x_col, y=y_col, title=f"{x_col} vs {y_col}")
        return fig

    def prepare_powerbi_data(self, scored_df: pd.DataFrame) -> Dict:
        data = scored_df.copy()

        risk_dist = data.groupby("niveau_risque").agg({
            "ncli": "count",
            "prime_totale": "sum",
            "score_risque": "mean",
            "prime_par_jour_moy": "mean"
        }).reset_index()
        risk_dist = risk_dist.rename(columns={"ncli": "count"})

        top_risky = data.nlargest(10, "score_risque")[[
            "ncli", "nomncli", "score_risque", "niveau_risque",
            "prime_totale", "nb_avenants", "decision_assurance"
        ]]

        overall_metrics = self.portfolio_risk_summary(data)

        return {
            "risk_distribution": risk_dist.to_dict("records"),
            "top_risky_clients": top_risky.to_dict("records"),
            "overall_metrics": overall_metrics,
            "raw_data_sample": data.head(100).to_dict("records")
        }

    def prepare_powerbi_dataframe(self, scored_df: pd.DataFrame) -> pd.DataFrame:
        return self.adapter.adapt_for_powerbi(scored_df)

    def export_to_csv(self, scored_df: pd.DataFrame) -> str:
        df_export = self.prepare_powerbi_dataframe(scored_df)

        essential_cols = [
            "ncli", "nomncli", "score_risque", "niveau_risque",
            "prime_totale", "prime_par_jour_moy", "duree_moyenne",
            "nb_avenants", "decision_assurance", "priority"
        ]

        if 'frequence_sinistre' in df_export.columns:
            essential_cols.append("frequence_sinistre")

        if 'retard_paiement_moyen' in df_export.columns:
            essential_cols.append("retard_paiement_moyen")

        if 'marge_technique' in df_export.columns:
            essential_cols.append("marge_technique")

        if 'loss_ratio' in df_export.columns:
            essential_cols.append("loss_ratio")

        available_cols = [col for col in essential_cols if col in df_export.columns]
        df_export = df_export[available_cols]

        return self.adapter.to_csv_string(df_export)

    def export_to_json(self, powerbi_data: Dict) -> str:
        return self.adapter.to_json_api(powerbi_data)

    def get_customer_adapter(self) -> CustomerAdapter:
        return self.adapter
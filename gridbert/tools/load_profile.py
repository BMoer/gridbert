# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Load Profile Analysis — Lastprofil-Analyse mit Metriken, Anomalie-Erkennung und Visualisierungen.

Ported from ~/Projekte/Load Profile Analysis. Key algorithms:
- Metrics: base load (15th percentile), peak, full load hours, monthly aggregation
- FDA Anomaly Detection: TVD-MSS (Huang & Sun 2019) with k-means clustering
- Savings: base load reduction, peak shaving, weekend/night optimization
- Visualizations: heatmap, duration curve, monthly chart
"""

from __future__ import annotations

import base64
import io
import logging
from datetime import date

import numpy as np
import pandas as pd

from gridbert.models.load_profile import (
    AnomalyResult,
    ClusterInfo,
    LoadProfileAnalysis,
    LoadProfileMetrics,
    SavingsOpportunity,
)

log = logging.getLogger(__name__)

# --- Constants ---
QUANTILE_BASE_LOAD = 0.15
INTERVAL_HOURS = 0.25  # 15 min
HOURS_PER_YEAR = 8760
NIGHT_START = 22
NIGHT_END = 4


def analyze_load_profile(
    consumption_data: list[dict],
    price_per_kwh: float = 0.20,
) -> LoadProfileAnalysis:
    """Vollständige Lastprofil-Analyse.

    Args:
        consumption_data: Liste von {timestamp: ISO-string, kwh: float} Einträgen.
        price_per_kwh: Strompreis in EUR/kWh (brutto) für Sparpotenzialkalkulation.

    Returns:
        LoadProfileAnalysis mit Metriken, Anomalien, Sparpotenzialen und Visualisierungen.
    """
    try:
        df = _prepare_dataframe(consumption_data)
        if df.empty or len(df) < 96:  # Minimum 1 Tag
            return LoadProfileAnalysis(
                metrics=_empty_metrics(),
                analyse_erfolgreich=False,
                fehler="Zu wenig Datenpunkte (mindestens 1 Tag à 96 Intervalle benötigt).",
            )

        metrics = _calculate_metrics(df)
        anomalien, cluster = _detect_anomalies(df)
        einsparpotenziale = _estimate_savings(metrics, price_per_kwh)
        visualisierungen = _generate_visualizations(df, metrics)

        sparpotenzial_kwh = sum(s.einsparung_kwh for s in einsparpotenziale)
        sparpotenzial_eur = sum(s.einsparung_eur for s in einsparpotenziale)

        return LoadProfileAnalysis(
            metrics=metrics,
            anomalien=anomalien,
            cluster=cluster,
            einsparpotenziale=einsparpotenziale,
            sparpotenzial_kwh=round(sparpotenzial_kwh, 1),
            sparpotenzial_eur=round(sparpotenzial_eur, 2),
            visualisierungen=visualisierungen,
        )
    except Exception as exc:
        log.exception("Lastprofil-Analyse fehlgeschlagen")
        return LoadProfileAnalysis(
            metrics=_empty_metrics(),
            analyse_erfolgreich=False,
            fehler=str(exc),
        )


# --- Data Preparation ---


def _prepare_dataframe(data: list[dict]) -> pd.DataFrame:
    """Rohdaten zu DataFrame mit DatetimeIndex und consumption_kw konvertieren."""
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()

    # kWh → kW (15-min Intervall)
    if "kwh" in df.columns:
        df["consumption_kw"] = df["kwh"] / INTERVAL_HOURS
    elif "kw" in df.columns:
        df["consumption_kw"] = df["kw"]

    df = df[["consumption_kw"]].dropna()
    # Negative Werte entfernen
    df = df[df["consumption_kw"] >= 0]
    return df


# --- Metrics Calculation ---


def _calculate_metrics(df: pd.DataFrame) -> LoadProfileMetrics:
    """Kennzahlen berechnen."""
    kw = df["consumption_kw"]
    total_kwh = float(kw.sum() * INTERVAL_HOURS)
    grundlast_kw = float(np.percentile(kw, QUANTILE_BASE_LOAD * 100))
    spitzenlast_kw = float(kw.max())

    volllaststunden = total_kwh / spitzenlast_kw if spitzenlast_kw > 0 else 0
    grundlast_anteil = (grundlast_kw * HOURS_PER_YEAR) / total_kwh * 100 if total_kwh > 0 else 0

    # Monatsaggregation
    monthly = df.resample("ME").apply(lambda x: float(x.sum() * INTERVAL_HOURS))
    monthly_kwh = {
        ts.strftime("%Y-%m"): round(val, 1)
        for ts, val in monthly["consumption_kw"].items()
    }

    # Nachtverbrauch (22:00-04:00)
    night_mask = (df.index.hour >= NIGHT_START) | (df.index.hour < NIGHT_END)
    nacht_mean = float(kw[night_mask].mean()) if night_mask.any() else 0.0

    # Wochenendverbrauch
    weekend_mask = df.index.dayofweek >= 5
    wochenende_mean = float(kw[weekend_mask].mean()) if weekend_mask.any() else 0.0

    return LoadProfileMetrics(
        mean_kw=round(float(kw.mean()), 3),
        median_kw=round(float(kw.median()), 3),
        min_kw=round(float(kw.min()), 3),
        max_kw=round(spitzenlast_kw, 3),
        std_kw=round(float(kw.std()), 3),
        grundlast_kw=round(grundlast_kw, 3),
        spitzenlast_kw=round(spitzenlast_kw, 3),
        volllaststunden=round(volllaststunden, 0),
        grundlast_anteil_pct=round(grundlast_anteil, 1),
        total_kwh=round(total_kwh, 1),
        monthly_kwh=monthly_kwh,
        nacht_mean_kw=round(nacht_mean, 3),
        wochenende_mean_kw=round(wochenende_mean, 3),
    )


# --- Anomaly Detection ---


def _detect_anomalies(df: pd.DataFrame) -> tuple[list[AnomalyResult], list[ClusterInfo]]:
    """FDA-basierte Anomalie-Erkennung (fallback auf statistische Methode)."""
    # Tagesprofile erstellen (96 Intervalle pro Tag)
    daily_profiles = _build_daily_profiles(df)
    if len(daily_profiles) < 14:
        return [], []

    try:
        return _fda_anomaly_detection(daily_profiles)
    except ImportError:
        log.info("scikit-fda nicht installiert, verwende statistische Anomalie-Erkennung")
        return _statistical_anomaly_detection(daily_profiles)
    except Exception as exc:
        log.warning("FDA-Anomalie-Erkennung fehlgeschlagen: %s", exc)
        return _statistical_anomaly_detection(daily_profiles)


def _build_daily_profiles(df: pd.DataFrame) -> dict[date, np.ndarray]:
    """Tagesprofile als 96-Punkt Arrays extrahieren."""
    profiles: dict[date, np.ndarray] = {}
    for day, group in df.groupby(df.index.date):
        if len(group) >= 90:  # Mindestens ~94% vollständig
            values = group["consumption_kw"].values[:96]
            if len(values) == 96:
                profiles[day] = values
    return profiles


def _fda_anomaly_detection(
    profiles: dict[date, np.ndarray],
) -> tuple[list[AnomalyResult], list[ClusterInfo]]:
    """FDA TVD-MSS Anomalie-Erkennung mit scikit-fda."""
    import skfda
    from skfda.ml.clustering import KMeans as FDAKMeans

    dates = sorted(profiles.keys())
    data_matrix = np.array([profiles[d] for d in dates])

    fd = skfda.FDataGrid(data_matrix, grid_points=np.linspace(0, 24, 96))

    # K-Means Clustering
    n_clusters = min(4, max(2, len(dates) // 15))
    kmeans = FDAKMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(fd)
    centroids = kmeans.cluster_centers_.data_matrix.squeeze()

    # Anomalien: Tage die stark von ihrem Cluster-Mittelwert abweichen
    anomalien: list[AnomalyResult] = []
    for i, (d, profile) in enumerate(zip(dates, data_matrix)):
        cluster_id = int(labels[i])
        centroid = centroids[cluster_id]
        diff = profile - centroid
        excess_kwh = float(np.sum(np.maximum(diff, 0)) * INTERVAL_HOURS)
        peak_dev = float(np.max(np.abs(diff)))

        # Anomalie-Schwelle: Tagesabweichung > 2 Standardabweichungen
        cluster_mask = labels == cluster_id
        cluster_data = data_matrix[cluster_mask]
        cluster_std = np.std(cluster_data - centroid)

        if cluster_std > 0 and np.max(np.abs(diff)) > 2 * cluster_std:
            anomalien.append(AnomalyResult(
                datum=d,
                wochentag=_wochentag(d),
                typ=_classify_anomaly(diff, cluster_std),
                cluster_id=cluster_id,
                abweichung_kwh=round(excess_kwh, 2),
                spitzen_abweichung_kw=round(peak_dev, 3),
            ))

    # Cluster-Info
    cluster_info: list[ClusterInfo] = []
    for cid in range(n_clusters):
        mask = labels == cid
        cluster_dates = [dates[i] for i in range(len(dates)) if mask[i]]
        cluster_data = data_matrix[mask]
        cluster_info.append(ClusterInfo(
            cluster_id=cid,
            tage=int(mask.sum()),
            mean_daily_kwh=round(float(cluster_data.sum(axis=1).mean() * INTERVAL_HOURS), 1),
            typische_wochentage=_typical_weekdays(cluster_dates),
        ))

    return anomalien, cluster_info


def _statistical_anomaly_detection(
    profiles: dict[date, np.ndarray],
) -> tuple[list[AnomalyResult], list[ClusterInfo]]:
    """Einfache statistische Anomalie-Erkennung (Fallback)."""
    dates = sorted(profiles.keys())
    data_matrix = np.array([profiles[d] for d in dates])

    mean_profile = np.mean(data_matrix, axis=0)
    std_profile = np.std(data_matrix, axis=0)

    anomalien: list[AnomalyResult] = []
    for i, (d, profile) in enumerate(zip(dates, data_matrix)):
        diff = profile - mean_profile
        z_scores = np.abs(diff) / np.maximum(std_profile, 0.001)
        max_z = float(np.max(z_scores))

        if max_z > 2.5:
            excess_kwh = float(np.sum(np.maximum(diff, 0)) * INTERVAL_HOURS)
            anomalien.append(AnomalyResult(
                datum=d,
                wochentag=_wochentag(d),
                typ="magnitude" if np.mean(z_scores) > 2 else "shape",
                abweichung_kwh=round(excess_kwh, 2),
                spitzen_abweichung_kw=round(float(np.max(np.abs(diff))), 3),
            ))

    return anomalien, []


def _classify_anomaly(diff: np.ndarray, cluster_std: float) -> str:
    """Anomalie-Typ klassifizieren."""
    magnitude = np.mean(np.abs(diff)) > 1.5 * cluster_std
    shape = np.std(diff) > 1.5 * cluster_std
    if magnitude and shape:
        return "both"
    return "magnitude" if magnitude else "shape"


def _wochentag(d: date) -> str:
    """Deutschen Wochentag-Namen zurückgeben."""
    tage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    return tage[d.weekday()]


def _typical_weekdays(dates: list[date]) -> list[str]:
    """Häufigste Wochentage in einer Datumsliste."""
    from collections import Counter
    if not dates:
        return []
    counts = Counter(_wochentag(d) for d in dates)
    return [day for day, _ in counts.most_common(3)]


# --- Savings Estimation ---


def _estimate_savings(metrics: LoadProfileMetrics, price: float) -> list[SavingsOpportunity]:
    """Einsparpotenziale berechnen."""
    opportunities: list[SavingsOpportunity] = []

    # 1. Grundlast-Reduktion (10% realistisch)
    if metrics.grundlast_kw > 0:
        reduction_kw = metrics.grundlast_kw * 0.10
        savings_kwh = reduction_kw * HOURS_PER_YEAR
        savings_eur = savings_kwh * price
        if savings_eur >= 10:
            opportunities.append(SavingsOpportunity(
                kategorie="base_load",
                beschreibung=(
                    f"Grundlast-Reduktion von {metrics.grundlast_kw:.2f} kW "
                    f"um 10% ({reduction_kw:.2f} kW)"
                ),
                einsparung_kwh=round(savings_kwh, 1),
                einsparung_eur=round(savings_eur, 2),
                konfidenz="medium",
            ))

    # 2. Peak Shaving (nur bei peak_ratio > 2.5)
    if metrics.spitzenlast_kw > 0 and metrics.mean_kw > 0:
        peak_ratio = metrics.spitzenlast_kw / metrics.mean_kw
        if peak_ratio > 2.5:
            peak_reduction = (metrics.spitzenlast_kw - 2.5 * metrics.mean_kw) * 0.15
            peak_hours = HOURS_PER_YEAR * 0.05
            savings_kwh = peak_reduction * peak_hours * 0.20
            savings_eur = savings_kwh * price
            if savings_eur >= 10:
                opportunities.append(SavingsOpportunity(
                    kategorie="peak_shaving",
                    beschreibung=(
                        f"Spitzenlast-Reduktion (Peak/Mean Ratio: {peak_ratio:.1f}x)"
                    ),
                    einsparung_kwh=round(savings_kwh, 1),
                    einsparung_eur=round(savings_eur, 2),
                    konfidenz="low",
                ))

    # 3. Wochenend-Optimierung
    if metrics.wochenende_mean_kw > metrics.grundlast_kw * 1.2:
        excess = metrics.wochenende_mean_kw - metrics.grundlast_kw
        reducible = excess * 0.50
        weekend_hours = 104 * 24  # 104 Wochenendtage × 24h
        savings_kwh = reducible * weekend_hours
        savings_eur = savings_kwh * price
        if savings_eur >= 10:
            opportunities.append(SavingsOpportunity(
                kategorie="weekend",
                beschreibung=(
                    f"Wochenend-Verbrauch ({metrics.wochenende_mean_kw:.2f} kW) "
                    f"liegt 20%+ über Grundlast ({metrics.grundlast_kw:.2f} kW)"
                ),
                einsparung_kwh=round(savings_kwh, 1),
                einsparung_eur=round(savings_eur, 2),
                konfidenz="medium",
            ))

    # 4. Nacht-Optimierung
    if metrics.nacht_mean_kw > metrics.grundlast_kw * 1.1:
        excess = metrics.nacht_mean_kw - metrics.grundlast_kw
        reducible = excess * 0.30
        night_hours = 8 * 365
        savings_kwh = reducible * night_hours
        savings_eur = savings_kwh * price
        if savings_eur >= 10:
            opportunities.append(SavingsOpportunity(
                kategorie="night",
                beschreibung=(
                    f"Nachtverbrauch ({metrics.nacht_mean_kw:.2f} kW) "
                    f"liegt 10%+ über Grundlast ({metrics.grundlast_kw:.2f} kW)"
                ),
                einsparung_kwh=round(savings_kwh, 1),
                einsparung_eur=round(savings_eur, 2),
                konfidenz="low",
            ))

    return opportunities


# --- Visualizations ---


def _generate_visualizations(
    df: pd.DataFrame, metrics: LoadProfileMetrics
) -> dict[str, str]:
    """Visualisierungen als base64 PNG generieren."""
    viz: dict[str, str] = {}

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        viz["heatmap"] = _generate_heatmap(df, plt)
        viz["jahresdauerlinie"] = _generate_duration_curve(df, plt)
        viz["monatsverbrauch"] = _generate_monthly_chart(df, metrics, plt)
    except ImportError:
        log.info("matplotlib nicht installiert — keine Visualisierungen erstellt")

    return viz


def _fig_to_base64(fig) -> str:
    """Matplotlib Figure → base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    result = base64.b64encode(buf.read()).decode("utf-8")
    fig.clear()
    return result


def _generate_heatmap(df: pd.DataFrame, plt) -> str:
    """Heatmap: Stunde × Tag Carpet Plot."""
    pivot = df.copy()
    pivot["hour"] = pivot.index.hour + pivot.index.minute / 60
    pivot["date"] = pivot.index.date

    heatmap_data = pivot.pivot_table(
        values="consumption_kw", index="hour", columns="date", aggfunc="mean"
    )

    fig, ax = plt.subplots(figsize=(14, 6))
    im = ax.pcolormesh(
        range(heatmap_data.shape[1]),
        heatmap_data.index,
        heatmap_data.values,
        cmap="YlOrRd",
        shading="auto",
    )
    ax.set_ylabel("Stunde")
    ax.set_xlabel("Tag")
    ax.set_title("Lastprofil Heatmap (kW)")
    fig.colorbar(im, ax=ax, label="kW")
    result = _fig_to_base64(fig)
    plt.close(fig)
    return result


def _generate_duration_curve(df: pd.DataFrame, plt) -> str:
    """Jahresdauerlinie (sortiertes Lastprofil)."""
    sorted_kw = np.sort(df["consumption_kw"].values)[::-1]
    hours = np.arange(len(sorted_kw)) * INTERVAL_HOURS

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.fill_between(hours, sorted_kw, alpha=0.3, color="#22c55e")
    ax.plot(hours, sorted_kw, color="#16a34a", linewidth=1)
    ax.set_xlabel("Stunden")
    ax.set_ylabel("Leistung (kW)")
    ax.set_title("Jahresdauerlinie")
    ax.axhline(y=float(np.median(sorted_kw)), color="gray", linestyle="--", alpha=0.5, label="Median")
    ax.legend()
    result = _fig_to_base64(fig)
    plt.close(fig)
    return result


def _generate_monthly_chart(df: pd.DataFrame, metrics: LoadProfileMetrics, plt) -> str:
    """Monatsverbrauch als Balkendiagramm."""
    months = list(metrics.monthly_kwh.keys())
    values = list(metrics.monthly_kwh.values())

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(months, values, color="#22c55e", alpha=0.8)
    ax.set_xlabel("Monat")
    ax.set_ylabel("Verbrauch (kWh)")
    ax.set_title(f"Monatsverbrauch (Gesamt: {metrics.total_kwh:,.0f} kWh)")
    plt.xticks(rotation=45, ha="right")

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                f"{val:.0f}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    result = _fig_to_base64(fig)
    plt.close(fig)
    return result


def _empty_metrics() -> LoadProfileMetrics:
    """Leere Metriken für Fehlerfälle."""
    return LoadProfileMetrics(
        mean_kw=0, median_kw=0, min_kw=0, max_kw=0, std_kw=0,
        grundlast_kw=0, spitzenlast_kw=0, volllaststunden=0,
        grundlast_anteil_pct=0, total_kwh=0,
    )

"""Chart presentation helpers for Carbon Evidence Ledger.

Presentation only. Chart data is prepared from PipelineRunResult copies.
Charts are rendered exclusively through Streamlit-native Vega-Lite APIs —
never via custom HTML/SVG markdown.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from carbon_ledger.pipeline import PipelineRunResult
from carbon_ledger.ui.i18n import DEFAULT_LANG, t
from carbon_ledger.ui.view_models import (
    build_activity_overview,
    calculation_label,
    company_inventory_record_ids,
)

# Semantic visualization palette (shared across pages; Stage 3B.2b tokens)
COLOR_CALCULATED = "#14A39A"
COLOR_INFO = "#3563E9"
COLOR_SCOPE_1 = "#16324F"
COLOR_SCOPE_2 = "#0F8A83"
COLOR_SCOPE_3 = "#64748B"
COLOR_MISSING_CONVERSION = "#B7791F"
COLOR_MISSING_FACTOR = "#D97706"
COLOR_CRITICAL = "#B42318"
COLOR_SUPPORTING = "#94A3B8"
COLOR_NAVY = "#0D2238"
COLOR_SLATE = "#64748B"

# Bounded chart heights for SaaS layout (never full-viewport)
CHART_HEIGHT_OVERVIEW = 300
CHART_HEIGHT_SMALL = 240
CHART_HEIGHT_COMPACT = 120

CALC_STATUS_COLORS: dict[str, str] = {
    "calculated": COLOR_CALCULATED,
    "blocked_missing_conversion": COLOR_MISSING_CONVERSION,
    "blocked_natural_gas_type_required": COLOR_MISSING_CONVERSION,
    "no_factor_configured": COLOR_MISSING_FACTOR,
    "no_matching_factor": COLOR_MISSING_FACTOR,
    "not_emissions_activity": COLOR_SUPPORTING,
}

ISSUE_GAP_COLORS: dict[str, str] = {
    "blocked_missing_conversion": COLOR_MISSING_CONVERSION,
    "no_factor_configured": COLOR_MISSING_FACTOR,
    "no_matching_factor": COLOR_MISSING_FACTOR,
}

ISSUE_GAP_LABEL_KEYS: dict[str, str] = {
    "blocked_missing_conversion": "chart.issue.missing_conversion",
    "no_factor_configured": "chart.issue.missing_factor",
    "no_matching_factor": "chart.issue.missing_factor",
}


def _copy_frame(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    return frame.copy()


def calculation_status_distribution(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Count activities by friendly calculation-status label."""
    overview = build_activity_overview(result, lang)
    if overview.empty:
        return pd.DataFrame(columns=["status_code", "label", "count", "color"])
    counts = (
        overview.groupby(["calculation_status", "calculation_label"], dropna=False)
        .size()
        .reset_index(name="count")
    )
    rows: list[dict[str, Any]] = []
    for _, row in counts.iterrows():
        code = str(row["calculation_status"])
        rows.append(
            {
                "status_code": code,
                "label": str(row["calculation_label"]),
                "count": int(row["count"]),
                "color": CALC_STATUS_COLORS.get(code, COLOR_SUPPORTING),
            }
        )
    frame = pd.DataFrame(rows)
    return frame.sort_values("count", ascending=False).reset_index(drop=True)


def activity_status_breakdown(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """One row per activity with calculation status for horizontal bars."""
    overview = build_activity_overview(result, lang)
    if overview.empty:
        return pd.DataFrame(
            columns=["activity_name", "status_code", "label", "color", "rank"]
        )
    rows: list[dict[str, Any]] = []
    for index, row in overview.iterrows():
        code = str(row.get("calculation_status", ""))
        rows.append(
            {
                "activity_name": str(row.get("activity_name", "")),
                "status_code": code,
                "label": str(row.get("calculation_label", "")),
                "color": CALC_STATUS_COLORS.get(code, COLOR_SUPPORTING),
                "rank": 1,
            }
        )
    return pd.DataFrame(rows)


def calculated_emissions_contributions(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Contribution rows for company-inventory activities only."""
    overview = build_activity_overview(result, lang)
    if overview.empty:
        return pd.DataFrame(columns=["activity_name", "tco2e"])
    included_ids = company_inventory_record_ids(result)
    calculated = overview[
        overview["record_id"].astype(str).isin(included_ids)
    ].copy()
    if calculated.empty:
        return pd.DataFrame(columns=["activity_name", "tco2e"])
    calculated["tco2e"] = pd.to_numeric(
        calculated["calculated_tco2e"], errors="coerce"
    )
    calculated = calculated.dropna(subset=["tco2e"])
    # Blocked / supporting rows are never treated as zero contributions.
    grouped = (
        calculated.groupby("activity_name", dropna=False)["tco2e"]
        .sum()
        .reset_index()
    )
    grouped["tco2e"] = grouped["tco2e"].astype(float)
    return grouped.sort_values("tco2e", ascending=False).reset_index(drop=True)


def monthly_emissions_series(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Monthly time-series of company-inventory tCO2e (presentation only)."""
    activities = result.activity_records_accepted.copy()
    calcs = result.calculation_results.copy()
    if activities.empty or calcs.empty:
        return pd.DataFrame(columns=["month", "tco2e"])
    included_ids = company_inventory_record_ids(result)
    merged = activities.merge(
        calcs[["record_id", "calculation_status", "calculated_tco2e"]],
        on="record_id",
        how="left",
    )
    ready = merged[merged["record_id"].astype(str).isin(included_ids)].copy()
    if ready.empty:
        return pd.DataFrame(columns=["month", "tco2e"])
    ready["month_ts"] = pd.to_datetime(
        ready["activity_start_date"], errors="coerce"
    )
    ready = ready.dropna(subset=["month_ts"])
    ready["tco2e"] = pd.to_numeric(ready["calculated_tco2e"], errors="coerce")
    ready = ready.dropna(subset=["tco2e"])
    if ready.empty:
        return pd.DataFrame(columns=["month", "tco2e"])
    ready["month"] = ready["month_ts"].dt.to_period("M").astype(str)
    out = (
        ready.groupby("month", sort=True)["tco2e"]
        .sum()
        .reset_index()
    )
    out["tco2e"] = out["tco2e"].astype(float)
    return out


def emissions_source_rows(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (calculated contributions, blocked labels not shown as zero)."""
    contrib = calculated_emissions_contributions(result, lang)
    overview = build_activity_overview(result, lang)
    if overview.empty:
        return contrib, pd.DataFrame(columns=["activity_name", "status_label"])
    blocked = overview[
        ~overview["calculation_status"]
        .astype(str)
        .isin(["calculated", "not_emissions_activity"])
    ]
    if blocked.empty:
        return contrib, pd.DataFrame(columns=["activity_name", "status_label"])
    labels = (
        blocked.groupby("activity_name", dropna=False)["calculation_label"]
        .first()
        .reset_index()
        .rename(columns={"calculation_label": "status_label"})
    )
    return contrib, labels


def _donut_spec(height: int = CHART_HEIGHT_SMALL) -> dict[str, Any]:
    return {
        "height": height,
        "mark": {"type": "arc", "innerRadius": 52, "cornerRadius": 4},
        "encoding": {
            "theta": {"field": "count", "type": "quantitative", "stack": True},
            "color": {
                "field": "label",
                "type": "nominal",
                "legend": {
                    "title": None,
                    "labelColor": COLOR_SLATE,
                    "labelFontSize": 12,
                    "orient": "right",
                },
            },
            "tooltip": [
                {"field": "label", "type": "nominal"},
                {"field": "count", "type": "quantitative"},
            ],
        },
        "view": {"stroke": None},
        "config": {
            "axis": {"labelColor": COLOR_SLATE, "titleColor": COLOR_NAVY},
            "legend": {"labelColor": COLOR_SLATE},
        },
    }


def _horizontal_status_spec(height: int = CHART_HEIGHT_SMALL) -> dict[str, Any]:
    return {
        "height": min(height, CHART_HEIGHT_OVERVIEW),
        "mark": {"type": "bar", "cornerRadiusEnd": 4, "height": 18},
        "encoding": {
            "y": {
                "field": "activity_name",
                "type": "nominal",
                "sort": None,
                "axis": {
                    "title": None,
                    "labelColor": COLOR_NAVY,
                    "labelFontSize": 12,
                    "labelLimit": 160,
                },
            },
            "x": {
                "field": "rank",
                "type": "quantitative",
                "axis": None,
                "scale": {"domain": [0, 1]},
            },
            "color": {
                "field": "label",
                "type": "nominal",
                "legend": {
                    "title": None,
                    "labelColor": COLOR_SLATE,
                    "labelFontSize": 12,
                },
            },
            "tooltip": [
                {"field": "activity_name", "type": "nominal"},
                {"field": "label", "type": "nominal"},
            ],
        },
        "view": {"stroke": None},
        "config": {"view": {"stroke": None}},
    }


def _contribution_bar_spec(height: int = CHART_HEIGHT_COMPACT) -> dict[str, Any]:
    return {
        "height": height,
        # Extra right padding so end-of-bar value labels are not clipped.
        "padding": {"left": 4, "right": 64, "top": 4, "bottom": 4},
        "layer": [
            {
                "mark": {
                    "type": "bar",
                    "cornerRadiusEnd": 4,
                    "color": COLOR_CALCULATED,
                },
                "encoding": {
                    "y": {
                        "field": "activity_name",
                        "type": "nominal",
                        "sort": "-x",
                        "axis": {
                            "title": None,
                            "labelColor": COLOR_NAVY,
                            "labelFontSize": 12,
                            "labelLimit": 140,
                        },
                    },
                    "x": {
                        "field": "tco2e",
                        "type": "quantitative",
                        "axis": {
                            "title": "tCO₂e",
                            "titleColor": COLOR_SLATE,
                            "labelColor": COLOR_SLATE,
                            "labelFontSize": 11,
                            "grid": True,
                            "gridColor": "#E2E8F0",
                        },
                    },
                    "tooltip": [
                        {
                            "field": "activity_name",
                            "type": "nominal",
                            "title": "Source",
                        },
                        {
                            "field": "tco2e",
                            "type": "quantitative",
                            "title": "tCO₂e",
                            "format": ",.2f",
                        },
                    ],
                },
            },
            {
                "mark": {
                    "type": "text",
                    "align": "left",
                    "baseline": "middle",
                    "dx": 6,
                    "color": COLOR_SLATE,
                    "fontSize": 11,
                },
                "encoding": {
                    "y": {
                        "field": "activity_name",
                        "type": "nominal",
                        "sort": "-x",
                    },
                    "x": {"field": "tco2e", "type": "quantitative"},
                    "text": {
                        "field": "tco2e",
                        "type": "quantitative",
                        "format": ",.1f",
                    },
                },
            },
        ],
        "view": {"stroke": None},
    }


def _monthly_area_spec(height: int = CHART_HEIGHT_OVERVIEW) -> dict[str, Any]:
    return {
        "height": height,
        "mark": {
            "type": "area",
            "line": {"color": COLOR_CALCULATED},
            "color": {
                "x1": 1,
                "y1": 1,
                "x2": 1,
                "y2": 0,
                "gradient": "linear",
                "stops": [
                    {"offset": 0, "color": "rgba(20, 163, 154, 0.35)"},
                    {"offset": 1, "color": "rgba(20, 163, 154, 0.02)"},
                ],
            },
        },
        "encoding": {
            "x": {
                "field": "month",
                "type": "ordinal",
                "axis": {
                    "title": None,
                    "labelColor": COLOR_SLATE,
                    "labelFontSize": 11,
                    "labelAngle": 0,
                },
            },
            "y": {
                "field": "tco2e",
                "type": "quantitative",
                "axis": {
                    "title": "tCO₂e",
                    "titleColor": COLOR_SLATE,
                    "labelColor": COLOR_SLATE,
                    "labelFontSize": 11,
                    "grid": True,
                    "gridColor": "#E2E8F0",
                },
            },
            "tooltip": [
                {"field": "month", "type": "ordinal", "title": "Period"},
                {
                    "field": "tco2e",
                    "type": "quantitative",
                    "title": "tCO₂e",
                    "format": ",.1f",
                },
            ],
        },
        "view": {"stroke": None},
    }


def _gap_bar_spec(height: int = CHART_HEIGHT_SMALL) -> dict[str, Any]:
    return {
        "height": height,
        "mark": {"type": "bar", "cornerRadiusEnd": 4},
        "encoding": {
            "y": {
                "field": "label",
                "type": "nominal",
                "sort": "-x",
                "axis": {
                    "title": None,
                    "labelColor": COLOR_NAVY,
                    "labelFontSize": 12,
                },
            },
            "x": {
                "field": "count",
                "type": "quantitative",
                "axis": {
                    "title": None,
                    "labelColor": COLOR_SLATE,
                    "tickMinStep": 1,
                    "grid": False,
                },
            },
            "color": {
                "field": "label",
                "type": "nominal",
                "legend": None,
            },
            "tooltip": [
                {"field": "label", "type": "nominal"},
                {"field": "count", "type": "quantitative"},
            ],
        },
        "view": {"stroke": None},
    }


def ghg_scope_classification_counts(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Count GHG activity classifications (not emissions share)."""
    if not result.include_ghg:
        return pd.DataFrame(columns=["label", "count", "color"])
    overview = build_activity_overview(result, lang)
    if overview.empty:
        return pd.DataFrame(columns=["label", "count", "color"])
    counts = overview["ghg_label"].value_counts()
    color_map = {
        t("ghg.scope_1", lang): COLOR_SCOPE_1,
        t("ghg.scope_2", lang): COLOR_SCOPE_2,
        t("ghg.scope_3", lang): COLOR_SCOPE_3,
        t("ghg.scope_3_cat1", lang): COLOR_SCOPE_3,
        t("status.not_applicable", lang): COLOR_SUPPORTING,
        t("common.not_run", lang): COLOR_SUPPORTING,
    }
    rows = [
        {
            "label": str(label),
            "count": int(count),
            "color": color_map.get(str(label), COLOR_SUPPORTING),
        }
        for label, count in counts.items()
    ]
    return pd.DataFrame(rows)


def cbam_role_distribution(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Count CBAM data-role labels from current evaluations."""
    if not result.include_cbam:
        return pd.DataFrame(columns=["label", "count"])
    overview = build_activity_overview(result, lang)
    if overview.empty:
        return pd.DataFrame(columns=["label", "count"])
    counts = overview["cbam_label"].value_counts()
    return pd.DataFrame(
        [{"label": str(label), "count": int(count)} for label, count in counts.items()]
    )


def ifrs_readiness_distribution(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Count IFRS S2 readiness labels from current evaluations."""
    if not result.include_ifrs_s2:
        return pd.DataFrame(columns=["label", "count"])
    overview = build_activity_overview(result, lang)
    if overview.empty:
        return pd.DataFrame(columns=["label", "count"])
    counts = overview["ifrs_s2_label"].value_counts()
    return pd.DataFrame(
        [{"label": str(label), "count": int(count)} for label, count in counts.items()]
    )


def issue_gap_type_counts(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Count open QA issues by gap type (not severity when uniform)."""
    issues = _copy_frame(result.core_qa_issues)
    if issues.empty or "source_status" not in issues.columns:
        return pd.DataFrame(columns=["status_code", "label", "count", "color"])
    rows: list[dict[str, Any]] = []
    for code, group in issues.groupby(issues["source_status"].astype(str)):
        label_key = ISSUE_GAP_LABEL_KEYS.get(code)
        label = t(label_key, lang) if label_key else calculation_label(code, lang)
        rows.append(
            {
                "status_code": code,
                "label": label,
                "count": int(len(group)),
                "color": ISSUE_GAP_COLORS.get(code, COLOR_SUPPORTING),
            }
        )
    return pd.DataFrame(rows).sort_values("count", ascending=False).reset_index(
        drop=True
    )


def _role_bar_spec(height: int = 200) -> dict[str, Any]:
    return {
        "height": height,
        "mark": {"type": "bar", "cornerRadiusEnd": 4, "color": COLOR_INFO},
        "encoding": {
            "y": {
                "field": "label",
                "type": "nominal",
                "sort": "-x",
                "axis": {
                    "title": None,
                    "labelColor": COLOR_NAVY,
                    "labelFontSize": 12,
                    "labelLimit": 180,
                },
            },
            "x": {
                "field": "count",
                "type": "quantitative",
                "axis": {
                    "title": None,
                    "labelColor": COLOR_SLATE,
                    "tickMinStep": 1,
                    "grid": False,
                },
            },
            "tooltip": [
                {"field": "label", "type": "nominal"},
                {"field": "count", "type": "quantitative"},
            ],
        },
        "view": {"stroke": None},
    }


def _render_vega(data: pd.DataFrame, spec: dict[str, Any]) -> None:
    """Render a Vega-Lite chart without dumping the spec into markdown."""
    if data.empty:
        return
    # Streamlit accepts a DataFrame plus a spec dict; never print the dict.
    chart_data = data.copy()
    st.vega_lite_chart(chart_data, spec=spec, use_container_width=True)


def render_calculation_status_donut(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
    *,
    height: int = CHART_HEIGHT_SMALL,
) -> pd.DataFrame:
    """Dashboard donut: calculation-status counts."""
    frame = calculation_status_distribution(result, lang)
    st.markdown(f"**{t('chart.calc_status.title', lang)}**")
    activity_count = int(frame["count"].sum()) if not frame.empty else 0
    st.caption(t("chart.calc_status.help", lang, n=activity_count))
    if frame.empty:
        return frame
    # Vega-Lite color from column requires domain/range lists for reliability.
    spec = _donut_spec(height=height)
    spec["encoding"]["color"]["scale"] = {
        "domain": frame["label"].tolist(),
        "range": frame["color"].tolist(),
    }
    _render_vega(frame[["label", "count"]], spec)
    return frame


def render_activity_status_bars(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Dashboard horizontal status bars per activity (capped height)."""
    frame = activity_status_breakdown(result, lang)
    st.markdown(f"**{t('chart.activity_status.title', lang)}**")
    st.caption(t("chart.activity_status.help", lang))
    if frame.empty:
        return frame
    # Cap to a sample of rows so the chart never fills the viewport.
    display = frame.head(12).copy()
    legend_order = display.drop_duplicates("label")
    height = min(CHART_HEIGHT_OVERVIEW, max(CHART_HEIGHT_SMALL, 28 * len(display) + 40))
    spec = _horizontal_status_spec(height=height)
    spec["encoding"]["color"]["scale"] = {
        "domain": legend_order["label"].tolist(),
        "range": legend_order["color"].tolist(),
    }
    _render_vega(display, spec)
    return frame


def render_emissions_contribution_bars(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Compact contribution bars for calculated activities only."""
    frame = calculated_emissions_contributions(result, lang)
    st.caption(t("chart.emissions_contrib.help", lang))
    if frame.empty:
        st.caption(t("chart.emissions_contrib.empty", lang))
        return frame
    # Single-category charts stay compact; never explode to full viewport.
    n = max(1, len(frame))
    height = min(
        CHART_HEIGHT_OVERVIEW,
        max(CHART_HEIGHT_COMPACT, min(40 * n + 36, CHART_HEIGHT_OVERVIEW)),
    )
    if n == 1:
        height = CHART_HEIGHT_COMPACT
    _render_vega(frame, _contribution_bar_spec(height=height))
    return frame


def render_monthly_emissions_trend(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Bounded monthly emissions area chart."""
    frame = monthly_emissions_series(result, lang)
    if frame.empty:
        st.caption(t("chart.trend.empty", lang))
        return frame
    _render_vega(frame, _monthly_area_spec(height=CHART_HEIGHT_OVERVIEW))
    return frame


def render_emissions_source_bars(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Horizontal emissions-by-source chart; blocked rows excluded (not zero)."""
    contrib, blocked = emissions_source_rows(result, lang)
    if contrib.empty:
        st.caption(t("chart.emissions_contrib.empty", lang))
    else:
        n = max(1, len(contrib))
        height = (
            CHART_HEIGHT_COMPACT
            if n == 1
            else min(CHART_HEIGHT_OVERVIEW, max(CHART_HEIGHT_COMPACT, 36 * n + 40))
        )
        _render_vega(contrib, _contribution_bar_spec(height=height))
    if not blocked.empty:
        names = "、".join(blocked["activity_name"].astype(str).head(4).tolist())
        st.caption(
            f"{t('chart.source.not_calculated', lang)}：{names}"
        )
    return contrib


def render_ghg_scope_donut(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Frameworks GHG: activity classification counts (not emissions)."""
    frame = ghg_scope_classification_counts(result, lang)
    st.markdown(f"**{t('chart.ghg_scope.title', lang)}**")
    st.caption(t("chart.ghg_scope.help", lang))
    if frame.empty:
        return frame
    spec = _donut_spec(height=250)
    spec["encoding"]["color"]["scale"] = {
        "domain": frame["label"].tolist(),
        "range": frame["color"].tolist(),
    }
    _render_vega(frame[["label", "count"]], spec)
    return frame


def render_cbam_role_bars(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Compact CBAM role counts."""
    frame = cbam_role_distribution(result, lang)
    st.markdown(f"**{t('chart.cbam_roles.title', lang)}**")
    st.caption(t("chart.cbam_roles.help", lang))
    if frame.empty:
        return frame
    _render_vega(frame, _role_bar_spec(height=max(160, 32 * len(frame) + 40)))
    return frame


def render_ifrs_readiness_bars(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Compact IFRS S2 readiness counts (no percentage score)."""
    frame = ifrs_readiness_distribution(result, lang)
    st.markdown(f"**{t('chart.ifrs_ready.title', lang)}**")
    st.caption(t("chart.ifrs_ready.help", lang))
    if frame.empty:
        return frame
    _render_vega(frame, _role_bar_spec(height=max(140, 32 * len(frame) + 40)))
    return frame


def render_issue_gap_bars(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame | None:
    """Issues page gap-type bars; skip when no meaningful variation."""
    frame = issue_gap_type_counts(result, lang)
    if frame.empty:
        return None
    # Skip a chart that would show a single uniform severity pie; gap types
    # are useful when at least one category exists.
    st.markdown(f"**{t('chart.issue_gaps.title', lang)}**")
    st.caption(t("chart.issue_gaps.help", lang))
    spec = _gap_bar_spec(height=max(140, 36 * len(frame) + 40))
    spec["encoding"]["color"]["scale"] = {
        "domain": frame["label"].tolist(),
        "range": frame["color"].tolist(),
    }
    _render_vega(frame[["label", "count"]], spec)
    return frame


def status_kind_for_calculation(code: str) -> str:
    """Map calculation status codes to shared badge kinds."""
    mapping = {
        "calculated": "success",
        "blocked_missing_conversion": "warning",
        "blocked_natural_gas_type_required": "warning",
        "no_factor_configured": "attention",
        "no_matching_factor": "attention",
        "not_emissions_activity": "muted",
    }
    return mapping.get(code, "muted")

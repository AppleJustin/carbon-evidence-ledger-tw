"""Activity Explorer — three information layers (operational / basis / audit)."""

from __future__ import annotations

import json

import streamlit as st

from carbon_ledger.ui.charts import status_kind_for_calculation
from carbon_ledger.ui.components import (
    inject_design_system,
    render_empty_state,
    render_page_header,
    render_page_help,
    render_section_header,
    render_status_badge,
)
from carbon_ledger.ui.i18n import t
from carbon_ledger.ui.state import (
    get_current_result,
    get_focus_record,
    get_language,
    is_uploaded_analysis,
)
from carbon_ledger.ui.view_models import (
    activity_detail_context,
    build_activity_overview,
    calculation_label,
    factor_registry_row,
)

inject_design_system()
lang = get_language(st.session_state)
result = get_current_result(st.session_state)

render_page_header(t("ev.title", lang), t("ev.subtitle", lang))
render_section_header(t("act.title", lang), t("act.subtitle", lang))
render_page_help(t("act.help", lang))

if result is None:
    render_empty_state(
        t("empty.no_analysis_title", lang),
        t("empty.no_analysis_body", lang),
    )
    st.stop()

overview = build_activity_overview(result, lang)
if overview.empty:
    render_empty_state(t("act.title", lang), t("act.select_hint", lang))
    st.stop()

st.info(t("act.select_hint", lang))

filter_cols = st.columns([2, 1.2, 1.4, 1.2])
with filter_cols[0]:
    search = st.text_input(t("act.filter_search", lang), value="")
with filter_cols[1]:
    type_options = [t("act.filter_all", lang)] + sorted(
        overview["activity_name"].dropna().unique().tolist()
    )
    selected_type = st.selectbox(t("act.filter_type", lang), type_options)
with filter_cols[2]:
    status_options = [t("act.filter_all", lang)] + sorted(
        overview["calculation_label"].dropna().unique().tolist()
    )
    selected_status = st.selectbox(t("act.filter_status", lang), status_options)
with filter_cols[3]:
    attention_filter = st.selectbox(
        t("act.filter_attention", lang),
        [
            t("act.filter_all", lang),
            t("act.filter_yes", lang),
            t("act.filter_no", lang),
        ],
    )

filtered = overview.copy()
all_label = t("act.filter_all", lang)
if search.strip():
    needle = search.strip().lower()
    filtered = filtered[
        filtered["activity_name"].str.lower().str.contains(needle, na=False)
        | filtered["activity_type"].str.lower().str.contains(needle, na=False)
    ]
if selected_type != all_label:
    filtered = filtered[filtered["activity_name"] == selected_type]
if selected_status != all_label:
    filtered = filtered[filtered["calculation_label"] == selected_status]
if attention_filter == t("act.filter_yes", lang):
    filtered = filtered[filtered["attention_required"]]
elif attention_filter == t("act.filter_no", lang):
    filtered = filtered[~filtered["attention_required"]]

if filtered.empty:
    render_empty_state(t("act.title", lang), t("act.select_hint", lang))
    st.stop()

# Layer 1 — customer/operational default (record_id kept off-display for selection)
display = filtered[
    [
        "activity_name",
        "activity_amount",
        "activity_unit",
        "calculation_label",
        "ghg_label",
        "ifrs_s2_label",
        "attention_required",
    ]
].rename(
    columns={
        "activity_name": t("dash.col.activity", lang),
        "activity_amount": t("dash.col.amount", lang),
        "activity_unit": t("act.col.unit", lang),
        "calculation_label": t("dash.col.calc", lang),
        "ghg_label": t("dash.col.ghg", lang),
        "ifrs_s2_label": t("dash.col.ifrs", lang),
        "attention_required": t("act.filter_attention", lang),
    }
)

event = st.dataframe(
    display,
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
    key="activity_explorer_table",
)

focus = get_focus_record(st.session_state)
selected_rows = []
if event is not None and getattr(event, "selection", None) is not None:
    selected_rows = list(event.selection.rows)

record_ids = filtered["record_id"].astype(str).tolist()
if selected_rows:
    selected_record_id = record_ids[selected_rows[0]]
elif focus and focus in set(record_ids):
    selected_record_id = focus
else:
    selected_record_id = record_ids[0]

detail = activity_detail_context(result, selected_record_id, lang)
if not detail:
    render_empty_state(t("act.title", lang), t("act.select_hint", lang))
    st.stop()

overview_row = detail["overview"]
calc = detail["calculation"]
activity = detail["activity"]
calc_status = str(overview_row.get("calculation_status", ""))

st.write("")
render_section_header(t("act.status_strip", lang))
strip = st.columns(4)
with strip[0]:
    st.caption(t("dash.col.calc", lang))
    render_status_badge(
        str(overview_row.get("calculation_label", "—")),
        kind=status_kind_for_calculation(calc_status),
    )
with strip[1]:
    st.caption("GHG")
    render_status_badge(str(overview_row.get("ghg_label", "—")), kind="info")
with strip[2]:
    st.caption("IFRS S2")
    render_status_badge(str(overview_row.get("ifrs_s2_label", "—")), kind="muted")
with strip[3]:
    st.caption(t("dash.col.qa", lang))
    qa_label = str(overview_row.get("qa_label", "—"))
    qa_kind = (
        "warning"
        if (
            "高" in qa_label
            or "High" in qa_label
            or "Critical" in qa_label
            or "重大" in qa_label
        )
        else "success"
    )
    render_status_badge(qa_label, kind=qa_kind)

# Layer 1 detail summary
st.write("")
render_section_header(t("act.layer.operational", lang))
summary_cols = st.columns(3)
with summary_cols[0]:
    st.markdown(f"**{t('dash.col.activity', lang)}**")
    st.write(overview_row.get("activity_name", "—"))
    st.markdown(f"**{t('dash.col.amount', lang)}**")
    st.write(
        f"{overview_row.get('activity_amount', '—')} "
        f"{overview_row.get('activity_unit', '')}"
    )
    if str(activity.get("activity_type") or "") == "refrigerant_refill":
        st.markdown(f"**{t('act.basis.refrigerant_code', lang)}**")
        st.write(
            str(
                overview_row.get("refrigerant_code")
                or activity.get("refrigerant_code")
                or calc.get("refrigerant_code")
                or "—"
            )
        )
with summary_cols[1]:
    st.markdown(f"**{t('act.col.period', lang)}**")
    st.write(
        f"{activity.get('activity_start_date', '—')} → "
        f"{activity.get('activity_end_date', '—')}"
    )
    st.markdown(f"**{t('dash.col.calc', lang)}**")
    render_status_badge(
        str(overview_row.get("calculation_label", "—")),
        kind=status_kind_for_calculation(calc_status),
    )
with summary_cols[2]:
    if calc_status == "calculated" and overview_row.get("calculated_tco2e") is not None:
        st.markdown(f"**{t('dash.col.emissions', lang)}**")
        st.write(f"{float(overview_row['calculated_tco2e']):.6g} tCO₂e")
    else:
        st.markdown(t("act.no_zero", lang))
        st.caption(detail["calculation_next_action"])
    docs = result.source_documents_accepted
    doc_id = str(activity.get("source_document_id") or "")
    doc_name = "—"
    if not docs.empty and doc_id:
        match = docs[docs["source_document_id"].astype(str) == doc_id]
        if not match.empty:
            doc_name = str(match.iloc[0].get("file_name") or "—")
    st.markdown(f"**{t('act.col.source_doc', lang)}**")
    st.write(doc_name)

# Layer 2 — calculation basis (business names, not raw IDs)
with st.expander(t("act.layer.basis", lang), expanded=False):
    st.markdown(f"**{t('dash.col.calc', lang)}:** {detail['calculation_label']}")
    if calc_status == "calculated":
        amount = overview_row.get("activity_amount")
        unit = overview_row.get("activity_unit") or ""
        factor_value = calc.get("factor_value")
        kg = calc.get("calculated_kgco2e")
        tco2e = calc.get("calculated_tco2e")
        registry = factor_registry_row(str(calc.get("factor_id") or "")) or {}
        factor_year = registry.get("factor_year") or "—"
        factor_desc = (
            registry.get("factor_name")
            or registry.get("description")
            or registry.get("source_name")
            or t("act.trace_factor", lang)
        )
        activity_type = str(activity.get("activity_type") or "")
        is_combustion = activity_type in {"natural_gas", "diesel"}
        is_refrigerant = activity_type == "refrigerant_refill"
        trace: dict = {}
        raw_trace = calc.get("calculation_trace")
        if isinstance(raw_trace, dict):
            trace = raw_trace
        elif raw_trace not in (None, "", "nan"):
            try:
                parsed = json.loads(str(raw_trace))
                if isinstance(parsed, dict):
                    trace = parsed
            except (TypeError, ValueError, json.JSONDecodeError):
                trace = {}
        st.markdown(f"**{t('act.basis.quantity', lang)}**")
        st.write(f"{amount} {unit}" if amount is not None else "—")
        if is_combustion:
            if activity_type == "natural_gas":
                st.markdown(f"**{t('act.basis.ng_type', lang)}**")
                st.write(str(activity.get("fuel_subtype") or "—"))
            else:
                st.markdown(f"**{t('act.basis.diesel_use', lang)}**")
                diesel_use = str(activity.get("process_use") or "")
                st.write(
                    t("intake.diesel_company_vehicle", lang)
                    if diesel_use == "company_vehicle"
                    else t("intake.ng_type_unknown", lang)
                )
            heating_value = calc.get("heating_value")
            heating_unit = calc.get("heating_value_unit") or ""
            hv_trace = trace.get("heating_value") or {}
            if isinstance(hv_trace, dict) and not heating_value:
                heating_value = hv_trace.get("value")
                heating_unit = hv_trace.get("unit") or heating_unit
            st.markdown(f"**{t('act.basis.heating_value', lang)}**")
            if heating_value is not None and str(heating_value) not in {
                "",
                "nan",
            }:
                st.write(f"{float(heating_value):,.6g} {heating_unit}".strip())
            else:
                st.write("—")
            energy_tj = calc.get("energy_tj")
            energy_trace = trace.get("energy") or {}
            if (
                isinstance(energy_trace, dict)
                and energy_tj in (None, "", "nan")
            ):
                energy_tj = energy_trace.get("tj")
            st.markdown(f"**{t('act.basis.energy', lang)}**")
            if energy_tj is not None and str(energy_tj) not in {"", "nan"}:
                st.write(f"{float(energy_tj):.6g} TJ")
            else:
                st.write("—")
            gases = trace.get("gases") if isinstance(trace.get("gases"), dict) else {}
            st.markdown(f"**{t('act.basis.gas_factors', lang)}**")
            gas_bits = []
            for gas_name in ("CO2", "CH4", "N2O"):
                gas_row = gases.get(gas_name) if isinstance(gases, dict) else None
                factor_val = ""
                if isinstance(gas_row, dict):
                    factor_val = str(gas_row.get("factor_value") or "")
                gas_bits.append(
                    f"{gas_name} {factor_val}".strip() if factor_val else gas_name
                )
            st.write(" · ".join(gas_bits) if gas_bits else "—")
            st.markdown(f"**{t('act.basis.gwp', lang)}**")
            st.write(
                f"CO2 {calc.get('co2_gwp') or '—'} · "
                f"CH4 {calc.get('ch4_gwp') or '—'} · "
                f"N2O {calc.get('n2o_gwp') or '—'}"
            )
            st.markdown(f"**{t('act.basis.result', lang)}**")
            st.write(
                f"{float(tco2e):.6g} tCO₂e" if tco2e is not None else "—"
            )
            st.markdown(f"**{t('act.basis.source', lang)}**")
            hv_source = calc.get("heating_value_source_reference_id")
            gwp_source = calc.get("gwp_source_reference_id")
            factor_source = (
                calc.get("source_reference_id")
                or registry.get("source_reference_id")
            )
            st.write(
                " · ".join(
                    str(item)
                    for item in (hv_source, factor_source, gwp_source)
                    if item not in (None, "", "nan")
                )
                or t("act.trace_source_official", lang)
            )
        elif is_refrigerant:
            st.markdown(f"**{t('act.basis.refrigerant_code', lang)}**")
            st.write(
                str(
                    activity.get("refrigerant_code")
                    or calc.get("refrigerant_code")
                    or "—"
                )
            )
            st.markdown(f"**{t('act.basis.refill_quantity', lang)}**")
            st.write(f"{amount} {unit}" if amount is not None else "—")
            st.markdown(f"**{t('act.basis.gwp', lang)}**")
            gwp_value = calc.get("gwp_value")
            if gwp_value in (None, "", "nan"):
                gwp_value = factor_value
            gwp_id = calc.get("gwp_id") or calc.get("factor_id") or ""
            if gwp_value not in (None, "", "nan"):
                label = f"{float(gwp_value):.6g}"
                if gwp_id not in (None, "", "nan"):
                    label = f"{label} ({gwp_id})"
                st.write(label)
            else:
                st.write("—")
            st.markdown(f"**{t('act.basis.result', lang)}**")
            st.write(
                f"{float(tco2e):.6g} tCO₂e" if tco2e is not None else "—"
            )
            st.markdown(f"**{t('act.basis.source', lang)}**")
            source_bits = [
                calc.get("formula_id"),
                calc.get("formula_version"),
                calc.get("gwp_source_reference_id") or calc.get("source_reference_id"),
            ]
            st.write(
                " · ".join(
                    str(item)
                    for item in source_bits
                    if item not in (None, "", "nan")
                )
                or t("act.trace_source_official", lang)
            )
            raw_trace = calc.get("calculation_trace")
            if raw_trace not in (None, "", "nan"):
                st.caption(str(raw_trace))
        else:
            st.markdown(f"**{t('act.trace_activity', lang)}**")
            st.write(f"{amount} {unit}" if amount is not None else "—")
            if calc.get("normalized_value") not in (None, "", "nan"):
                st.markdown(f"**{t('act.trace_normalized', lang)}**")
                st.write(
                    f"{calc.get('normalized_value')} "
                    f"{calc.get('normalized_unit') or ''}".strip()
                )
            st.markdown(f"**{t('act.trace_factor', lang)}**")
            st.write(str(factor_desc))
            if factor_value is not None and str(factor_value) not in {"", "nan"}:
                st.write(f"{float(factor_value):.6g} kgCO2e/{unit or 'unit'}")
            st.markdown(f"**{t('act.trace_factor_year', lang)}**")
            st.write(factor_year)
            authority = registry.get("issuing_authority") or registry.get(
                "authority"
            )
            if authority:
                st.markdown(f"**{t('act.trace_authority', lang)}**")
                st.write(str(authority))
            st.markdown(f"**{t('act.trace_calc', lang)}**")
            if (
                amount is not None
                and factor_value is not None
                and kg is not None
                and tco2e is not None
            ):
                st.write(
                    f"{float(amount):,.6g} × {float(factor_value):.6g}\n\n"
                    f"= {float(kg):,.6g} kgCO2e\n\n"
                    f"= {float(tco2e):.6g} tCO2e"
                )
            else:
                st.write(
                    f"{float(tco2e):.6g} tCO₂e" if tco2e is not None else "—"
                )
        source_key = (
            "act.trace_source_official"
            if is_uploaded_analysis(st.session_state)
            else "act.trace_source_demo"
        )
        st.caption(f"{t('act.trace_source', lang)}：{t(source_key, lang)}")
    else:
        st.markdown(t("act.no_zero", lang))
        st.warning(t("act.why_blocked", lang))
        st.write(detail["calculation_explanation"])
        st.info(t("act.what_next", lang))
        st.write(detail["calculation_next_action"])

# Layer 3 — audit trace (raw IDs only when expanded)
with st.expander(t("act.layer.audit", lang), expanded=False):
    st.write(
        {
            "record_id": overview_row.get("record_id"),
            "source_document_id": activity.get("source_document_id"),
            "source_locator": activity.get("source_locator"),
            "measurement_method": activity.get("measurement_method"),
            "data_quality_tier": activity.get("data_quality_tier"),
            "calculation_status": overview_row.get("calculation_status"),
            "calculation_label": calculation_label(
                str(overview_row.get("calculation_status", "")), lang
            ),
            "calculation_id": calc.get("calculation_id"),
            "factor_id": calc.get("factor_id"),
            "gwp_id": calc.get("gwp_id"),
            "formula_id": calc.get("formula_id"),
            "formula_version": calc.get("formula_version"),
            "refrigerant_code": calc.get("refrigerant_code")
            or activity.get("refrigerant_code"),
            "normalized_value": calc.get("normalized_value"),
            "normalized_unit": calc.get("normalized_unit"),
            "evaluation_id_ghg": detail["ghg"].get("evaluation_id"),
            "rule_id_ghg": detail["ghg"].get("rule_id"),
            "reference_id_ghg": detail["ghg"].get("reference_id"),
            "evaluation_id_ifrs": detail["ifrs_s2"].get("evaluation_id"),
            "rule_id_ifrs": detail["ifrs_s2"].get("rule_id"),
            "calculation_trace": calc.get("calculation_trace"),
        }
    )

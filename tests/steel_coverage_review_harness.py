"""Streamlit harness that renders the purchased-steel coverage review."""

from __future__ import annotations

import streamlit as st

from carbon_ledger.ui.purchased_steel_confirmation import (
    render_purchased_steel_coverage_review,
)
from carbon_ledger.ui.state import initialize_ui_state

initialize_ui_state(st.session_state)
accepted = st.session_state.get("steel_review_accepted")
if accepted is None:
    st.stop()
render_purchased_steel_coverage_review(
    accepted,
    str(st.session_state.get("steel_review_lang") or "zh-TW"),
    calculation_status_by_record=st.session_state.get("steel_review_status")
    or {},
    pipeline_result=st.session_state.get("steel_review_result"),
)

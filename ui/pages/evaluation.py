"""Evaluation Suite -- 6 required scenarios + aggregate metrics, unchanged from the base spec."""
import streamlit as st


def render():
    st.markdown('<div class="aegis-header">🧪 Evaluation Suite</div>', unsafe_allow_html=True)
    st.caption("Runs 6 required scenarios end-to-end through the LangGraph workflow, plus aggregate metrics.")
    if st.button("▶ Run Evaluation Suite"):
        from tests.eval_suite import run_all
        with st.spinner("Running scenarios..."):
            out = run_all()
        for r in out["results"]:
            status = "✅ PASS" if r.get("passed") else "❌ FAIL"
            with st.expander(f"{status} — Scenario {r['id']} [{r['layer']}]: {r['query']}"):
                st.write(r.get("description"))
                st.json(r)
        st.subheader("Aggregate Metrics")
        st.json(out["metrics"])

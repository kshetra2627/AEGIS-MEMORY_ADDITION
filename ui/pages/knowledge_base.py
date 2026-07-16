"""Knowledge Base -- corpus management: stats, document table, upload, rebuild."""
import os
import streamlit as st
from ui.components import metric_card, data_table, empty_state, load_with_skeleton
from ui.insights import get_indexed_policy_stats
from rag.ingest import ingest_all, corpus_is_empty, list_indexed_documents, POLICIES_DIR
from ui.insights import load_audit_df
from ui.graph import build_knowledge_graph


def _folder_size(path: str) -> str:
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    for unit in ["B", "KB", "MB", "GB"]:
        if total < 1024:
            return f"{total:.1f} {unit}"
        total /= 1024
    return f"{total:.1f} TB"


def render():
    st.markdown('<div class="aegis-header">📁 Knowledge Base</div>', unsafe_allow_html=True)
    st.markdown('<div class="aegis-subtitle">Manage the compliance corpus that grounds every Aegis advisory.</div>', unsafe_allow_html=True)

    if corpus_is_empty():
        st.warning("No documents found in data/policies/. Add files there or upload below, then click Rebuild Index.")

    stats = load_with_skeleton(get_indexed_policy_stats, n=1)
    if stats is None:
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("📄", stats["documents"], "Indexed Documents", animate=True)
    with c2:
        metric_card("🧩", stats["chunks"], "Total Chunks", animate=True)
    with c3:
        metric_card("🧬", os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"), "Embedding Model")
    with c4:
        chroma_path = os.path.join("database", "chroma")
        size = _folder_size(chroma_path) if os.path.isdir(chroma_path) else "0 B"
        metric_card("💾", size, "Storage Used")

    st.markdown('<div class="section-title">Actions</div>', unsafe_allow_html=True)
    a1, a2, a3 = st.columns(3)
    with a1:
        uploaded = st.file_uploader("Upload policy document", type=["pdf", "docx", "txt"], label_visibility="collapsed")
        if uploaded is not None:
            dest = os.path.join(POLICIES_DIR, uploaded.name)
            os.makedirs(POLICIES_DIR, exist_ok=True)
            with open(dest, "wb") as f:
                f.write(uploaded.getbuffer())
            st.success(f"Saved {uploaded.name}. Click Rebuild Index to ingest.")
    with a2:
        if st.button("🔄 Rebuild Index", use_container_width=True):
            with st.spinner("Clearing collection, rescanning corpus, regenerating embeddings..."):
                summary = ingest_all(force_rebuild=True)
            st.success(f"Rebuilt: {len(summary['ingested'])} ingested, {len(summary['skipped_duplicate'])} duplicates skipped, {summary['chunks_added']} chunks added.")
            st.rerun()
    with a3:
        if st.button("🔍 Rescan (no rebuild)", use_container_width=True):
            with st.spinner("Scanning for new/changed documents..."):
                summary = ingest_all(force_rebuild=False)
            st.success(f"{len(summary['ingested'])} new file(s) ingested, {summary['chunks_added']} chunks added.")
            st.rerun()

    st.markdown('<div class="section-title">Indexed Documents</div>', unsafe_allow_html=True)
    docs = load_with_skeleton(list_indexed_documents, n=3)
    if docs is None:
        return
    if not docs:
        empty_state("No documents indexed yet.")
        return

    data_table(docs, columns=["filename", "pages", "chunks", "date_indexed", "status", "hash"])

    for d in docs:
        with st.expander(f"👁 Preview — {d['filename']}"):
            st.write(f"**Status:** {d['status']}")
            st.write(f"**Pages:** {d['pages']} · **Chunks:** {d['chunks']}")
            st.write(f"**Hash:** {d['hash']}")
            path = os.path.join(POLICIES_DIR, d["filename"])
            if os.path.exists(path):
                st.download_button("⬇ Download original file", data=open(path, "rb").read(), file_name=d["filename"], key=f"dl_{d['filename']}")
            if st.button("🗑 Delete", key=f"del_{d['filename']}"):
                try:
                    os.remove(path)
                    st.info(f"Deleted {d['filename']} from disk. Click Rebuild Index to remove it from the vector store.")
                except OSError as e:
                    st.error(f"Could not delete: {e}")

    with st.expander("🕸️ Knowledge Graph View — Topics → Owners → Documents"):
        df = load_audit_df()
        fig = build_knowledge_graph(df, [d["filename"] for d in docs])
        st.plotly_chart(fig, use_container_width=True)

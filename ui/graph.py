"""Knowledge Graph View: topics -> owners -> documents, derived from the real
owner-mapping table and actual retrieval history in the audit log (never hardcoded)."""
import math
import plotly.graph_objects as go
from agents.router import OWNER_MAP


def build_knowledge_graph(df, indexed_documents: list[str]):
    topics = sorted(OWNER_MAP.keys())
    owners = sorted(set(OWNER_MAP.values()))

    doc_topic_votes: dict[str, dict[str, int]] = {}
    if df is not None and not df.empty:
        for _, row in df.iterrows():
            topic = row.get("topic")
            for doc in row.get("retrieved_documents") or []:
                doc_topic_votes.setdefault(doc, {})
                doc_topic_votes[doc][topic] = doc_topic_votes[doc].get(topic, 0) + 1

    doc_topic = {doc: max(votes, key=votes.get) for doc, votes in doc_topic_votes.items()}
    for doc in indexed_documents:
        doc_topic.setdefault(doc, "Unclassified")

    positions = {}
    for i, t in enumerate(topics):
        angle = 2 * math.pi * i / max(len(topics), 1)
        positions[("topic", t)] = (2 * math.cos(angle), 2 * math.sin(angle))
    for i, o in enumerate(owners):
        angle = 2 * math.pi * i / max(len(owners), 1)
        positions[("owner", o)] = (4.5 * math.cos(angle), 4.5 * math.sin(angle))
    for i, (d, t) in enumerate(doc_topic.items()):
        base = positions.get(("topic", t), (0, 0))
        angle = 2 * math.pi * i / max(len(doc_topic), 1)
        positions[("doc", d)] = (base[0] + 0.9 * math.cos(angle), base[1] + 0.9 * math.sin(angle))

    edge_x, edge_y = [], []
    for t, o in OWNER_MAP.items():
        x0, y0 = positions[("topic", t)]
        x1, y1 = positions[("owner", o)]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
    for d, t in doc_topic.items():
        x0, y0 = positions[("doc", d)]
        x1, y1 = positions.get(("topic", t), (0, 0))
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1, color="#232B3D"), hoverinfo="none"))

    for kind, color, size in [("topic", "#3B82F6", 22), ("owner", "#F59E0B", 18), ("doc", "#22C55E", 12)]:
        xs, ys, labels = [], [], []
        for (k, name), (x, y) in positions.items():
            if k == kind:
                xs.append(x); ys.append(y); labels.append(name)
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers+text", text=labels, textposition="top center",
                                  marker=dict(size=size, color=color), name=kind.capitalize()))

    fig.update_layout(
        showlegend=True, height=520, paper_bgcolor="#131A2A", plot_bgcolor="#131A2A", font_color="#E5E9F0",
        xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig

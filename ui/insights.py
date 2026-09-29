"""Dynamic AI Insights engine. Every number here is computed from the real
SQLite audit log, the live ChromaDB vector store, or on-disk corpus state --
nothing here is hardcoded or simulated. Used by the Dashboard, Compliance
Agent page, and the AI Insights panel alike.
"""
import os
import re
import json
from datetime import datetime, date, timedelta
import pandas as pd

from tools.audit_logger import fetch_all
from agents.governance_agent import REFUSAL_MESSAGE
from agents.router import OWNER_MAP

# audit_logger stores timestamps as datetime.utcnow().isoformat() (naive UTC). "Today" for the
# dashboard/insights must mean the user's local today, or records logged in the evening in a
# timezone ahead of UTC (e.g. IST, UTC+5:30) get silently excluded because their UTC date is
# still "yesterday". Shift stored UTC timestamps to local time once, at read time only --
# the stored/logged value itself is untouched.
_LOCAL_OFFSET = datetime.now() - datetime.utcnow()


def load_audit_df(user_id: str | None = None) -> pd.DataFrame:
    """Fetch this authenticated user's audit rows and parse JSON columns."""
    if user_id is None:
        from ui.auth import get_current_user
        current_user = get_current_user()
        user_id = current_user["user_id"] if current_user else None
    if user_id is None:
        return pd.DataFrame()
    rows = fetch_all(user_id=user_id)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    for col in ("retrieved_documents", "retrieved_chunks", "citations"):
        if col in df.columns:
            df[col] = df[col].apply(lambda v: _safe_json(v))
    df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce") + _LOCAL_OFFSET
    df["date"] = df["timestamp_dt"].dt.date
    return df


def _safe_json(v):
    try:
        return json.loads(v) if isinstance(v, str) else (v or [])
    except Exception:
        return []


# ---------------------------------------------------------------- System / corpus status
def get_system_health(df: pd.DataFrame) -> dict:
    try:
        from rag.vectorstore import get_vectorstore
        get_vectorstore()
        chroma_ok = True
    except Exception:
        chroma_ok = False

    if df.empty:
        return {"status": "online" if chroma_ok else "offline", "last_provider": "none"}

    last = df.sort_values("timestamp_dt").iloc[-1]
    last_provider = last.get("llm_provider", "none")
    if not chroma_ok:
        return {"status": "offline", "last_provider": last_provider}
    if last_provider == "none":
        return {"status": "degraded", "last_provider": last_provider}
    return {"status": "online", "last_provider": last_provider}


def get_indexed_policy_stats() -> dict:
    try:
        from rag.vectorstore import get_vectorstore
        vs = get_vectorstore()
        data = vs.get(include=["metadatas"])
        metas = data.get("metadatas", []) or []
        filenames = {m.get("filename") for m in metas if m.get("filename")}
        return {"documents": len(filenames), "chunks": len(metas)}
    except Exception:
        return {"documents": 0, "chunks": 0}


def get_latest_corpus_update() -> str:
    path = os.path.join("database", "ingested_hashes.json")
    if os.path.exists(path):
        return datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
    return "Never"


def get_compliance_owners() -> list[str]:
    return sorted(set(OWNER_MAP.values()) | {"Compliance Manager"})


# ---------------------------------------------------------------- Dashboard metrics
def today_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "queries_today": 0, "pending_reviews": 0, "avg_confidence": 0,
            "high_risk": 0, "governance_pass_rate": 100,
        }
    today = date.today()
    today_df = df[df["date"] == today]
    pending = int((df["approval_status"] == "Pending").sum())
    avg_conf = round(today_df["confidence"].mean(), 1) if not today_df.empty else 0
    high_risk = int((today_df["risk"] == "High").sum())
    if not today_df.empty:
        refused = today_df["answer"].fillna("").str.contains(re.escape(REFUSAL_MESSAGE[:40])).sum()
        pass_rate = round((1 - refused / len(today_df)) * 100, 1)
    else:
        pass_rate = 100
    return {
        "queries_today": len(today_df), "pending_reviews": pending, "avg_confidence": avg_conf,
        "high_risk": high_risk, "governance_pass_rate": pass_rate,
    }


# ---------------------------------------------------------------- AI Insights (dynamic summary lines)
def generate_ai_insights(df: pd.DataFrame) -> list[str]:
    insights = []
    if df.empty:
        return ["No activity yet — ask the Compliance Agent a question to start building insights."]

    now = pd.Timestamp.now()
    last_7 = df[df["timestamp_dt"] >= now - timedelta(days=7)]
    prev_7 = df[(df["timestamp_dt"] < now - timedelta(days=7)) & (df["timestamp_dt"] >= now - timedelta(days=14))]

    if not last_7.empty:
        top_topic = last_7["topic"].value_counts().idxmax()
        insights.append(f"Most asked topic this week: **{top_topic}** ({last_7['topic'].value_counts().max()} queries).")

        for topic in last_7["topic"].unique():
            cur = (last_7["topic"] == topic).sum()
            prev = (prev_7["topic"] == topic).sum() if not prev_7.empty else 0
            if prev > 0 and cur > prev:
                pct = round((cur - prev) / prev * 100)
                if pct >= 15:
                    insights.append(f"**{topic}** questions increased {pct}% vs. the prior week.")

    if not prev_7.empty and not last_7.empty:
        prev_conf = prev_7["confidence"].mean()
        cur_conf = last_7["confidence"].mean()
        if prev_conf and cur_conf:
            delta = round((cur_conf - prev_conf) / prev_conf * 100, 1)
            if abs(delta) >= 3:
                direction = "improved" if delta > 0 else "declined"
                insights.append(f"Average confidence {direction} {abs(delta)}% vs. the prior week.")

    pending = int((df["approval_status"] == "Pending").sum())
    if pending:
        insights.append(f"{pending} pending approval{'s' if pending != 1 else ''} require{'s' if pending == 1 else ''} review.")

    if not insights:
        insights.append("Activity is steady — no significant shifts detected this week.")
    return insights[:6]


# ---------------------------------------------------------------- Policy gap detection
def detect_policy_gaps(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    refused = df[df["answer"].fillna("").str.contains(re.escape(REFUSAL_MESSAGE[:40]))]
    refused = refused[refused["topic"] != "Out-of-Domain"]
    if refused.empty:
        return pd.DataFrame()
    gaps = refused.groupby("topic").size().reset_index(name="refused_count")
    return gaps[gaps["refused_count"] >= 1].sort_values("refused_count", ascending=False)


def repeated_questions(df: pd.DataFrame, min_count: int = 2) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    norm = df["question"].fillna("").str.lower().str.strip().str.replace(r"[^\w\s]", "", regex=True)
    counts = norm.value_counts()
    repeated = counts[counts >= min_count]
    if repeated.empty:
        return pd.DataFrame()
    return pd.DataFrame({"question": repeated.index, "count": repeated.values})


def recent_high_risk_repeat(df: pd.DataFrame, question: str, topic: str) -> bool:
    """Flags whether a similar high-risk question occurred recently (last 30 days)."""
    if df.empty:
        return False
    recent = df[df["timestamp_dt"] >= pd.Timestamp.now() - timedelta(days=30)]
    same_topic_high_risk = recent[(recent["topic"] == topic) & (recent["risk"] == "High")]
    return len(same_topic_high_risk) > 0


def most_cited_document(df: pd.DataFrame) -> str:
    if df.empty:
        return "N/A"
    counts = {}
    for docs in df["retrieved_documents"]:
        for d in docs or []:
            counts[d] = counts.get(d, 0) + 1
    if not counts:
        return "N/A"
    return max(counts, key=counts.get)


def low_confidence_queries(df: pd.DataFrame, threshold: float = 40) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    return df[df["confidence"] < threshold][["timestamp", "question", "confidence", "topic"]].sort_values("confidence")


def recent_activity_feed(df: pd.DataFrame, n: int = 10) -> list[dict]:
    if df.empty:
        return []
    recent = df.drop_duplicates(subset=["id"]).sort_values("timestamp_dt", ascending=False).head(n)
    feed = []
    for _, r in recent.iterrows():
        feed.append({
            "time": r["timestamp"], "question": r["question"], "topic": r["topic"],
            "risk": r["risk"], "escalated": bool(r["escalated"]), "approval_status": r["approval_status"],
        })
    return feed


def suggest_related_documents(topic: str, current_filenames: set[str]) -> list[str]:
    """Compliance Copilot: surfaces other indexed documents not already cited, as topic-adjacent reading."""
    stats = get_indexed_policy_stats()
    if stats["documents"] == 0:
        return []
    try:
        from rag.vectorstore import get_vectorstore
        vs = get_vectorstore()
        data = vs.get(include=["metadatas"])
        all_files = {m.get("filename") for m in (data.get("metadatas") or []) if m.get("filename")}
        return sorted(all_files - current_filenames)[:3]
    except Exception:
        return []

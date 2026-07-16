"""LangChain StructuredTool wrappers for every agent capability. Each LangGraph node
invokes exactly one of these tools -- nodes never call raw helpers directly."""
from langchain_core.tools import StructuredTool

from agents.router import identify_owner as _identify_owner, TOPICS
from agents.escalation_agent import classify_risk as _classify_risk
from rag.retriever import retrieve as _retrieve
from tools.confidence import calculate_confidence_score
from tools.audit_logger import log_query

COMPLIANCE_KEYWORDS = [
    "polic", "regulat", "complian", "data", "privacy", "gdpr", "sanction", "aml",
    "kyc", "retention", "vendor", "contract", "employ", "securit", "breach",
    "audit", "licen", "transfer", "customer record", "onboard", "due diligence",
    "risk", "governance", "clause", "article", "consent", "processing", "controller",
]

TOPIC_KEYWORDS = {
    "Sanctions": ["sanction", "ofac", "embargo", "denied party", "denied person",
                  "watchlist", "export control", "restricted party"],
    "AML": ["aml", "anti-money laundering", "money laundering", "suspicious transaction",
            "suspicious activity", "fatf", "transaction monitoring", "financial crime"],
    "KYC": ["kyc", "know your customer", "customer due diligence", "identity verification",
            "customer verification", "identity check"],
    "GDPR": ["gdpr", "data subject", "right to erasure", "data protection regulation"],
    "Data Privacy": ["privacy", "personal data", "pii", "cross-border", "cross border",
                      "eu customer data", "eu region", "eu data", "data transfer",
                      "international transfer", "customer data", "retention period",
                      "records retention", "data retention", "retention schedule",
                      "how long do we keep", "how long should we keep"],
    "Cybersecurity": ["cybersecurity", "cyber security", "incident response", "nist", "cert-in",
                       "data breach", "cyber incident", "malware", "ransomware"],
    "Information Security": ["information security", "infosec", "access control", "encryption",
                              "firewall", "password policy"],
    "Employment": ["employee", "employment", "workplace", "hr policy", "background check",
                   "new hire", "hiring", "termination"],
    "Licensing": ["licence", "license", "licensing", "permit", "regulatory approval"],
    "Contracts": ["contract", "agreement", "terms and conditions", "sla", "service level agreement"],
    "Vendor Compliance": ["vendor", "supplier", "third-party", "third party", "procurement",
                           "outsourc", "code of conduct"],
}


def classify_topic(query: str) -> dict:
    """Classifies a query into a compliance topic and determines if it is in-domain at all."""
    q = query.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return {"topic": topic, "in_domain": True}

    in_domain = any(kw in q for kw in COMPLIANCE_KEYWORDS)
    return {"topic": "Unknown" if in_domain else "Out-of-Domain", "in_domain": in_domain}


def identify_owner(topic: str) -> dict:
    """Maps a compliance topic to its responsible owner/team."""
    return {"owner": _identify_owner(topic)}


def retrieve_policy_documents(query: str) -> dict:
    """Retrieves top-5 relevant policy chunks from the vector store with similarity scores."""
    chunks = _retrieve(query, k=5)
    return {"chunks": chunks}


def generate_citations(chunks: list[dict]) -> dict:
    """Formats every qualifying retrieved chunk into a full citation with all available fields."""
    citations = []
    for c in chunks:
        if not c.get("qualifies"):
            continue
        parts = [f"{c.get('title', 'Untitled')} ({c.get('filename', '')})"]
        if c.get("page"):
            parts.append(f"Page {c['page']}")
        if c.get("section"):
            parts.append(f"Section: {c['section']}")
        if c.get("clause"):
            parts.append(f"{c['clause']}")
        parts.append(f"Chunk {c.get('chunk_id', '')}")
        citations.append(" | ".join(parts))
    return {"citations": citations}


def calculate_confidence(chunks: list[dict], citations: list[str]) -> dict:
    """Computes deterministic confidence from retrieval similarity, chunk count, and citation coverage."""
    return calculate_confidence_score(chunks, citations)


def classify_risk(query: str, topic: str = "") -> dict:
    """Classifies compliance risk level of a query as Low, Medium, or High."""
    return {"risk": _classify_risk(query, topic)}


def human_review(risk: str, owner: str) -> dict:
    """Determines whether a human review gate must block finalization of the answer."""
    if risk == "High":
        return {"status": "Pending", "owner": owner, "requires_review": True}
    return {"status": "Not Required", "owner": owner, "requires_review": False}


def log_audit(record: dict) -> dict:
    """Persists the full audit record to SQLite + JSON export."""
    row_id = log_query(record)
    return {"row_id": row_id}


classify_topic_tool = StructuredTool.from_function(classify_topic)
identify_owner_tool = StructuredTool.from_function(identify_owner)
retrieve_policy_documents_tool = StructuredTool.from_function(retrieve_policy_documents)
generate_citations_tool = StructuredTool.from_function(generate_citations)
calculate_confidence_tool = StructuredTool.from_function(calculate_confidence)
classify_risk_tool = StructuredTool.from_function(classify_risk)
human_review_tool = StructuredTool.from_function(human_review)
log_audit_tool = StructuredTool.from_function(log_audit)

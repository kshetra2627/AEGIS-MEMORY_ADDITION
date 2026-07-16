"""Topic -> owner routing table. Deterministic, no LLM required."""

TOPICS = [
    "GDPR", "Data Privacy", "Sanctions", "AML", "Licensing", "Cybersecurity",
    "KYC", "Employment", "Contracts", "Vendor Compliance", "Information Security",
]

OWNER_MAP = {
    "GDPR": "DPO",
    "Data Privacy": "DPO",
    "Sanctions": "AML Officer",
    "AML": "AML Officer",
    "KYC": "AML Officer",
    "Licensing": "Legal",
    "Contracts": "Legal",
    "Employment": "HR Compliance",
    "Cybersecurity": "Security Officer",
    "Information Security": "Security Officer",
    "Vendor Compliance": "Procurement Compliance / Risk Officer",
}


def identify_owner(topic: str) -> str:
    return OWNER_MAP.get(topic, "Compliance Manager")

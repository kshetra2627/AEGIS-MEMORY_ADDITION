"""Seed script for Hindsight memory bank — Northwind Financial Services.

Seeds approximately 80 backdated compliance events for the fictional organisation
Northwind Financial Services (NW-FS) into the configured Hindsight bank.

Story threads seeded (per spec §9):
  1. Vendor onboarding    — 5 correction events; Aegis: Legal/Medium -> Procurement Compliance/High
  2. EU-US data transfers — 4 correction events; missing SCCs / transfer impact assessment
  3. Cybersecurity gap    — 4 corpus_gap events; no matching policy in corpus
  4. Sanctions screening  — 5 review_decision events; AML Officer, approved without correction
  5. Audit findings       — 5 audit_finding events with remediation status
  6. GDPR subject access  — 4 correction / review_decision events
  7. AML monitoring       — 4 review_decision events
  8. Data retention       — 4 correction events
  9. Insider trading      — 3 review_decision events
  10. General cases       — remainder to reach ~80 total

Usage:
    python scripts/seed_memory.py                # seed missing items
    python scripts/seed_memory.py --reset        # clear local state and re-seed everything
    python scripts/seed_memory.py --status       # show seeding state, do not seed
    python scripts/seed_memory.py --dry-run      # print what would be seeded without calling Hindsight

Idempotency:
  Each seed item has a stable document_id: "nwfs-seed-{slug}".
  A local state file scripts/.seed_state.json records which document_ids
  have already been successfully sent to Hindsight. Re-runs only send new
  items. Use --reset to clear the state file and re-seed everything.

  NOTE: Hindsight does not currently expose a document_id exact-match filter
  on list_memories, so we maintain idempotency locally.  The document_id is
  sent to Hindsight on every retain() call so it is stored server-side and
  visible in the dashboard, but we do not rely on it for deduplication queries.

Requirements:
  - HINDSIGHT_API_URL, HINDSIGHT_API_KEY must be set in .env
  - MEMORY_ENABLED=true
  - hindsight-client>=0.10.1 installed

All people, departments, vendors and identifiers are purely fictional.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import memory.hindsight_client as hc

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, ".seed_state.json")

# ---------------------------------------------------------------------------
# Seed data
# Each entry: (slug, type, date, content_text, tags, metadata)
# content_text uses the § 5 template: TYPE:/DATE:/QUESTION:/TOPIC:/etc.
# All text is plain ASCII-compatible (avoid em-dashes; use "--").
# ---------------------------------------------------------------------------

SEED_EVENTS = [

    # ===========================================================================
    # STORY THREAD 1: VENDOR ONBOARDING
    # 5 correction events: Aegis says Legal/Medium; reviewers correct to
    # Procurement Compliance / High.  One event is dated 12 June (spec requirement).
    # ===========================================================================

    (
        "vendor-onboarding-2026-06-12",
        "correction",
        "2026-06-12T00:00:00Z",
        """\
TYPE: correction
DATE: 2026-06-12
QUESTION: Can we onboard FinSecure Payment Solutions as a payment processing vendor without completing a formal security questionnaire?
TOPIC: Vendor Compliance
AEGIS_OWNER: Legal | AEGIS_RISK: Medium
CORRECTED_OWNER: Procurement Compliance | CORRECTED_RISK: High
REASON: All third-party payment processors must complete Northwind's enhanced vendor due-diligence pack (security questionnaire, financial health check, and PCI-DSS attestation) before onboarding. This was the fourth similar case this quarter -- routing to Procurement Compliance is mandatory.""",
        ["vendor", "correction", "procurement"],
        {"thread": "vendor_onboarding", "corrected_owner": "Procurement Compliance", "corrected_risk": "High"},
    ),

    (
        "vendor-onboarding-2026-05-28",
        "correction",
        "2026-05-28T00:00:00Z",
        """\
TYPE: correction
DATE: 2026-05-28
QUESTION: What is the process for onboarding DataBridge Analytics as a data analytics vendor providing access to customer transaction data?
TOPIC: Vendor Compliance
AEGIS_OWNER: Legal | AEGIS_RISK: Medium
CORRECTED_OWNER: Procurement Compliance | CORRECTED_RISK: High
REASON: Any vendor with access to customer transaction data requires enhanced vendor compliance review including a Data Processing Agreement, security posture assessment, and Procurement Compliance sign-off. Legal alone is insufficient for this category.""",
        ["vendor", "correction", "data-processing"],
        {"thread": "vendor_onboarding", "corrected_owner": "Procurement Compliance", "corrected_risk": "High"},
    ),

    (
        "vendor-onboarding-2026-05-09",
        "correction",
        "2026-05-09T00:00:00Z",
        """\
TYPE: correction
DATE: 2026-05-09
QUESTION: Our operations team wants to use SwiftCheck KYC Services for automated identity verification. What approvals are needed?
TOPIC: Vendor Compliance
AEGIS_OWNER: Legal | AEGIS_RISK: Medium
CORRECTED_OWNER: Procurement Compliance | CORRECTED_RISK: High
REASON: KYC vendors access regulated personal data and are subject to Northwind's Tier-1 vendor review. Reviewer: Priya Mehta (Procurement Compliance Lead) -- these cases must always be escalated. Enhanced review required per vendor risk policy v2.3.""",
        ["vendor", "correction", "kyc"],
        {"thread": "vendor_onboarding", "corrected_owner": "Procurement Compliance", "corrected_risk": "High"},
    ),

    (
        "vendor-onboarding-2026-04-22",
        "review_decision",
        "2026-04-22T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-04-22
QUESTION: Can CloudVault Storage Ltd be onboarded for archiving regulated financial records without a full security audit?
TOPIC: Vendor Compliance
AEGIS_OWNER: Legal | AEGIS_RISK: Medium
REVIEWER_DECISION: reject
REVIEWER: Marcus Okonkwo (Head of Procurement Compliance)
REASON: Cloud storage vendors holding regulated financial records require ISO 27001 certification evidence, a completed ISMS questionnaire, and sign-off from both Procurement Compliance and the CISO. Routing to Procurement Compliance. This draft was incomplete -- risk should be High.""",
        ["vendor", "review", "cloud-storage"],
        {"thread": "vendor_onboarding", "reviewer_decision": "reject"},
    ),

    (
        "vendor-onboarding-2026-04-07",
        "correction",
        "2026-04-07T00:00:00Z",
        """\
TYPE: correction
DATE: 2026-04-07
QUESTION: We need to engage RiskRadar Compliance Tools for ongoing AML transaction monitoring. What is the onboarding process?
TOPIC: Vendor Compliance
AEGIS_OWNER: Legal | AEGIS_RISK: Medium
CORRECTED_OWNER: Procurement Compliance | CORRECTED_RISK: High
REASON: AML-related vendors are subject to heightened due diligence under Northwind's Vendor Risk Framework §4.2. Procurement Compliance coordinates the Tier-1 review alongside AML Officer sign-off. Similar vendor cases here have required enhanced review.""",
        ["vendor", "correction", "aml"],
        {"thread": "vendor_onboarding", "corrected_owner": "Procurement Compliance", "corrected_risk": "High"},
    ),

    # ===========================================================================
    # STORY THREAD 2: EU-TO-US DATA TRANSFERS
    # 4 events: reviewer decisions flag missing SCCs / transfer impact assessment
    # ===========================================================================

    (
        "eu-us-transfer-2026-06-18",
        "review_decision",
        "2026-06-18T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-06-18
QUESTION: Can Northwind's London operations share EU customer account data with our US risk analytics team in New York for fraud model training?
TOPIC: Data Privacy
AEGIS_OWNER: DPO | AEGIS_RISK: High
REVIEWER_DECISION: reject
REVIEWER: Ananya Krishnan (Data Protection Officer)
REASON: Cross-border transfer from EEA to US requires (1) valid Standard Contractual Clauses (SCCs -- Article 46 GDPR), (2) completed Transfer Impact Assessment (TIA), and (3) DPO sign-off. Draft answer omitted the TIA requirement entirely. Must not proceed without both SCCs and TIA.""",
        ["gdpr", "data-transfer", "scc"],
        {"thread": "eu_us_transfer", "reviewer_decision": "reject"},
    ),

    (
        "eu-us-transfer-2026-06-03",
        "correction",
        "2026-06-03T00:00:00Z",
        """\
TYPE: correction
DATE: 2026-06-03
QUESTION: Our marketing team wants to transfer EU prospect contact lists to the US CRM platform for campaign targeting. What steps do we need to take?
TOPIC: Data Privacy
AEGIS_OWNER: DPO | AEGIS_RISK: High
CORRECTED_OWNER: DPO | CORRECTED_RISK: High
REASON: While owner routing was correct, the draft answer did not mention Standard Contractual Clauses (EU SCCs 2021) or the requirement for a Transfer Impact Assessment for US transfers post-Schrems II. Both are mandatory under Northwind's International Transfer Policy. Answer must explicitly cite both.""",
        ["gdpr", "data-transfer", "scc", "tia"],
        {"thread": "eu_us_transfer", "corrected_owner": "DPO"},
    ),

    (
        "eu-us-transfer-2026-05-16",
        "review_decision",
        "2026-05-16T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-05-16
QUESTION: Northwind's Dublin compliance team needs to share GDPR investigation records with the New York legal team. Is this permissible under current policy?
TOPIC: Data Privacy
AEGIS_OWNER: DPO | AEGIS_RISK: High
REVIEWER_DECISION: request_changes
REVIEWER: Ananya Krishnan (Data Protection Officer)
REASON: GDPR investigation records are sensitive personal data (Article 9/10). Transfer requires not just SCCs but also a documented legitimate interest assessment and approval by the DPO before each transfer instance -- not a blanket standing authorisation. Draft did not state this.""",
        ["gdpr", "data-transfer", "sensitive-data"],
        {"thread": "eu_us_transfer", "reviewer_decision": "request_changes"},
    ),

    (
        "eu-us-transfer-2026-04-29",
        "correction",
        "2026-04-29T00:00:00Z",
        """\
TYPE: correction
DATE: 2026-04-29
QUESTION: Can we replicate our EU customer database to an AWS US-East region for disaster recovery purposes?
TOPIC: Data Privacy
AEGIS_OWNER: DPO | AEGIS_RISK: High
CORRECTED_OWNER: DPO | CORRECTED_RISK: High
REASON: AWS US-East replication of EU personal data constitutes a restricted transfer under GDPR Article 44. Must include: (1) SCCs with AWS covering processor obligations, (2) Transfer Impact Assessment documenting US surveillance law risks, (3) supplementary technical measures (encryption at rest and in transit with Northwind-held keys). Previous draft mentioned SCCs but omitted TIA and supplementary measures.""",
        ["gdpr", "data-transfer", "cloud", "aws"],
        {"thread": "eu_us_transfer", "corrected_owner": "DPO"},
    ),

    # ===========================================================================
    # STORY THREAD 3: CYBERSECURITY RENEWAL (corpus_gap)
    # 4 events: policy corpus has no matching evidence for these questions
    # ===========================================================================

    (
        "cyber-gap-penetration-testing-2026-06-25",
        "corpus_gap",
        "2026-06-25T00:00:00Z",
        """\
TYPE: corpus_gap
DATE: 2026-06-25
QUESTION: What is Northwind's mandatory schedule for penetration testing of internet-facing systems under our current cybersecurity policy?
TOPIC: Cybersecurity
AEGIS_OWNER: CISO | AEGIS_RISK: Medium
REFUSAL_REASON: Insufficient policy evidence -- no Northwind internal penetration testing schedule or cybersecurity policy document found in the corpus. The uploaded corpus covers general NIST CSF and CERT-In guidance but does not include Northwind's own cybersecurity procedures. This gap should be addressed by uploading the internal security policy.""",
        ["cybersecurity", "corpus-gap", "pentest"],
        {"thread": "cyber_gap"},
    ),

    (
        "cyber-gap-incident-response-2026-06-10",
        "corpus_gap",
        "2026-06-10T00:00:00Z",
        """\
TYPE: corpus_gap
DATE: 2026-06-10
QUESTION: What is the mandatory notification timeline for a data breach affecting UK retail banking customers under our incident response plan?
TOPIC: Cybersecurity
AEGIS_OWNER: CISO | AEGIS_RISK: High
REFUSAL_REASON: No Northwind incident response plan or UK FCA breach notification procedure found in the corpus. The corpus contains CERT-In directions (India-specific) but lacks UK-specific breach notification timelines. Recommend uploading FCA SYSC 15A policy and internal IRP.""",
        ["cybersecurity", "corpus-gap", "incident-response", "fca"],
        {"thread": "cyber_gap"},
    ),

    (
        "cyber-gap-mfa-policy-2026-05-21",
        "corpus_gap",
        "2026-05-21T00:00:00Z",
        """\
TYPE: corpus_gap
DATE: 2026-05-21
QUESTION: Does Northwind's policy require multi-factor authentication for all privileged administrator accounts, and what exceptions are permitted?
TOPIC: Cybersecurity
AEGIS_OWNER: CISO | AEGIS_RISK: High
REFUSAL_REASON: Northwind's MFA policy and privileged access management (PAM) standards are not present in the current policy corpus. NIST CSF guidance on access controls is available but cannot substitute for Northwind's specific MFA mandate. CISO team should upload the PAM standard.""",
        ["cybersecurity", "corpus-gap", "mfa", "pam"],
        {"thread": "cyber_gap"},
    ),

    (
        "cyber-gap-cloud-security-2026-05-05",
        "corpus_gap",
        "2026-05-05T00:00:00Z",
        """\
TYPE: corpus_gap
DATE: 2026-05-05
QUESTION: What cloud security baseline controls must be applied to all AWS workloads under Northwind's cloud security standard?
TOPIC: Cybersecurity
AEGIS_OWNER: CISO | AEGIS_RISK: High
REFUSAL_REASON: Northwind's Cloud Security Standard (CSS) is not present in the corpus. The NIST Cybersecurity Framework is available but does not contain Northwind-specific AWS baseline controls. The CISO office should add the CSS to the policy corpus to enable accurate guidance.""",
        ["cybersecurity", "corpus-gap", "cloud", "aws"],
        {"thread": "cyber_gap"},
    ),

    # ===========================================================================
    # STORY THREAD 4: SANCTIONS SCREENING
    # 5 review_decision events -- consistently AML Officer, approved without change
    # Demonstrates memory reinforcing correct behaviour, not just correcting errors.
    # ===========================================================================

    (
        "sanctions-screening-2026-06-20",
        "review_decision",
        "2026-06-20T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-06-20
QUESTION: A corporate client in Dubai has asked us to execute a USD wire transfer to a counterparty in Turkey. What sanctions screening obligations apply?
TOPIC: AML/Sanctions
AEGIS_OWNER: AML Officer | AEGIS_RISK: High
REVIEWER_DECISION: approve
REVIEWER: Dominic Fransen (AML Officer)
REASON: Routing to AML Officer is correct. Answer correctly cited OFAC SDN list screening, UN Security Council consolidated list, and Northwind's real-time screening requirement before execution. Approved without change.""",
        ["sanctions", "aml", "approved"],
        {"thread": "sanctions_screening", "reviewer_decision": "approve"},
    ),

    (
        "sanctions-screening-2026-06-05",
        "review_decision",
        "2026-06-05T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-06-05
QUESTION: Can Northwind open a correspondent banking relationship with a financial institution whose ultimate beneficial owner is a Russian national? What screening is required?
TOPIC: AML/Sanctions
AEGIS_OWNER: AML Officer | AEGIS_RISK: High
REVIEWER_DECISION: approve
REVIEWER: Dominic Fransen (AML Officer)
REASON: Correct routing and risk classification. The answer properly identified OFAC Russia-related designations, EU restrictive measures, and Northwind's enhanced due diligence for politically exposed persons and sanctioned jurisdiction connections. Approved without change.""",
        ["sanctions", "aml", "correspondent-banking", "approved"],
        {"thread": "sanctions_screening", "reviewer_decision": "approve"},
    ),

    (
        "sanctions-screening-2026-05-22",
        "review_decision",
        "2026-05-22T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-05-22
QUESTION: A payment instruction references an entity in Iran. What are our obligations before processing?
TOPIC: AML/Sanctions
AEGIS_OWNER: AML Officer | AEGIS_RISK: High
REVIEWER_DECISION: approve
REVIEWER: Dominic Fransen (AML Officer)
REASON: Routing to AML Officer is correct. Iran is subject to comprehensive OFAC sanctions (ITSR). The answer correctly stated the payment must be blocked and reported, not merely screened. Approved without change.""",
        ["sanctions", "aml", "iran", "approved"],
        {"thread": "sanctions_screening", "reviewer_decision": "approve"},
    ),

    (
        "sanctions-screening-2026-05-08",
        "review_decision",
        "2026-05-08T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-05-08
QUESTION: We have identified a match between a customer name and an OFAC SDN list entry. What are the next steps?
TOPIC: AML/Sanctions
AEGIS_OWNER: AML Officer | AEGIS_RISK: High
REVIEWER_DECISION: approve
REVIEWER: Dominic Fransen (AML Officer)
REASON: Correct routing and risk level. Answer correctly described the block-and-report obligation, the 10-day OFAC reporting window, and the requirement to freeze assets. Approved. Consistent with all prior sanctions cases this quarter.""",
        ["sanctions", "aml", "sdn", "approved"],
        {"thread": "sanctions_screening", "reviewer_decision": "approve"},
    ),

    (
        "sanctions-screening-2026-04-15",
        "review_decision",
        "2026-04-15T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-04-15
QUESTION: A trade finance client wants to finance a shipment of industrial equipment to Belarus. What compliance checks are required before we can proceed?
TOPIC: AML/Sanctions
AEGIS_OWNER: AML Officer | AEGIS_RISK: High
REVIEWER_DECISION: approve
REVIEWER: Dominic Fransen (AML Officer)
REASON: Correct routing to AML Officer. Answer correctly identified EU and UK Belarus sanctions, dual-use goods controls, and the need for export licence verification. Approved without change. AML Officer is always the correct owner for sanctions trade finance cases.""",
        ["sanctions", "aml", "trade-finance", "belarus", "approved"],
        {"thread": "sanctions_screening", "reviewer_decision": "approve"},
    ),

    # ===========================================================================
    # STORY THREAD 5: AUDIT FINDINGS
    # 5 audit_finding items with remediation status
    # ===========================================================================

    (
        "audit-finding-vendor-reviews-overdue-2026-06-01",
        "audit_finding",
        "2026-06-01T00:00:00Z",
        """\
TYPE: audit_finding
DATE: 2026-06-01
FINDING: 23 of 47 Tier-1 vendor annual security reviews are overdue by more than 60 days. No exception approvals on file.
AREA: Vendor Compliance
SEVERITY: High
OWNER: Marcus Okonkwo (Head of Procurement Compliance)
REMEDIATION_STATUS: In Progress -- Procurement Compliance has issued notices to all 23 vendors. Target completion: 2026-07-15.
AUDITOR: Internal Audit -- Fatima Al-Rashid""",
        ["audit", "vendor", "finding"],
        {"thread": "audit_findings", "severity": "High"},
    ),

    (
        "audit-finding-gdpr-dpia-missing-2026-05-18",
        "audit_finding",
        "2026-05-18T00:00:00Z",
        """\
TYPE: audit_finding
DATE: 2026-05-18
FINDING: Four new data processing activities were launched in Q1 2026 without a completed Data Protection Impact Assessment (DPIA), contrary to GDPR Article 35 and Northwind's DPIA procedure.
AREA: Data Privacy
SEVERITY: High
OWNER: Ananya Krishnan (Data Protection Officer)
REMEDIATION_STATUS: Completed -- DPIAs retrospectively completed and approved by DPO on 2026-05-31. Process updated to include DPIA gate in product launch checklist.
AUDITOR: Internal Audit -- Fatima Al-Rashid""",
        ["audit", "gdpr", "dpia", "finding"],
        {"thread": "audit_findings", "severity": "High"},
    ),

    (
        "audit-finding-aml-sar-training-2026-05-02",
        "audit_finding",
        "2026-05-02T00:00:00Z",
        """\
TYPE: audit_finding
DATE: 2026-05-02
FINDING: 18% of front-office staff have not completed mandatory SAR (Suspicious Activity Report) filing training within the required 12-month window.
AREA: AML/Sanctions
SEVERITY: Medium
OWNER: Dominic Fransen (AML Officer)
REMEDIATION_STATUS: In Progress -- Mandatory training sessions scheduled for June 2026. Compliance confirmed by 2026-06-30 target.
AUDITOR: External Audit -- Delphine Lecourt (KPMG)""",
        ["audit", "aml", "training", "sar", "finding"],
        {"thread": "audit_findings", "severity": "Medium"},
    ),

    (
        "audit-finding-access-review-overdue-2026-04-10",
        "audit_finding",
        "2026-04-10T00:00:00Z",
        """\
TYPE: audit_finding
DATE: 2026-04-10
FINDING: Quarterly access reviews for privileged IT accounts were not completed in Q4 2025 and Q1 2026. Eleven accounts with elevated access have not been reviewed.
AREA: Cybersecurity
SEVERITY: High
OWNER: Oliver Stein (CISO)
REMEDIATION_STATUS: Completed -- All eleven accounts reviewed and four access rights reduced. Quarterly review process automated via IGA tooling as of 2026-04-25.
AUDITOR: External Audit -- Delphine Lecourt (KPMG)""",
        ["audit", "cybersecurity", "access-control", "finding"],
        {"thread": "audit_findings", "severity": "High"},
    ),

    (
        "audit-finding-records-retention-gaps-2026-04-02",
        "audit_finding",
        "2026-04-02T00:00:00Z",
        """\
TYPE: audit_finding
DATE: 2026-04-02
FINDING: Sampling of 50 customer files found that 9 files exceeded the 7-year retention limit by more than 2 years. No deletion waiver or legal hold on file.
AREA: Records Retention
SEVERITY: Medium
OWNER: Claire Dupont (Records and Information Management Lead)
REMEDIATION_STATUS: Completed -- 9 files securely deleted. Automated retention enforcement enabled in the document management system. Annual compliance check scheduled.
AUDITOR: Internal Audit -- Fatima Al-Rashid""",
        ["audit", "retention", "records", "finding"],
        {"thread": "audit_findings", "severity": "Medium"},
    ),

    # ===========================================================================
    # STORY THREAD 6: GDPR SUBJECT ACCESS REQUESTS
    # 4 events -- correction and review_decision
    # ===========================================================================

    (
        "gdpr-sar-timeline-2026-06-15",
        "correction",
        "2026-06-15T00:00:00Z",
        """\
TYPE: correction
DATE: 2026-06-15
QUESTION: A customer submitted a Subject Access Request (SAR) on 10 June. What is the response deadline under GDPR?
TOPIC: Data Privacy
AEGIS_OWNER: DPO | AEGIS_RISK: Medium
CORRECTED_OWNER: DPO | CORRECTED_RISK: Medium
REASON: The draft answer stated 30 days but failed to note that the clock starts from the day the request is received and that the 30-day period can be extended by a further two months for complex or high-volume requests, with notification to the data subject within the initial 30-day window (Article 12(3) GDPR). Correction required for accuracy.""",
        ["gdpr", "sar", "timeline"],
        {"thread": "gdpr_sar"},
    ),

    (
        "gdpr-sar-third-party-2026-05-26",
        "review_decision",
        "2026-05-26T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-05-26
QUESTION: A SAR requests all records related to a customer including internal meeting notes referencing third parties. Must we disclose the third-party information?
TOPIC: Data Privacy
AEGIS_OWNER: DPO | AEGIS_RISK: Medium
REVIEWER_DECISION: request_changes
REVIEWER: Ananya Krishnan (Data Protection Officer)
REASON: Answer did not address the third-party balancing test. When SAR responses contain information about other individuals, disclosure must be balanced against their privacy rights (GDPR Article 15(4) + UK DPA 2018 s.45). Third-party data can be redacted where disclosure would prejudice their rights. Draft must be revised to reflect this.""",
        ["gdpr", "sar", "third-party"],
        {"thread": "gdpr_sar", "reviewer_decision": "request_changes"},
    ),

    (
        "gdpr-right-to-erasure-2026-05-12",
        "review_decision",
        "2026-05-12T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-05-12
QUESTION: A customer has requested erasure of all personal data under GDPR Article 17. Can we comply immediately?
TOPIC: Data Privacy
AEGIS_OWNER: DPO | AEGIS_RISK: High
REVIEWER_DECISION: request_changes
REVIEWER: Ananya Krishnan (Data Protection Officer)
REASON: Erasure cannot be immediate -- Northwind must first check for: (1) legal obligations to retain data (AML/CFT record-keeping, 5 years), (2) ongoing contractual or legal proceedings, (3) legitimate interests override. The draft said erasure was required within 30 days without any of these caveats. Risk is correctly High but answer needs significant revision.""",
        ["gdpr", "erasure", "retention"],
        {"thread": "gdpr_sar", "reviewer_decision": "request_changes"},
    ),

    (
        "gdpr-lawful-basis-marketing-2026-04-20",
        "correction",
        "2026-04-20T00:00:00Z",
        """\
TYPE: correction
DATE: 2026-04-20
QUESTION: Can we use existing customer contact details for a new product marketing campaign without seeking fresh consent?
TOPIC: Data Privacy
AEGIS_OWNER: DPO | AEGIS_RISK: Medium
CORRECTED_OWNER: DPO | CORRECTED_RISK: Medium
REASON: Correct owner. Draft answer relied solely on 'legitimate interests' as lawful basis without acknowledging PECR (UK) / ePrivacy Directive (EU) requirements for electronic marketing, which require prior opt-in consent for email/SMS marketing to individuals. Soft opt-in rules apply for existing customers only if the product is similar. Draft must be corrected.""",
        ["gdpr", "marketing", "pecr", "consent"],
        {"thread": "gdpr_sar"},
    ),

    # ===========================================================================
    # STORY THREAD 7: AML TRANSACTION MONITORING
    # 4 review_decision events
    # ===========================================================================

    (
        "aml-pep-screening-2026-06-22",
        "review_decision",
        "2026-06-22T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-06-22
QUESTION: A new corporate client's director has been identified as a Politically Exposed Person (PEP). What enhanced due diligence measures apply under Northwind's AML policy?
TOPIC: AML/Sanctions
AEGIS_OWNER: AML Officer | AEGIS_RISK: High
REVIEWER_DECISION: approve
REVIEWER: Dominic Fransen (AML Officer)
REASON: Correct routing to AML Officer. Answer correctly cited FATF Recommendation 12 and Northwind's EDD procedures: senior management approval for the relationship, source-of-wealth verification, and ongoing enhanced monitoring. Approved without change.""",
        ["aml", "pep", "edd", "approved"],
        {"thread": "aml_monitoring", "reviewer_decision": "approve"},
    ),

    (
        "aml-str-threshold-2026-06-08",
        "review_decision",
        "2026-06-08T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-06-08
QUESTION: What cash transaction reporting thresholds apply to Northwind's retail banking operations and what are the filing requirements?
TOPIC: AML/Sanctions
AEGIS_OWNER: AML Officer | AEGIS_RISK: Medium
REVIEWER_DECISION: request_changes
REVIEWER: Dominic Fransen (AML Officer)
REASON: Answer cited a single threshold but Northwind operates in multiple jurisdictions with different CTR thresholds (UK: no mandatory CTR -- SAR-based; India: INR 10 lakh; US correspondent: USD 10,000 CTR). Draft must specify jurisdiction-specific thresholds.""",
        ["aml", "ctr", "reporting", "jurisdiction"],
        {"thread": "aml_monitoring", "reviewer_decision": "request_changes"},
    ),

    (
        "aml-structured-deposits-2026-05-19",
        "review_decision",
        "2026-05-19T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-05-19
QUESTION: A customer is making multiple cash deposits of GBP 8,500 on consecutive days. What are our monitoring and reporting obligations?
TOPIC: AML/Sanctions
AEGIS_OWNER: AML Officer | AEGIS_RISK: High
REVIEWER_DECISION: approve
REVIEWER: Dominic Fransen (AML Officer)
REASON: Correct routing and risk. Answer correctly identified the structuring / smurfing risk, the obligation to file a SAR with the UK NCA under POCA 2002, and the tipping-off prohibition. Approved without change.""",
        ["aml", "structuring", "sar", "approved"],
        {"thread": "aml_monitoring", "reviewer_decision": "approve"},
    ),

    (
        "aml-kyc-refresh-2026-04-28",
        "case",
        "2026-04-28T00:00:00Z",
        """\
TYPE: case
DATE: 2026-04-28
QUESTION: How frequently must Northwind refresh KYC documentation for high-risk corporate clients?
TOPIC: AML/Sanctions
OWNER: AML Officer
RISK: High
GOVERNANCE_OUTCOME: passed
ANSWER_SUMMARY: High-risk corporate clients require KYC documentation refresh at least annually, or upon any material change (change of control, new beneficial owners, change in business activity). Periodic reviews triggered by transaction alerts must also prompt an out-of-cycle refresh. Based on FATF Recommendations 10/22 and Northwind AML Policy §7.""",
        ["aml", "kyc", "periodic-review"],
        {"thread": "aml_monitoring"},
    ),

    # ===========================================================================
    # STORY THREAD 8: DATA RETENTION
    # 4 correction events
    # ===========================================================================

    (
        "retention-customer-records-2026-06-09",
        "correction",
        "2026-06-09T00:00:00Z",
        """\
TYPE: correction
DATE: 2026-06-09
QUESTION: How long must Northwind retain closed retail banking account records?
TOPIC: Records Retention
AEGIS_OWNER: Legal | AEGIS_RISK: Low
CORRECTED_OWNER: Legal | CORRECTED_RISK: Low
REASON: Owner and risk correct. Draft stated 5 years but Northwind's retention schedule requires 7 years for closed retail accounts to satisfy FCA COBS 9.5 and AML record-keeping under POCA/TPCA. Corrected to 7 years post-account-closure.""",
        ["retention", "records", "banking"],
        {"thread": "data_retention"},
    ),

    (
        "retention-trade-records-2026-05-27",
        "case",
        "2026-05-27T00:00:00Z",
        """\
TYPE: case
DATE: 2026-05-27
QUESTION: What is the retention period for MiFID II trade records including order and execution data?
TOPIC: Records Retention
OWNER: Legal
RISK: Medium
GOVERNANCE_OUTCOME: passed
ANSWER_SUMMARY: MiFID II Article 25 requires investment firms to retain records of all services and transactions for at least 7 years (UK: FCA COBS 9.5 applies same 7-year standard). Records must be accessible for regulatory inspection throughout the period. Based on MiFID II Article 25 and Northwind Records Retention Schedule v3.2.""",
        ["retention", "mifid2", "trading"],
        {"thread": "data_retention"},
    ),

    (
        "retention-hr-data-2026-05-13",
        "correction",
        "2026-05-13T00:00:00Z",
        """\
TYPE: correction
DATE: 2026-05-13
QUESTION: An employee left Northwind 8 years ago. Can HR delete their personnel file?
TOPIC: Records Retention
AEGIS_OWNER: Legal | AEGIS_RISK: Low
CORRECTED_OWNER: Legal | CORRECTED_RISK: Low
REASON: Draft said records should be deleted based on a 7-year rule. However Northwind's HR Retention Schedule requires 7 years from termination date -- meaning an employee who left 8 years ago is now past the retention period and the file should be deleted (not retained further). The logic in the draft was reversed. Owner and risk are correct.""",
        ["retention", "hr", "employee"],
        {"thread": "data_retention"},
    ),

    (
        "retention-email-communications-2026-04-18",
        "case",
        "2026-04-18T00:00:00Z",
        """\
TYPE: case
DATE: 2026-04-18
QUESTION: What is Northwind's retention period for business email communications involving investment advice?
TOPIC: Records Retention
OWNER: Legal
RISK: Low
GOVERNANCE_OUTCOME: passed
ANSWER_SUMMARY: Business emails constituting investment advice or material records of financial transactions must be retained for 7 years under MiFID II and FCA SYSC rules. General business correspondence not constituting regulated activity is retained for 3 years per Northwind's email retention policy. Archive enforcement is managed by the Records Management team.""",
        ["retention", "email", "investment"],
        {"thread": "data_retention"},
    ),

    # ===========================================================================
    # STORY THREAD 9: INSIDER TRADING / MARKET ABUSE
    # 3 review_decision events
    # ===========================================================================

    (
        "insider-trading-material-info-2026-06-16",
        "review_decision",
        "2026-06-16T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-06-16
QUESTION: A senior analyst at Northwind has received non-public information about a potential M&A transaction from an investment banking colleague. What restrictions apply?
TOPIC: Market Integrity
AEGIS_OWNER: Legal | AEGIS_RISK: High
REVIEWER_DECISION: approve
REVIEWER: James Whitfield (General Counsel)
REASON: Correct routing and risk. Answer correctly identified the information barrier obligation, the prohibition on trading and tipping under UK MAR, the requirement to record the wall-crossing in the conflicts register, and restricted list procedures. Approved without change.""",
        ["market-abuse", "insider-trading", "information-barrier", "approved"],
        {"thread": "insider_trading", "reviewer_decision": "approve"},
    ),

    (
        "insider-trading-personal-account-2026-05-30",
        "case",
        "2026-05-30T00:00:00Z",
        """\
TYPE: case
DATE: 2026-05-30
QUESTION: What pre-clearance requirements apply before a Northwind compliance officer trades in the shares of a client?
TOPIC: Market Integrity
OWNER: Legal
RISK: High
GOVERNANCE_OUTCOME: passed
ANSWER_SUMMARY: All Northwind staff classified as Relevant Persons must obtain pre-clearance from the Compliance Monitoring team before dealing in securities of any client or counterparty of Northwind. The request must identify the security, the proposed trade size, and whether the person possesses any material non-public information. Pre-clearance does not apply to trades in collective investment schemes (UCITS/ETFs). Based on Northwind Personal Account Dealing Policy §3 and UK MAR Article 19.""",
        ["market-abuse", "personal-account-dealing", "pre-clearance"],
        {"thread": "insider_trading"},
    ),

    (
        "insider-trading-restricted-list-2026-04-25",
        "review_decision",
        "2026-04-25T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-04-25
QUESTION: How often should Northwind's restricted list be reviewed and who has authority to add securities to it?
TOPIC: Market Integrity
AEGIS_OWNER: Legal | AEGIS_RISK: Medium
REVIEWER_DECISION: approve
REVIEWER: James Whitfield (General Counsel)
REASON: Correct routing. Answer correctly stated the restricted list is reviewed weekly by Compliance and updated in real time when material non-public information is received. Authority to add securities rests with the Head of Compliance or General Counsel. Approved without change.""",
        ["market-abuse", "restricted-list", "compliance", "approved"],
        {"thread": "insider_trading", "reviewer_decision": "approve"},
    ),

    # ===========================================================================
    # ADDITIONAL CASES: SUPPLIER CODE OF CONDUCT / THIRD-PARTY RISK
    # 4 cases to round out to ~80 events
    # ===========================================================================

    (
        "supplier-conduct-modern-slavery-2026-06-24",
        "case",
        "2026-06-24T00:00:00Z",
        """\
TYPE: case
DATE: 2026-06-24
QUESTION: Does Northwind need to include modern slavery and human trafficking clauses in contracts with all new suppliers?
TOPIC: Vendor Compliance
OWNER: Procurement Compliance
RISK: Medium
GOVERNANCE_OUTCOME: passed
ANSWER_SUMMARY: Yes -- under the UK Modern Slavery Act 2015, Northwind must include appropriate modern slavery warranty and audit-rights clauses in contracts with suppliers. This applies to all suppliers regardless of jurisdiction. Northwind's Supplier Code of Conduct §8 mandates annual confirmation from Tier-1 suppliers. For Tier-2 and below, inclusion in standard terms and conditions is sufficient.""",
        ["vendor", "modern-slavery", "supplier-code"],
        {"thread": "supplier_conduct"},
    ),

    (
        "supplier-conduct-esg-due-diligence-2026-06-11",
        "case",
        "2026-06-11T00:00:00Z",
        """\
TYPE: case
DATE: 2026-06-11
QUESTION: What ESG due diligence obligations does Northwind have when onboarding new suppliers?
TOPIC: Vendor Compliance
OWNER: Procurement Compliance
RISK: Low
GOVERNANCE_OUTCOME: passed
ANSWER_SUMMARY: Northwind's Supplier Code of Conduct requires all new suppliers to complete an ESG self-assessment questionnaire. Tier-1 suppliers (annual spend >GBP 500K) must also provide their own ESG or sustainability report. Procurement Compliance reviews responses and may request corrective action plans before approving onboarding. Based on Northwind Supplier Code of Conduct §§ 2, 4, 7.""",
        ["vendor", "esg", "supplier-code"],
        {"thread": "supplier_conduct"},
    ),

    (
        "supplier-conduct-subprocessor-approval-2026-05-29",
        "correction",
        "2026-05-29T00:00:00Z",
        """\
TYPE: correction
DATE: 2026-05-29
QUESTION: Can a cloud software vendor sub-contract processing of Northwind customer data to a third-party data centre without notifying us?
TOPIC: Data Privacy
AEGIS_OWNER: Legal | AEGIS_RISK: Medium
CORRECTED_OWNER: DPO | CORRECTED_RISK: High
REASON: Any change of sub-processor or appointment of a new sub-processor requires prior written consent from Northwind (GDPR Article 28(2)). The DPA with the vendor must include a clause requiring 30 days' written notice and a right to object. Routing to DPO is correct -- Legal is insufficient for sub-processor matters. Risk is High due to GDPR enforcement risk.""",
        ["data-privacy", "sub-processor", "gdpr"],
        {"thread": "supplier_conduct", "corrected_owner": "DPO", "corrected_risk": "High"},
    ),

    (
        "supplier-conduct-conflict-minerals-2026-05-14",
        "case",
        "2026-05-14T00:00:00Z",
        """\
TYPE: case
DATE: 2026-05-14
QUESTION: Does Northwind have obligations under conflict minerals regulations when procuring IT hardware for its data centres?
TOPIC: Vendor Compliance
OWNER: Procurement Compliance
RISK: Low
GOVERNANCE_OUTCOME: passed
ANSWER_SUMMARY: Northwind, as a financial services provider and not a product manufacturer, is not directly in scope for EU Conflict Minerals Regulation (EU 2017/821). However, Northwind's Supplier Code of Conduct encourages IT hardware suppliers to comply with responsible sourcing standards (RBA Code, OECD Due Diligence Guidance). No direct statutory obligation on Northwind, but supplier questionnaire should address this.""",
        ["vendor", "conflict-minerals", "hardware"],
        {"thread": "supplier_conduct"},
    ),

    # ===========================================================================
    # ADDITIONAL ROUND-OUT CASES: FINANCIAL CRIME / BRIBERY
    # 4 events
    # ===========================================================================

    (
        "bribery-gifts-policy-2026-06-17",
        "case",
        "2026-06-17T00:00:00Z",
        """\
TYPE: case
DATE: 2026-06-17
QUESTION: What is the maximum value of a gift that a Northwind employee can accept from a client without manager pre-approval?
TOPIC: Financial Crime
OWNER: Legal
RISK: Low
GOVERNANCE_OUTCOME: passed
ANSWER_SUMMARY: Northwind's Gifts and Hospitality Policy permits acceptance of gifts up to GBP 50 in value without pre-approval. Gifts between GBP 50 and GBP 100 require line manager approval. Any gift over GBP 100 must be approved by the Head of Compliance and entered in the Gifts Register. Cash gifts of any amount are prohibited. Based on Northwind G&H Policy v4 and UK Bribery Act 2010 guidance.""",
        ["bribery", "gifts", "hospitality"],
        {"thread": "bribery"},
    ),

    (
        "bribery-public-officials-2026-06-02",
        "review_decision",
        "2026-06-02T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-06-02
QUESTION: Northwind is tendering for a government contract in India. A local intermediary has suggested paying a facilitation payment to expedite the licensing process. Can we proceed?
TOPIC: Financial Crime
AEGIS_OWNER: Legal | AEGIS_RISK: High
REVIEWER_DECISION: approve
REVIEWER: James Whitfield (General Counsel)
REASON: Routing to Legal is correct. The answer correctly advised that facilitation payments are prohibited under the UK Bribery Act 2010 regardless of local custom or legality, that this conduct would constitute bribery of a foreign public official (s.6 Bribery Act), and that the intermediary arrangement must be reviewed under Northwind's third-party due diligence policy. Risk correctly classified as High. Approved without change.""",
        ["bribery", "facilitation-payment", "india", "approved"],
        {"thread": "bribery", "reviewer_decision": "approve"},
    ),

    (
        "bribery-adequate-procedures-2026-05-20",
        "case",
        "2026-05-20T00:00:00Z",
        """\
TYPE: case
DATE: 2026-05-20
QUESTION: What constitutes 'adequate procedures' under the UK Bribery Act 2010 that Northwind must maintain?
TOPIC: Financial Crime
OWNER: Legal
RISK: Medium
GOVERNANCE_OUTCOME: passed
ANSWER_SUMMARY: Under the UK Bribery Act 2010 s.7, 'adequate procedures' comprise six principles: proportionate procedures, top-level commitment, risk assessment, due diligence on associated persons, communication and training, and monitoring and review. Northwind's Anti-Bribery and Corruption Policy v3 maps to all six principles. Annual training is mandatory for all staff. Based on Ministry of Justice Guidance (March 2011) and Northwind AB&C Policy.""",
        ["bribery", "adequate-procedures", "bribery-act"],
        {"thread": "bribery"},
    ),

    (
        "bribery-third-party-intermediary-2026-04-30",
        "review_decision",
        "2026-04-30T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-04-30
QUESTION: Can Northwind engage a sales agent in a high-risk jurisdiction without conducting due diligence on the agent?
TOPIC: Financial Crime
AEGIS_OWNER: Legal | AEGIS_RISK: High
REVIEWER_DECISION: request_changes
REVIEWER: James Whitfield (General Counsel)
REASON: While the draft correctly identified the bribery risk, it did not specify the required scope of third-party due diligence: UBO verification, PEP screening, negative news search, and contractual anti-bribery warranties. Northwind's Third-Party Due Diligence Procedure §3 requires all four. Draft must be revised to specify each step.""",
        ["bribery", "third-party", "due-diligence"],
        {"thread": "bribery", "reviewer_decision": "request_changes"},
    ),

    # ===========================================================================
    # FINAL ROUND-OUT: RECORDS RETENTION EDGE CASES + FFIEC
    # 4 events to reach approx 80 total
    # ===========================================================================

    (
        "ffiec-examination-prep-2026-06-26",
        "case",
        "2026-06-26T00:00:00Z",
        """\
TYPE: case
DATE: 2026-06-26
QUESTION: What documentation must Northwind prepare for an upcoming FFIEC IT examination?
TOPIC: Cybersecurity
OWNER: CISO
RISK: High
GOVERNANCE_OUTCOME: passed
ANSWER_SUMMARY: For an FFIEC IT examination, Northwind must prepare: IT strategic plan, IS audit reports (most recent 2 years), business continuity and disaster recovery test results, information security program documentation, change management logs, network diagrams, and evidence of cybersecurity framework assessment (FFIEC CAT recommended). Based on FFIEC IT Examination Handbook and Northwind IT Governance Policy.""",
        ["ffiec", "examination", "cybersecurity"],
        {"thread": "ffiec"},
    ),

    (
        "ffiec-bsa-aml-exam-2026-06-14",
        "review_decision",
        "2026-06-14T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-06-14
QUESTION: What are the key elements regulators examine during a BSA/AML compliance programme review?
TOPIC: AML/Sanctions
AEGIS_OWNER: AML Officer | AEGIS_RISK: High
REVIEWER_DECISION: approve
REVIEWER: Dominic Fransen (AML Officer)
REASON: Correct routing to AML Officer. Answer correctly described the five pillars of an adequate BSA/AML programme: internal controls, independent testing, a designated BSA/AML compliance officer, training, and customer due diligence. Regulators also examine SAR filing quality and timeliness, CTR accuracy, and OFAC screening procedures. Approved without change.""",
        ["ffiec", "bsa-aml", "examination", "approved"],
        {"thread": "ffiec", "reviewer_decision": "approve"},
    ),

    (
        "retention-legal-hold-2026-06-07",
        "case",
        "2026-06-07T00:00:00Z",
        """\
TYPE: case
DATE: 2026-06-07
QUESTION: Northwind has received a regulatory investigation notice. How should we handle normal deletion schedules for records potentially in scope?
TOPIC: Records Retention
OWNER: Legal
RISK: High
GOVERNANCE_OUTCOME: passed
ANSWER_SUMMARY: Upon receipt of a regulatory investigation notice or litigation hold notice, all normal deletion schedules must be suspended for records within scope. The Legal team issues a formal Legal Hold Notice to custodians. Records relevant to the investigation must be preserved regardless of their normal retention period. Failure to preserve records constitutes spoliation and may attract regulatory penalties. Based on Northwind Legal Hold Policy §2 and UK Civil Procedure Rules.""",
        ["retention", "legal-hold", "investigation"],
        {"thread": "data_retention"},
    ),

    (
        "dpdp-india-notice-2026-06-04",
        "correction",
        "2026-06-04T00:00:00Z",
        """\
TYPE: correction
DATE: 2026-06-04
QUESTION: Does Northwind need to provide a privacy notice to Indian customers in a specific language under the Digital Personal Data Protection Act 2023?
TOPIC: Data Privacy
AEGIS_OWNER: DPO | AEGIS_RISK: Medium
CORRECTED_OWNER: DPO | CORRECTED_RISK: Medium
REASON: The draft answer did not address the language requirement under DPDP Act 2023 s.5(1)(b): the notice must be available in any of the 22 scheduled languages of India that the data principal requests. This is a material requirement that was omitted. Owner and risk classification are correct.""",
        ["dpdp", "india", "privacy-notice", "language"],
        {"thread": "dpdp_india"},
    ),

    # ===========================================================================
    # ADDITIONAL VENDOR ONBOARDING CASES (extending thread 1 to 8 events)
    # ===========================================================================

    (
        "vendor-onboarding-2026-06-27",
        "correction",
        "2026-06-27T00:00:00Z",
        """\
TYPE: correction
DATE: 2026-06-27
QUESTION: We want to engage a new HR payroll software provider -- TalentPay Ltd -- who will process employee salary data. What compliance steps are required before go-live?
TOPIC: Vendor Compliance
AEGIS_OWNER: Legal | AEGIS_RISK: Medium
CORRECTED_OWNER: Procurement Compliance | CORRECTED_RISK: High
REASON: HR payroll systems that process employee personal and financial data are classified as Tier-1 vendors under Northwind's Vendor Risk Framework. Procurement Compliance must lead the onboarding review including a DPIA, Data Processing Agreement, and security certification check. Enhanced vendor compliance review required.""",
        ["vendor", "correction", "hr", "payroll"],
        {"thread": "vendor_onboarding", "corrected_owner": "Procurement Compliance", "corrected_risk": "High"},
    ),

    (
        "vendor-onboarding-2026-06-19",
        "review_decision",
        "2026-06-19T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-06-19
QUESTION: Northwind's operations team wants to use RegTech Insights Ltd for automated regulatory change monitoring. Is vendor compliance approval required?
TOPIC: Vendor Compliance
AEGIS_OWNER: Legal | AEGIS_RISK: Low
REVIEWER_DECISION: request_changes
REVIEWER: Marcus Okonkwo (Head of Procurement Compliance)
REASON: Even though this vendor has read-only access to regulatory news feeds, the contract must still pass through Procurement Compliance for standard vendor registration and a basic security review. Risk reclassification to Medium is recommended given regulatory data sensitivity. Draft answer understated the process.""",
        ["vendor", "review", "regtech"],
        {"thread": "vendor_onboarding", "reviewer_decision": "request_changes"},
    ),

    (
        "vendor-onboarding-2026-03-31",
        "correction",
        "2026-03-31T00:00:00Z",
        """\
TYPE: correction
DATE: 2026-03-31
QUESTION: Can we fast-track the onboarding of a new credit scoring vendor to meet a product launch deadline next week?
TOPIC: Vendor Compliance
AEGIS_OWNER: Legal | AEGIS_RISK: Medium
CORRECTED_OWNER: Procurement Compliance | CORRECTED_RISK: High
REASON: Credit scoring vendors access sensitive customer financial data and credit history. Fast-tracking the vendor due-diligence process is not permitted under Northwind policy -- all Tier-1 vendors must complete the full review cycle regardless of commercial timelines. Procurement Compliance escalated this and confirmed enhanced vendor review is mandatory.""",
        ["vendor", "correction", "credit-scoring", "fast-track"],
        {"thread": "vendor_onboarding", "corrected_owner": "Procurement Compliance", "corrected_risk": "High"},
    ),

    # ===========================================================================
    # ADDITIONAL EU-US TRANSFER CASES (extending thread 2)
    # ===========================================================================

    (
        "eu-us-transfer-2026-06-27",
        "case",
        "2026-06-27T00:00:00Z",
        """\
TYPE: case
DATE: 2026-06-27
QUESTION: What is the current EU-approved mechanism for transferring personal data from the EU to the United States following Schrems II?
TOPIC: Data Privacy
OWNER: DPO
RISK: High
GOVERNANCE_OUTCOME: passed
ANSWER_SUMMARY: Following the invalidation of Privacy Shield in Schrems II (C-311/18), the primary approved mechanism for EU-to-US transfers is the Standard Contractual Clauses (SCCs) adopted by the European Commission in June 2021 (Decision 2021/914). A Transfer Impact Assessment (TIA) must also be conducted for each transfer to assess US surveillance law risks. The EU-US Data Privacy Framework (adequacy decision, July 2023) is also available for certified US organisations. Based on GDPR Article 46 and Northwind International Transfer Policy.""",
        ["gdpr", "data-transfer", "scc", "schrems-ii"],
        {"thread": "eu_us_transfer"},
    ),

    (
        "eu-us-transfer-2026-04-14",
        "correction",
        "2026-04-14T00:00:00Z",
        """\
TYPE: correction
DATE: 2026-04-14
QUESTION: Northwind's US parent company needs access to EU employee HR records for consolidated global reporting. How should this transfer be structured?
TOPIC: Data Privacy
AEGIS_OWNER: DPO | AEGIS_RISK: High
CORRECTED_OWNER: DPO | CORRECTED_RISK: High
REASON: Intra-group transfers remain restricted transfers under GDPR. Options include: Intra-Group Agreement incorporating EU SCCs (as controller-to-controller SCCs), Binding Corporate Rules (BCRs -- longer lead time), or the EU-US DPF if the US entity is certified. The draft did not mention the SCCs option or BCRs and incorrectly implied that group ownership removes GDPR transfer restrictions.""",
        ["gdpr", "data-transfer", "intra-group", "bcr"],
        {"thread": "eu_us_transfer"},
    ),

    # ===========================================================================
    # ADDITIONAL CYBERSECURITY CORPUS GAP CASES (extending thread 3)
    # ===========================================================================

    (
        "cyber-gap-bcdr-testing-2026-06-23",
        "corpus_gap",
        "2026-06-23T00:00:00Z",
        """\
TYPE: corpus_gap
DATE: 2026-06-23
QUESTION: What is Northwind's required frequency for testing business continuity and disaster recovery plans?
TOPIC: Cybersecurity
AEGIS_OWNER: CISO | AEGIS_RISK: High
REFUSAL_REASON: Northwind's Business Continuity Policy and Disaster Recovery Plan testing schedule are not present in the policy corpus. The NIST Cybersecurity Framework and FFIEC IT Handbook provide general guidance but do not contain Northwind-specific BC/DR testing requirements. The CISO office should upload the Northwind BCM Policy to enable accurate guidance on testing frequency.""",
        ["cybersecurity", "corpus-gap", "bcdr", "business-continuity"],
        {"thread": "cyber_gap"},
    ),

    (
        "cyber-gap-vulnerability-disclosure-2026-05-30",
        "corpus_gap",
        "2026-05-30T00:00:00Z",
        """\
TYPE: corpus_gap
DATE: 2026-05-30
QUESTION: Does Northwind have a coordinated vulnerability disclosure policy and how should external security researchers report findings?
TOPIC: Cybersecurity
AEGIS_OWNER: CISO | AEGIS_RISK: Medium
REFUSAL_REASON: No Northwind Vulnerability Disclosure Policy or responsible disclosure procedure was found in the corpus. The NIST CSF addresses patch management in general terms but does not cover coordinated disclosure programmes. The CISO should publish and upload a CVD policy to enable this question to be answered.""",
        ["cybersecurity", "corpus-gap", "vulnerability-disclosure", "cvd"],
        {"thread": "cyber_gap"},
    ),

    # ===========================================================================
    # ADDITIONAL AML MONITORING CASES
    # ===========================================================================

    (
        "aml-wire-transfer-data-2026-06-13",
        "case",
        "2026-06-13T00:00:00Z",
        """\
TYPE: case
DATE: 2026-06-13
QUESTION: What originator and beneficiary information must accompany international wire transfers under FATF Recommendation 16 (the Travel Rule)?
TOPIC: AML/Sanctions
OWNER: AML Officer
RISK: High
GOVERNANCE_OUTCOME: passed
ANSWER_SUMMARY: Under FATF Recommendation 16 (Travel Rule), all wire transfers above USD/EUR 1,000 must include: full name, account number, and address/national identity number of the originator, and full name and account number of the beneficiary. The ordering institution must transmit this information with the transfer and it must be available for retrieval by competent authorities. Based on FATF R.16 and Northwind Wire Transfer Policy §5.""",
        ["aml", "travel-rule", "wire-transfer", "fatf"],
        {"thread": "aml_monitoring"},
    ),

    (
        "aml-derisking-policy-2026-04-08",
        "review_decision",
        "2026-04-08T00:00:00Z",
        """\
TYPE: review_decision
DATE: 2026-04-08
QUESTION: Northwind is considering terminating relationships with all money service businesses (MSBs) due to AML risk. Is a blanket de-risking approach compliant with our policy?
TOPIC: AML/Sanctions
AEGIS_OWNER: AML Officer | AEGIS_RISK: High
REVIEWER_DECISION: request_changes
REVIEWER: Dominic Fransen (AML Officer)
REASON: Blanket de-risking of all MSBs is not consistent with a risk-based approach and may be commercially and reputationally problematic. FATF guidance and FCA Dear CEO letters both caution against wholesale de-risking. The correct approach is individual risk assessment per MSB relationship. Draft must be revised to reflect individual assessment rather than blanket termination.""",
        ["aml", "derisking", "msb"],
        {"thread": "aml_monitoring", "reviewer_decision": "request_changes"},
    ),

    # ===========================================================================
    # ADDITIONAL RECORDS RETENTION / LEGAL HOLD CASES
    # ===========================================================================

    (
        "retention-marketing-data-2026-06-20",
        "case",
        "2026-06-20T00:00:00Z",
        """\
TYPE: case
DATE: 2026-06-20
QUESTION: How long can Northwind retain the personal data of prospective customers who did not take out a product (application abandonments)?
TOPIC: Records Retention
OWNER: DPO
RISK: Medium
GOVERNANCE_OUTCOME: passed
ANSWER_SUMMARY: Prospective customer data collected during an incomplete application may be retained for up to 6 months to allow the prospect to resume their application. After 6 months of inactivity, the data must be deleted or anonymised unless the individual has given explicit consent for longer retention for marketing purposes. Based on Northwind Retention Schedule §4.3 and GDPR data minimisation principle (Article 5(1)(c)).""",
        ["retention", "marketing", "prospects"],
        {"thread": "data_retention"},
    ),

    (
        "retention-litigation-hold-2026-04-23",
        "correction",
        "2026-04-23T00:00:00Z",
        """\
TYPE: correction
DATE: 2026-04-23
QUESTION: A former employee has threatened employment tribunal proceedings. Can HR still delete their personnel file under the normal 7-year retention rule?
TOPIC: Records Retention
AEGIS_OWNER: Legal | AEGIS_RISK: Medium
CORRECTED_OWNER: Legal | CORRECTED_RISK: High
REASON: The threat of litigation triggers a litigation hold -- the personnel file must be preserved even if it would otherwise be due for deletion under the 7-year rule. Deleting the file after receiving notice of a potential claim would constitute spoliation. Legal should issue a hold notice immediately. Risk should be High given potential for legal proceedings. Draft correctly identified Legal as owner but understated risk.""",
        ["retention", "legal-hold", "employment", "litigation"],
        {"thread": "data_retention", "corrected_owner": "Legal", "corrected_risk": "High"},
    ),

]

# ---------------------------------------------------------------------------
# Count for developer reference (printed at seed time)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Local state file helpers
# ---------------------------------------------------------------------------

def _load_state():
    """Load the set of document_ids already successfully seeded."""
    if not os.path.exists(STATE_FILE):
        return set()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("seeded_ids", []))
    except Exception:
        return set()


def _save_state(seeded_ids):
    """Persist the set of seeded document_ids to the state file."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"seeded_ids": sorted(seeded_ids)}, f, indent=2)


def _clear_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print("[seed] State file removed -- all items will be re-seeded.")


# ---------------------------------------------------------------------------
# Seeding logic
# ---------------------------------------------------------------------------

def _check_config():
    """Check that Hindsight is configured and enabled. Return (ok, msg)."""
    api_url = os.getenv("HINDSIGHT_API_URL", "").strip()
    api_key = os.getenv("HINDSIGHT_API_KEY", "").strip()
    mem_enabled = os.getenv("MEMORY_ENABLED", "false").strip().lower()

    issues = []
    if not api_url:
        issues.append("HINDSIGHT_API_URL is not set")
    if not api_key:
        issues.append("HINDSIGHT_API_KEY is not set")
    if mem_enabled != "true":
        issues.append("MEMORY_ENABLED is '{}' (must be 'true')".format(mem_enabled))

    if issues:
        return False, "\n".join("  - " + i for i in issues)
    return True, None


def _doc_id(slug):
    return "nwfs-seed-{}".format(slug)


def seed(dry_run=False, reset=False):
    """Seed memory events. Returns (seeded_count, skipped_count, error_count)."""
    ok, config_err = _check_config()
    if not ok:
        print("ERROR: Hindsight is not properly configured:\n{}".format(config_err))
        print()
        print("Set these values in your .env file:")
        print("  HINDSIGHT_API_URL=https://api.hindsight.vectorize.io")
        print("  HINDSIGHT_API_KEY=<your-api-key>")
        print("  MEMORY_ENABLED=true")
        return 0, 0, len(SEED_EVENTS)

    if reset:
        _clear_state()

    seeded_ids = _load_state()
    pending = [e for e in SEED_EVENTS if _doc_id(e[0]) not in seeded_ids]

    total = len(SEED_EVENTS)
    skip_count = total - len(pending)
    seed_count = 0
    error_count = 0

    print("[seed] Total events defined: {}".format(total))
    print("[seed] Already seeded (skipping): {}".format(skip_count))
    print("[seed] To seed now: {}".format(len(pending)))

    if not pending:
        print("[seed] Nothing to seed -- bank is already up to date.")
        print("[seed] Use --reset to re-seed everything.")
        return 0, skip_count, 0

    if dry_run:
        print("[seed] DRY RUN -- no Hindsight calls will be made.")
        for slug, mem_type, ts, text, tags, metadata in pending:
            doc_id = _doc_id(slug)
            print("  Would retain: {} | {} | {}".format(doc_id, mem_type, ts[:10]))
        return 0, skip_count, 0

    print("[seed] Starting retain calls... (this may take a minute)")
    print()

    for i, (slug, mem_type, ts, text, tags, metadata) in enumerate(pending, 1):
        doc_id = _doc_id(slug)
        # Merge mem_type into metadata alongside provided metadata
        full_metadata = dict(metadata or {})
        full_metadata["mem_type"] = mem_type
        full_metadata["seed"] = "nwfs"

        ok_r, err = hc.retain(
            text,
            metadata={k: str(v) for k, v in full_metadata.items()},
            timestamp=ts,
            tags=(tags or []) + ["nwfs-seed"],
        )
        if ok_r:
            seeded_ids.add(doc_id)
            seed_count += 1
            print("  [{}{}] OK  {}  ({})".format(
                i, "/" + str(len(pending)), doc_id, mem_type))
            # Save state incrementally so progress is not lost on interruption
            _save_state(seeded_ids)
        else:
            error_count += 1
            print("  [{}{}] ERR {}  -- {}".format(
                i, "/" + str(len(pending)), doc_id, err))

        # Small delay to avoid hammering the API
        time.sleep(0.15)

    print()
    print("[seed] Done.  Seeded: {}  Skipped: {}  Errors: {}".format(
        seed_count, skip_count, error_count))

    if error_count > 0:
        print("[seed] WARNING: {} item(s) failed to seed. "
              "Re-run the script to retry only the failed items.".format(error_count))

    return seed_count, skip_count, error_count


def show_status():
    """Print current seeding status without seeding anything."""
    ok, config_err = _check_config()
    seeded_ids = _load_state()

    print("[status] Hindsight configured: {}".format("YES" if ok else "NO"))
    if not ok:
        print("[status] Config issues:\n{}".format(config_err))
    print("[status] Total events defined: {}".format(len(SEED_EVENTS)))
    print("[status] Seeded (per state file): {}".format(len(seeded_ids)))
    print("[status] Pending: {}".format(len(SEED_EVENTS) - len(seeded_ids)))
    print("[status] State file: {}".format(STATE_FILE))

    # Show per-thread summary
    thread_counts = {}
    for slug, mem_type, ts, text, tags, metadata in SEED_EVENTS:
        thread = metadata.get("thread", "other")
        thread_counts[thread] = thread_counts.get(thread, 0) + 1
    print()
    print("[status] Events per story thread:")
    for thread, count in sorted(thread_counts.items()):
        print("  {:40s} {}".format(thread, count))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Seed Northwind Financial Services compliance events into Hindsight."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear local state and re-seed all events (useful after a bank wipe).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Print what would be seeded without making any Hindsight API calls.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current seeding status and exit.",
    )
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    seeded, skipped, errors = seed(dry_run=args.dry_run, reset=args.reset)

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

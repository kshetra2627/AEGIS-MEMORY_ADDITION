# Aegis — Hardcoded Value Audit

## 1. Summary

Total hardcoded values found:
84

Potentially sensitive values:
19

Configuration values:
37

UI/static values:
28

---

## 2. Sensitive / Security-Critical Values

| File | Line | Type | Risk | Recommendation |
|------|------|------|------|----------------|
| `.env` | 2 | Groq API Key | High (Exposure of production LLM token: `[REDACTED]`) | Store exclusively in secure secret store or encrypted secret manager; ensure `.env` is never committed. |
| `.env` | 4 | Gemini API Key | High (Exposure of Google AI API token: `[REDACTED]`) | Store in cloud secrets manager (e.g. AWS Secrets Manager, GCP Secret Manager); keep out of source control. |
| `.env` | 6 | OpenRouter API Key | High (Exposure of model gateway API key: `[REDACTED]`) | Keep in secure secret store; rotate key periodically. |
| `.env` | 14 | Hindsight Memory API Key | High (Exposure of organizational memory token: `[REDACTED]`) | Rotate key and pull dynamically from vault or KMS. |
| `scripts/smoke_hindsight.py` | 96 | Test API Key Literal | Low (Deliberate test string `[REDACTED]` used for failure test) | Acceptable for offline test, but parameterize via mock object instead of monkeypatching. |
| `tests/test_auth.py` | 58 | Mock Account Password | Medium (Test credential `[REDACTED]`) | Use ephemeral test factories (e.g. `faker` or `uuid4()`) instead of static password literals. |
| `tests/test_auth.py` | 64 | Mock Account Password | Medium (Test credential `[REDACTED]`) | Use dynamically generated password in test suite. |
| `tests/test_auth.py` | 87 | Mock Account Password | Medium (Test credential assertion `[REDACTED]`) | Reference generated test fixture variable. |
| `tests/test_auth.py` | 95 | Mock Account Password | Medium (Test verification `[REDACTED]`) | Reference fixture variable. |
| `tests/test_auth.py` | 186 | Mock Account Password | Medium (Test credential `[REDACTED]`) | Reference dynamically generated fixture variable. |
| `tests/test_auth.py` | 190 | Mock Account Password | Medium (Test signin password `[REDACTED]`) | Reference dynamically generated fixture variable. |
| `tests/test_auth.py` | 215 | Mock Account Password | Medium (User A password `[REDACTED]`) | Reference dynamically generated fixture variable. |
| `tests/test_auth.py` | 216 | Mock Account Password | Medium (User B password `[REDACTED]`) | Reference dynamically generated fixture variable. |
| `tests/test_auth.py` | 224 | Mock Account Password | Medium (User A password check `[REDACTED]`) | Reference fixture variable. |
| `tests/test_auth.py` | 226 | Mock Account Password | Medium (User B password check `[REDACTED]`) | Reference fixture variable. |
| `tests/test_e2e_verification.py` | 203 | E2E Test Password | Medium (E2E User A credential `[REDACTED]`) | Use ephemeral dynamic token fixture. |
| `tests/test_e2e_verification.py` | 212 | E2E Test Password | Medium (E2E User A signin `[REDACTED]`) | Use ephemeral dynamic token fixture. |
| `tests/test_e2e_verification.py` | 233 | E2E Test Password | Medium (E2E User B credential `[REDACTED]`) | Use ephemeral dynamic token fixture. |
| `tests/test_e2e_verification.py` | 241 | E2E Test Password | Medium (E2E duplicate register `[REDACTED]`) | Use ephemeral dynamic token fixture. |

---

## 3. Configuration Values

| File | Line | Value Type | Current Implementation | Recommendation |
|------|------|------------|-----------------------|----------------|
| `llm_provider.py` | 9, 19 | Fallback LLM Models | Hardcoded list `["openai/gpt-oss-20b", "openai/gpt-oss-120b"]` | Provide via `GROQ_FALLBACK_MODELS` environment variable. |
| `llm_provider.py` | 28, 67 | API Request Timeout | Hardcoded integer `timeout=20` | Make configurable via `LLM_REQUEST_TIMEOUT` env variable. |
| `llm_provider.py` | 49 | Default Gemini Model | Hardcoded string `"gemini-2.5-flash"` fallback | Move default to `.env.example` and read without in-code fallback. |
| `llm_provider.py` | 57 | Gemini Request Timeout | Hardcoded integer `timeout=20` | Bind to unified `LLM_REQUEST_TIMEOUT`. |
| `llm_provider.py` | 79 | Sampling Temperature | Hardcoded float `temperature: float = 0.1` | Make configurable via `LLM_TEMPERATURE` env variable. |
| `rag/retriever.py` | 18 | Similarity Threshold | Fallback string `"0.65"` in `os.getenv` | Retain `.env` sourcing; keep default in configuration schema. |
| `rag/retriever.py` | 19 | Retrieval Candidate Pool | Hardcoded integer `CANDIDATE_POOL_SIZE = 15` | Move to config/environment setting `RAG_CANDIDATE_POOL_SIZE`. |
| `rag/retriever.py` | 36 | Top-K Retrieval | Hardcoded default parameter `k: int = 5` | Provide via `RAG_TOP_K` environment variable. |
| `rag/embeddings.py` | 11 | Embedding Model | Fallback string `"all-MiniLM-L6-v2"` | Sourced from `EMBEDDING_MODEL` env var; ensure documented in config schema. |
| `rag/vectorstore.py` | 7 | Chroma Persistence Path | Hardcoded path `os.path.join("database", "chroma")` | Expose via `CHROMA_PERSIST_DIR` environment variable. |
| `rag/vectorstore.py` | 8 | Vector Collection Name | Hardcoded string `COLLECTION_NAME = "policies"` | Make configurable via `CHROMA_COLLECTION_NAME`. |
| `rag/vectorstore.py` | 9 | Hash Registry Path | Hardcoded path `os.path.join("database", "ingested_hashes.json")` | Expose via `HASH_REGISTRY_PATH` env variable. |
| `rag/vectorstore.py` | 22 | HNSW Vector Distance Metric | Hardcoded dict `{"hnsw:space": "cosine"}` | Expose via vector store configuration dict. |
| `memory/hindsight_client.py` | 43 | Memory Bank Identifier | Hardcoded fallback `"aegis-northwind"` | Require explicit `HINDSIGHT_BANK_ID` or error out if unset. |
| `memory/hindsight_client.py` | 44 | Memory Enabled Default | Hardcoded fallback `"false"` | Keep as explicit toggle. |
| `memory/hindsight_client.py` | 45 | Memory Timeout Seconds | Hardcoded fallback `"5"` | Sourced from `MEMORY_TIMEOUT_SECONDS`; maintain config documentation. |
| `memory/hindsight_client.py` | 46 | Memory Top-K | Hardcoded fallback `"5"` | Sourced from `MEMORY_TOP_K`; maintain config documentation. |
| `tools/audit_logger.py` | 13 | Audit SQLite Database Path | Hardcoded path `os.path.join("database", "audit.db")` | Expose via `AUDIT_DB_PATH` environment variable. |
| `tools/audit_logger.py` | 14 | Audit JSON Export Path | Hardcoded path `os.path.join("logs", "audit_log.json")` | Expose via `AUDIT_JSON_PATH` environment variable. |
| `tools/compliance_tools.py` | 11 | Compliance Keywords List | 27 hardcoded string keywords | Externalize into a JSON/YAML configuration file (`config/compliance_keywords.json`). |
| `tools/compliance_tools.py` | 18 | Topic Classification Keywords | Hardcoded dictionary with 11 topic keyword lists | Move to `config/topic_rules.json` to allow hot-reloading rules without code deploys. |
| `tools/compliance_tools.py` | 62 | Policy Retrieval K-Limit | Hardcoded parameter `k=5` | Reference unified `RAG_TOP_K` setting. |
| `agents/router.py` | 3 | Supported Topics List | 11 hardcoded topics | Derive dynamically from `OWNER_MAP` or external taxonomy file. |
| `agents/router.py` | 8 | Owner Mapping Table | Hardcoded mapping of topics to team roles | Move to `config/owner_routing.json` for organizational flexibility. |
| `agents/router.py` | 24 | Fallback Compliance Owner | Hardcoded string `"Compliance Manager"` | Make configurable via `DEFAULT_COMPLIANCE_OWNER`. |
| `config/risk_rules.json` | 2 | High Risk Regex Rules | 9 hardcoded regex strings | Retain in JSON config; add schema validation. |
| `config/risk_rules.json` | 13 | Medium Risk Regex Rules | 5 hardcoded regex strings | Retain in JSON config; add schema validation. |
| `config/risk_rules.json` | 20 | High Risk Topic Identifiers | `["Sanctions", "AML"]` | Retain in JSON config; allow runtime additions. |
| `config/risk_rules.json` | 21 | Cross-Border Markers | Hardcoded lists of EU markers, foreign regions, verbs | Retain in JSON config; allow runtime additions. |
| `ui/pages/settings.py` | 6 | Application Version | Hardcoded string `APP_VERSION = "1.0.0"` | Read from `package.json`, `pyproject.toml`, or git tag. |
| `ui/auth.py` | 23 | Authentication DB Path | Hardcoded path `os.path.join("database", "auth.db")` | Expose via `AUTH_DB_PATH` environment variable. |
| `ui/auth.py` | 31, 72 | Default User Role | Hardcoded default `'compliance_officer'` | Define in role configuration constants file. |
| `ui/auth.py` | 76 | Minimum Password Length | Hardcoded integer `8` | Expose via security policy setting `AUTH_MIN_PASSWORD_LENGTH`. |

---

## 4. Static UI Values

| File | Line | Value | Should It Remain Hardcoded? |
|------|------|-------|-----------------------------|
| `app.py` | 20 | `"Aegis - Compliance Advisory & Triage Agent"` | Yes, standard application window title. |
| `app.py` | 20 | `"🛡️"` | Yes, branding favicon emoji. |
| `app.py` | 62 | `"Aegis"` / `"Compliance Operations"` | Yes, branding element (or internationalize if i18n is required). |
| `app.py` | 181 | `"🚪 Sign Out"` | Yes, standard UI action label. |
| `ui/auth.py` | 240 | `"Aegis"` / `"COMPLIANCE OPERATIONS"` | Yes, front-page branding text. |
| `ui/auth.py` | 241 | `"AI THAT WORKS FOR COMPLIANCE"` | Yes, product marketing eyebrow. |
| `ui/auth.py` | 242 | `"Smarter Compliance. Stronger Enterprises."` | Yes, marketing hero headline. |
| `ui/auth.py` | 243 | `"Aegis leverages AI agents to help enterprises streamline compliance operations, reduce risk, and stay audit-ready — effortlessly."` | Yes, product supporting lede. |
| `ui/auth.py` | 244-249 | Feature block titles and descriptions (Automated Monitoring, AI-Powered Agents, Audit Ready) | Yes, marketing feature descriptions. |
| `ui/auth.py` | 264 | `"Sign in to your account"` | Yes, standard login card subtitle. |
| `ui/auth.py` | 270 | Tabs `["Sign In", "Register"]` | Yes, UI navigation tabs. |
| `ui/auth.py` | 274, 294 | `"Email Address"` placeholder `"name@company.com"` | Yes, form input placeholder. |
| `ui/auth.py` | 275 | `"Password"` placeholder `"••••••••"` | Yes, standard password mask. |
| `ui/auth.py` | 277 | `"Sign In →"` | Yes, action button text. |
| `ui/auth.py` | 293 | `"Display Name"` placeholder `"Jane Smith"` | Yes, form input placeholder. |
| `ui/auth.py` | 298 | `"Create Account →"` | Yes, action button text. |
| `ui/auth.py` | 75 | `"Enter a valid email address."` | Can remain hardcoded; move to localized strings if multi-language is required. |
| `ui/auth.py` | 77 | `"Password must be at least 8 characters."` | Can remain hardcoded; move to localized strings if multi-language is required. |
| `ui/auth.py` | 79 | `"Display name is required."` | Can remain hardcoded; move to localized strings if multi-language is required. |
| `ui/auth.py` | 90 | `"Account created."` | Can remain hardcoded; move to localized strings if multi-language is required. |
| `ui/auth.py` | 92 | `"An account with that email already exists."` | Can remain hardcoded; move to localized strings if multi-language is required. |
| `ui/auth.py` | 150 | `"Email and password are required."` | Can remain hardcoded; move to localized strings if multi-language is required. |
| `ui/auth.py` | 157 | `"Invalid email or password."` | Can remain hardcoded; move to localized strings if multi-language is required. |
| `ui/styles.py` | 8-21 | Theme hex palette (`#050B17`, `#07111F`, `#0A1426`, `#2563EB`, `#3B82F6`, `#60A5FA`, `#F8FAFC`, `#94A3B8`) | Yes, standard CSS custom property design system tokens. |
| `ui/pages/dashboard.py` | 23 | `"🛡️ Aegis"` | Yes, page header title. |
| `ui/pages/dashboard.py` | 24 | `"Enterprise AI Agent for Compliance Operations"` | Yes, product tagline. |
| `ui/pages/dashboard.py` | 38 | `"Today's Status"` | Yes, dashboard section header. |
| `ui/pages/settings.py` | 16 | `"⚙️ Settings"` | Yes, settings view title. |

---

## 5. API / URL Values

| File | Line | URL Type | Recommendation |
|------|------|----------|----------------|
| `llm_provider.py` | 28 | Groq Production API (`https://api.groq.com/openai/v1`) | Parameterize with `GROQ_BASE_URL` env variable for proxying / enterprise gateways. |
| `llm_provider.py` | 67 | OpenRouter Production API (`https://openrouter.ai/api/v1`) | Parameterize with `OPENROUTER_BASE_URL` env variable. |
| `memory/hindsight_client.py` | 4, 21 | Hindsight Cloud Endpoint (`https://api.hindsight.vectorize.io`) | Keep in `.env` (`HINDSIGHT_API_URL`); document fallback in `.env.example`. |
| `.env` | 13 | Active Hindsight API Endpoint | Ensure this endpoint matches the deployment target (cloud vs. self-hosted). |
| `.env.example` | 20 | Localhost Hindsight URL (`http://localhost:8888`) | Keep as documented example for self-hosted installations. |
| `.env.example` | 21, 22 | Cloud Hindsight URL (`https://api.hindsight.vectorize.io`) | Keep as documented production example. |
| `scripts/smoke_hindsight.py` | 109 | Localhost Loopback Port (`http://127.0.0.1:19999`) | Retain for network-failure simulation test. |
| `scripts/seed_memory.py` | 1234 | Cloud Hindsight URL (`https://api.hindsight.vectorize.io`) | Read from `HINDSIGHT_API_URL` env var instead of hardcoding in script. |
| `ui/styles.py` | 5 | Google Web Fonts (`https://fonts.googleapis.com/...`) | In restricted / air-gapped enterprise environments, host the Inter font locally. |

---

## 6. Mock / Test Data

The following mock accounts, test credentials, and sample simulation datasets were identified:

1. **Authentication Test Accounts (`tests/test_auth.py`)**:
   - `alice@example.com` (Display Name: "Alice Smith", Password: `[REDACTED]`)
   - `alice@example.com` (Duplicate registration attempt, Password: `[REDACTED]`)
   - `bob@example.com` (Short password test `<8 chars`, Password: `[REDACTED]`)
   - `dave@example.com` (Empty display name test, Password: `[REDACTED]`)
   - `signin_test@example.com` (Display Name: "Sign In Tester", Password: `[REDACTED]`)
   - `nobody@nowhere.com` (Non-existent user authentication failure test)
   - `user_a@corp.com` (User isolation test, Password: `[REDACTED]`)
   - `user_b@corp.com` (User isolation test, Password: `[REDACTED]`)

2. **End-to-End Test Accounts (`tests/test_e2e_verification.py`)**:
   - `e2e_user_a@test.com` (Display Name: "E2E User A", Password: `[REDACTED]`)
   - `e2e_user_b@test.com` (Display Name: "E2E User B", Password: `[REDACTED]`)
   - `nobody@nowhere.com` (Non-existent account test)

3. **Smoke Test Mock Failures (`scripts/smoke_hindsight.py`)**:
   - Simulated invalid API key: `"INVALID-KEY-smoke-test"`
   - Simulated dead loopback endpoint: `"http://127.0.0.1:19999"`
   - Sample prompt: `"vendor onboarding"`

4. **Synthetic Seed Memory Bank Records (`scripts/seed_memory.py`)**:
   - Pre-generated compliance resolution narratives, past audit responses, and policy interpretations loaded into the Hindsight memory bank.

5. **Test Query Datasets (`tests/test_e2e_verification.py`)**:
   - In-domain GDPR test: `"What is the retention period for customer records under GDPR?"`
   - High-risk EU-US transfer test: `"Can we transfer personal data from our EU office to our US subsidiary without Standard Contractual Clauses?"`
   - Out-of-domain governance test: `"What is the weather forecast for London this weekend?"`
   - Vendor onboarding test: `"Can we onboard a new payment vendor if the vendor has not yet provided complete security and compliance documentation?"`

---

## 7. Environment Variable Check

| Environment File | Present | Tracked in Git | Status |
|-------------------|---------|----------------|--------|
| `.env` | Yes | Excluded via `.gitignore` | Configured with active local keys. |
| `.env.local` | No | Not mentioned in `.gitignore` | Missing wildcard protection in `.gitignore`. |
| `.env.development`| No | Not mentioned in `.gitignore` | Missing wildcard protection in `.gitignore`. |
| `.env.production` | No | Not mentioned in `.gitignore` | Missing wildcard protection in `.gitignore`. |
| `.env.example` | Yes | Tracked in Git | Clean documentation template with placeholder values. |

### Gitignore Exclusion Audit
- Current `.gitignore` contents:
  ```gitignore
  .venv/
  __pycache__/
  *.pyc
  .env
  database/chroma/
  database/audit.db
  database/ingested_hashes.json
  logs/audit_log.json
  .streamlit/
  ```
- **CRITICAL GAP**: `.gitignore` explicitly ignores `.env` and `database/audit.db`, but does **NOT** ignore:
  1. `database/auth.db` (Contains production user accounts, display names, emails, and bcrypt password hashes).
  2. `.env.*` or `.env.local` / `.env.production` (Standard environment variations could be committed inadvertently).

---

## 8. Recommendations

### MUST FIX
1. **Add `database/auth.db` to `.gitignore`**: The SQLite authentication database stores actual registered users and bcrypt password hashes. It must never be tracked or committed to version control.
2. **Add `.env*.local` and `.env.*` to `.gitignore`**: Prevent accidental commits of environment-specific credential files.
3. **Secure API Key Storage**: Migrate active provider keys (`GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `HINDSIGHT_API_KEY`) from local unencrypted `.env` files into a managed secrets vault in deployment environments.

### SHOULD FIX
1. **Dynamic LLM Base URLs**: Parameterize `base_url` for Groq (`https://api.groq.com/openai/v1`) and OpenRouter (`https://openrouter.ai/api/v1`) in `llm_provider.py` via `GROQ_BASE_URL` and `OPENROUTER_BASE_URL` to facilitate corporate network proxying and gateway routing.
2. **Move Rule Tables to Configuration Files**: Externalize `COMPLIANCE_KEYWORDS` and `TOPIC_KEYWORDS` from `tools/compliance_tools.py` and `OWNER_MAP` from `agents/router.py` into JSON/YAML files to enable compliance officers to update routing and classification rules without code deployments.
3. **Parameterize Timeouts and Model Defaults**: Expose LLM timeouts, candidate pool sizes, and retrieval limits (`k=5`) via environment variables rather than hardcoded module-level constants.
4. **Offline Inter Font Option**: For air-gapped enterprise deployments, support serving the Inter font family locally rather than relying on `fonts.googleapis.com`.

### OPTIONAL
1. **Static UI Copy**: Product marketing headlines (`"Smarter Compliance. Stronger Enterprises."`), button labels, and validation feedback messages are appropriately defined in the presentation layer, but could be extracted to an i18n translation dictionary if internationalization is required in future releases.
2. **Test Account Ephemeral Generators**: Replace static test strings in unit tests with dynamic fixtures.

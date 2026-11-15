# Limitations, Security Risks, and Research Challenges

This document analyzes the fundamental assumptions, coverage blindspots, privacy trade-offs, and boundary conditions of the Multi-Agent Transparency Platform.

---

## 1. Coverage Blindspots & Uninstrumented Egress

### The Challenge:
The Observability Gateway operates at instrumented network and mediation boundaries (e.g., SDK wrappers, proxies, middleware). If an agent runtime makes an out-of-band direct socket call or invokes an unmediated native operating system binary that bypasses the gateway, that action remains invisible to the execution and interaction graphs.

### Mitigation & Residual Utility:
1. **Explicit Absence Accounting:** The gateway maintains a declared inventory of permitted tools. If a tool appears in the declared inventory but emits no CIM events during a delegation lifecycle, the absence is itself a detectable forensic signal.
2. **Mandatory Ingress/Egress Routing:** In enterprise environments, network security policies (e.g., eBPF or firewall sidecars) should enforce that agent egress can only route through the gateway proxy.
3. **Transparent Bounding:** The platform explicitly marks uninstrumented actions as `unbound/unknown` rather than falsely claiming complete observability.

---

## 2. Attribution vs. Intent Inference

### The Challenge:
A fundamental design commitment of this research is that **we observe executed actions and communicated messages, not internal neural model intent**.
- If an agent is steered by prompt injection, indirect instruction override, or hallucinations, its executed tool calls are still attributed to the active delegation under which they executed.
- The framework cannot determine whether an action was "intended" by the human principal or caused by adversarial jailbreaking.

### Design Boundary:
Attribution and authorization compliance are orthogonal to intent verification. The platform provides structural forensic evidence of the access/share footprint (*"what was touched and where did data go"*) so human auditors can judge intent.

---

## 3. Privacy vs. Forensic Transparency Trade-off

### The Challenge:
Recording complete inter-agent message payloads can inadvertently capture customer PII, internal credentials, proprietary intellectual property, or confidential communications.

### Mitigation via Three Capture Tiers:
- **Level 1 (Metadata Only):** Captures identities, timestamps, types, and statuses. Zero payload exposure.
- **Level 2 (Metadata + Summary — Default):** Stores structured semantic summaries and resource labels without raw message bodies.
- **Level 3 (Full Observable Content):** Stores complete observable message bodies, protected by automated regex-based redaction of emails, API tokens, phone numbers, and credit cards.
- **Strict Prohibition:** Internal neural chain-of-thought, hidden reasoning tokens, and model activation weights are **never requested, exposed, or persisted**.

---

## 4. Telemetry Security & Identifier Forgery

### The Challenge:
If agents were permitted to self-assert delegation identifiers, a compromised or prompt-injected agent could spoof a `delegation_id` belonging to a benign administrative principal, misattributing malicious actions.

### Mitigation (Invariant I5):
- The Observability Gateway authoritatively mints `delegation_id` tokens bound to authenticated principal sessions.
- In untrusted environments, emitted telemetry records should be cryptographically signed by the gateway using HMAC or asymmetric key pairs, and stored in append-only or tamper-evident ledgers.

---

## 5. Purely Observational (No Runtime Enforcement)

### The Challenge:
The system is an **observability and forensic platform**, not an inline runtime firewall or authorization blocker.
- It does not block unauthorized actions in real time, prevent data exfiltration, or automatically roll back compromised state.
- Runtime access control remains the responsibility of authorization substrates (such as ABAC, RBAC, or XACML policy decision points).

---

## 6. Operational Overhead

### Measured Impact:
- **Storage Overhead:** Baseline trace logging requires ~341 B/event. CIM adds ~247 B/event. Our full Interaction Graph extension with metadata summaries adds ~154 B/event (totaling ~742 B/event).
- **Latency Overhead:** Interception and delegation binding add ~0.01 ms median latency and ~0.29 ms p95 latency.
- In ultra-high-throughput environments, gateway event queues must be buffered asynchronously to prevent backpressure on agent decision loops.


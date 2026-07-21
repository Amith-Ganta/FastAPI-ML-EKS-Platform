# EKS-repo reverify + rewrite — checkpoint (resumable)

Repo: FastAPI-ML-EKS-Platform · remote Amith-Ganta/FastAPI-ML-EKS-Platform (main)
Contract is **NESTED** (`{"response":{predicted_category,confidence,class_probabilities}}`) — matches app.py:140, frontend.py:36. Do NOT flatten (flat = the *other* Docker repo).
Image is **tweakster24/insurance-premium-api:latest**, pulled (validated), NOT built-from-source. Do NOT change.
K8s.pem lives one dir up (scratchpad root), gitignored via `*.pem`. NEVER commit it.

## Verified defects (all fixed)
1. docs/architecture/README.md:56  VPA -.-> GRAF  →  VPA -.-> PODS        [FIXED]
2. README.md:86  VPA -. recommends size .-> MON  →  ... .-> P1 & P2 & P3  [FIXED]
3. docs/APP_README.md secrets table: blank line + missing DOCKER_USERNAME  [FIXED]

Rejected as false positives (LLM-as-judge): nested-JSON in EKS API.md/APP_README (correct here);
CONTRIBUTING.md snippets (illustrative templates, not contract).

## Full prose rewrite — one file per turn, commit+push each
- [x] commit #0: the 3 verified fixes (a57969d)
- [x] README.md (4ffa5be) — fixed "among" typo->error-rate, VPA updateMode note
- [x] docs/architecture/README.md (5a81ea0) — VPA->PODS edge + "acts on" reading
- [x] docs/kubernetes/COMPONENTS.md (28920c0) — voice only, all facts preserved
- [x] docs/kubernetes/DESIGN_DECISIONS.md — verified clean (already senior voice)
- [x] docs/diagrams/README.md — verified clean
- [x] docs/monitoring/README.md — verified clean
- [x] docs/security/README.md — verified clean
- [x] docs/operations/README.md — verified clean
- [x] docs/performance/README.md (804a262) — FIX: load-test payload → real schema
- [x] docs/debugging/README.md — verified clean
- [x] docs/runbooks/README.md — verified clean
- [x] docs/API.md (18cb030) — FIX: 'GET/redoc' → 'GET /redoc'
- [x] docs/DEPLOYMENT.md — verified clean
- [x] docs/LOCAL_SETUP.md (18cb030) — FIX: clone URL/cd/tree → FastAPI-ML-EKS-Platform
- [x] docs/ARCHITECTURE.md — verified clean (t3.micro = app EC2, correct)
- [x] docs/CONTRIBUTING.md (18cb030) — FIX: fork clone repo name; snippets = templates (OK)
- [x] docs/APP_README.md — left as-is: faithful mirror of app repo's own README
- [x] docs/images/README.md — verified clean
- [x] load-test/README.md (804a262) — FIX: load-test payload → real schema

Rule: keep every manifest reference, image name, IP, port, and diagram edge accurate to ground truth.

## SWEEP COMPLETE (all pushed to main)
Commits this pass: 804a262 (payload×2), 18cb030 (repo-name×2 + redoc typo).
Earlier: a57969d, 4ffa5be, 5a81ea0, 28920c0.
Real defects fixed total: 3 (initial) + 2 payload + 3 (redoc + 2×repo-name) = 8.
No contract flattening introduced. K8s.pem never touched. tweakster24 image unchanged.

# Production design decisions

Every non-obvious choice in this platform, with the reasoning and the trade-off
accepted. The point is not that these are the only right answers — it's that each
was a *decision*, made against alternatives, not a default left unexamined.

---

### Why `replicas: 2` (and not 1, and not "a big number")
- **Decision:** Deployment floor of 2.
- **Why:** 2 is the minimum that survives a single failure. With 1 replica, any
  node loss or rolling update is a full outage. 2 lets `maxUnavailable: 0` keep
  serving while one pod is replaced.
- **Trade-off:** 2 idle replicas cost more than 1. Accepted — availability is
  worth one small pod. Capacity above 2 is the HPA's job, not a hardcoded number.

### Why the HPA targets **50%** CPU
- **Decision:** `averageUtilization: 50` on CPU.
- **Why:** A new pod takes ~15–30s to pull, start, and pass readiness. If you
  scale at 90% you're already saturated during that window. 50% leaves headroom
  to absorb the spike while the new pod boots.
- **Trade-off:** Runs more replicas than a higher threshold would. Accepted —
  inference latency under burst matters more than squeezing the last 40% of CPU.

### Why HPA on CPU but VPA in **recommend-only** mode
- **Decision:** HPA enforces on CPU; VPA (`updateMode: "Off"`) only advises.
- **Why:** HPA and VPA acting on the *same* metric fight — HPA adds pods to lower
  per-pod CPU while VPA raises the CPU request. Splitting responsibilities (HPA =
  count, VPA = size-advice) removes the conflict.
- **Trade-off:** Right-sizing isn't automatic — a human applies VPA
  recommendations at deploy time. Accepted: on a 2-node cluster, VPA "Auto" mode
  *evicts* pods to resize them, which is too disruptive.

### Why `requests: cpu 25m / memory 256Mi`, `limits: cpu 250m / memory 256Mi`
- **Decision:** Small CPU request, memory request == limit.
- **Why:** Measurement (VPA/Goldilocks) showed the service idles far below 25m
  CPU; memory is the real constraint. Setting memory request == limit gives the
  pod **Guaranteed** QoS for memory, so it's the *last* thing evicted under
  node memory pressure. The CPU limit (250m) caps a runaway without throttling
  normal inference.
- **Trade-off:** A low CPU request means the scheduler packs pods tightly; a
  genuine CPU-heavy release would need the request raised. That's exactly what
  the VPA recommendation would flag.

### Why three probes, all `httpGet /health:8000`
- **Decision:** startup + readiness + liveness, all HTTP to `/health`.
- **Why:**
  - **startupProbe** shields a slow cold start (model unpickling) from liveness —
    up to 60s to boot before liveness can kill it.
  - **readinessProbe** gates Service endpoints: an overloaded pod is pulled from
    the load-balancer set *without* a restart, so it can recover.
  - **livenessProbe** restarts a genuinely wedged process — deliberately slower
    than readiness so transient load never triggers a restart storm.
  - **httpGet, not exec:** the slim image has no `curl`/`wget`; an exec probe
    would fail on the missing binary rather than on real health.
- **Trade-off:** Three probes are more config than one. Accepted — conflating
  "busy" with "dead" is a classic cascading-failure cause.

### Why **Ingress + one ALB** instead of `LoadBalancer` per Service or NodePort
- **Decision:** Consolidated ALB via the AWS Load Balancer Controller.
- **Why:** `type: LoadBalancer` provisions a cloud LB *per Service* — three
  services, three ELBs, three hourly bills, three endpoints. One ALB fronting all
  services by path is cheaper and gives L7 routing + TLS. NodePort exposes raw
  high ports on every node — no L7, no TLS, operationally ugly.
- **Trade-off:** Adds a controller (and its IRSA role) to install and understand.
  Accepted — it's the standard production edge on EKS and pays for itself in LB
  cost immediately.

### Why the Cluster Autoscaler when we already have an HPA
- **Decision:** Run the CA on top of the HPA.
- **Why:** The HPA schedules *pods*; pods need *nodes*. When the HPA wants more
  pods than the current nodes can hold (≈11/node on `t3.small`), they sit
  `Pending`. The CA turns "pending pods" into "another EC2 node."
- **Trade-off:** More nodes = more cost, and the CA needs IRSA + correct ASG
  tags. Accepted — without it, horizontal scaling silently caps at node capacity.

### Why managed node groups (and `t3.small`)
- **Decision:** EKS managed node group, 2× `t3.small`.
- **Why:** Managed node groups handle AMI updates, draining, and ASG wiring —
  less undifferentiated ops than self-managed nodes. `t3.small` is the cheapest
  size that comfortably holds the app plus the monitoring stack for a demo/learn
  cluster.
- **Trade-off:** `t3.small`'s ~11-pod IP ceiling is a real constraint (it shapes
  the HPA `max` and the CA trigger). A production workload would size up; here the
  ceiling is a *teaching* feature and is documented, not hidden.

### Why Prometheus internal, Grafana exposed
- **Decision:** Prometheus `ClusterIP`; Grafana `LoadBalancer` (or behind the ALB).
- **Why:** Prometheus is a scrape-and-store engine queried in-cluster — no reason
  to expose it. Grafana is the human view, so it gets an address.
- **Trade-off:** A public Grafana with `admin/admin123` is a security hole —
  flagged explicitly in [../security/README.md](../security/README.md) as
  harden-before-exposure.

### Why VPA + Goldilocks instead of just picking numbers
- **Decision:** Measure with VPA, visualize with Goldilocks, then set requests.
- **Why:** The recurring theme: **you cannot derive the right pod size from the
  node's spec.** It depends on real runtime behaviour under real traffic. VPA
  measures it; Goldilocks makes it a dashboard a human acts on.
- **Trade-off:** Extra components to run. Accepted — the alternative is guessing,
  then paying for the guess in wasted capacity or OOM kills.

### Why Velero on a stateless app
- **Decision:** Daily Velero backup of cluster *objects* to S3.
- **Why:** The app is stateless, but the *cluster configuration* is not
  disposable — namespaces, RBAC, Ingress, the monitoring stack. Velero makes
  "recreate the cluster" a restore instead of hand-rebuilding.
- **Trade-off:** S3 cost + an IRSA role. Negligible against the hours saved in a
  real DR event.

### Why EKS (managed control plane) over self-hosting
- **Decision:** EKS.
- **Why:** AWS runs the API server, scheduler, controller-manager, and etcd with
  HA and patching for ~\$0.10/hr. Self-hosting the control plane is a full-time
  job and a much larger blast radius.
- **Trade-off:** The ~\$0.10/hr control-plane fee and AWS lock-in for the managed
  pieces. Accepted for anything beyond a throwaway local cluster.

---

## Decisions still open (honest backlog)
- App `/metrics` endpoint (wire up `prometheus-fastapi-instrumentator`) — the
  `ServiceMonitor` already exists and waits for it.
- Move Grafana credentials to a Secret; put Grafana behind the ALB with auth.
- `runAsNonRoot` + a non-root base image (the current image runs as root).
- Terraform the cluster + IRSA roles so the whole platform is reproducible from
  code (today the Helm values carry `<ACCOUNT_ID>`/`<VPC_ID>` placeholders).

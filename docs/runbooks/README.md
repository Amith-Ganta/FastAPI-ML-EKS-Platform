# Runbooks

Incident response, written to be followed at 3am. Each runbook: **symptom →
first look → likely causes → fix → confirm**. Commands assume `kubectl` context
is set to `insurance-cluster` and the app is in `default`.

The golden first three commands for *any* pod incident:

```bash
kubectl get pods -o wide                 # state + node + restarts
kubectl describe pod <pod>               # Events section is usually the answer
kubectl logs <pod> --previous            # logs from the crashed container
```

**Index**
- [Scale the service up/down](#scale-the-service)
- [Deploy a new version](#deploy-a-new-version)
- [Roll back a bad deploy](#roll-back-a-bad-deploy)
- [CrashLoopBackOff](#crashloopbackoff)
- [ImagePullBackOff / ErrImagePull](#imagepullbackoff--errimagepull)
- [Pod stuck Pending](#pod-stuck-pending)
- [Node NotReady / node failure](#node-notready--node-failure)
- [LoadBalancer stuck `<pending>`](#loadbalancer-stuck-pending)
- [Service not routing / 503s](#service-not-routing--503s)
- [HPA not scaling](#hpa-not-scaling)
- [Prometheus targets down](#prometheus-targets-down)
- [Grafana unreachable](#grafana-unreachable)

---

## Scale the service

**When:** planned load change, or overriding the HPA temporarily.

```bash
# Check current state first
kubectl get hpa insurance-api
kubectl get deploy insurance-api

# Temporary manual override (HPA will fight you back toward its target):
kubectl scale deploy insurance-api --replicas=5

# Preferred: change the HPA bounds instead, so autoscaling stays in charge
kubectl patch hpa insurance-api --type merge \
  -p '{"spec":{"minReplicas":3,"maxReplicas":15}}'
```

> Manually scaling a Deployment that has an HPA is a temporary measure only — the
> HPA reconciles back to its computed value within a sync period. Change the HPA,
> not the Deployment, for anything lasting.

**Confirm:** `kubectl get pods -w` until the new count is `Running` + `Ready`.

---

## Deploy a new version

```bash
# The image is validated upstream; deploy = point at the new tag
kubectl set image deploy/insurance-api \
  insurance-api=tweakster24/insurance-premium-api:<newtag>

kubectl rollout status deploy/insurance-api   # blocks until healthy or fails
```

`maxUnavailable: 0` guarantees no capacity dip; `maxSurge: 1` adds one pod at a
time. If `rollout status` hangs, the new pods are failing readiness — jump to
[CrashLoopBackOff](#crashloopbackoff).

---

## Roll back a bad deploy

```bash
kubectl rollout history deploy/insurance-api          # list revisions
kubectl rollout undo deploy/insurance-api             # to previous
kubectl rollout undo deploy/insurance-api --to-revision=3
kubectl rollout status deploy/insurance-api
```

This works because each rollout created a new ReplicaSet and the old ones are
retained at 0 replicas — rollback just scales the old one back up.

---

## CrashLoopBackOff

**Symptom:** `STATUS = CrashLoopBackOff`, `RESTARTS` climbing.

```bash
kubectl describe pod <pod>            # Events + Last State: Terminated reason/exit
kubectl logs <pod> --previous        # why the last run died
```

| Likely cause | Tell | Fix |
|---|---|---|
| App throws on startup (bad model load, missing dep) | Traceback in `--previous` logs | Fix image; redeploy validated tag |
| Liveness probe too aggressive | `Killing` events before app is up | Ensure `startupProbe` covers cold start (it does here — 60s) |
| OOMKilled | `Last State: OOMKilled` | Raise memory limit (check VPA rec) |
| Wrong port / probe path | Probe `connection refused` | Confirm container listens on 8000, `/health` exists |

**Confirm:** `RESTARTS` stops climbing; `kubectl get pod <pod>` → `Running`.

---

## ImagePullBackOff / ErrImagePull

**Symptom:** pod stuck pulling the image.

```bash
kubectl describe pod <pod>   # Events show the exact pull error
```

| Cause | Fix |
|---|---|
| Wrong image/tag | Confirm it's `tweakster24/insurance-premium-api:latest` (the validated image) — a typo'd name is the #1 cause |
| Private registry, no auth | Add an `imagePullSecret` (not needed for this public image) |
| Rate limited / registry down | Retry; check Docker Hub status |
| Node has no internet egress | Check node's NAT/route (see [node runbook](#node-notready--node-failure)) |

**Confirm:** `kubectl get pod <pod>` leaves `ImagePullBackOff` for `Running`.

---

## Pod stuck Pending

**Symptom:** pod never leaves `Pending`.

```bash
kubectl describe pod <pod>   # Events: "0/2 nodes are available: ..."
kubectl get nodes
kubectl describe node <node> | sed -n '/Allocated resources/,/Events/p'
```

| Message | Meaning | Fix |
|---|---|---|
| `Insufficient cpu/memory` | Requests don't fit any node | Cluster Autoscaler should add a node; if not, see [HPA/CA](#hpa-not-scaling). Or lower requests (VPA rec). |
| `too many pods` | Hit `t3.small` ~11-pod IP ceiling | Add a node (CA) or larger instance |
| `node(s) had untolerated taint` | No tolerating node | Add toleration or untaint |
| CA not adding nodes | IRSA/ASG-tag misconfig | Check `kubectl -n kube-system logs deploy/cluster-autoscaler` |

**Confirm:** pod schedules and reaches `Running`.

---

## Node NotReady / node failure

```bash
kubectl get nodes
kubectl describe node <node>          # Conditions: MemoryPressure/DiskPressure/Ready
kubectl get pods -o wide | grep <node>
```

- Kubernetes evicts and reschedules the node's pods after the eviction timeout —
  this is why `replicas: 2` spread across nodes matters.
- **Fix:** in a managed node group, cordon + drain and let the ASG replace it:
  ```bash
  kubectl cordon <node>
  kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
  # terminate the EC2 instance; the ASG launches a replacement
  ```

**Confirm:** replacement node `Ready`; pods rescheduled and `Ready`.

---

## LoadBalancer stuck `<pending>`

**Symptom:** `kubectl get svc` shows `EXTERNAL-IP = <pending>` (or an Ingress has
no address).

```bash
kubectl describe svc <svc>
kubectl -n kube-system logs deploy/aws-load-balancer-controller
kubectl describe ingress <ingress>
```

| Cause | Fix |
|---|---|
| AWS LB Controller not installed/healthy | Install/repair it (see `k8s/ingress/`) |
| IRSA role missing/insufficient | Controller logs show `AccessDenied` → fix the IAM role trust + policy |
| Subnets not tagged for ELB discovery | Tag public subnets `kubernetes.io/role/elb=1` |
| Wrong `vpcId` in Helm values | Set the real VPC ID (placeholder `<VPC_ID>`) |

**Confirm:** an ALB DNS name appears; `curl` it on `/health`.

---

## Service not routing / 503s

**Symptom:** LB/ALB is up but requests 503 or hang.

```bash
kubectl get endpoints insurance-api-service   # <-- MOST IMPORTANT: is it empty? (Service is *-service)
kubectl get pods -l app=insurance-api
kubectl describe svc insurance-api-service     # selector vs pod labels
```

| Finding | Meaning | Fix |
|---|---|---|
| `ENDPOINTS` empty | No **Ready** pods behind the Service | readiness failing → [CrashLoopBackOff](#crashloopbackoff) |
| Selector ≠ pod labels | Service points at nothing | Align `spec.selector` with pod labels |
| Endpoints present, still 503 | ALB target-group health failing | Check `healthcheck-path: /health` annotation + SG rules |
| targetPort mismatch | Traffic to wrong port | Service `targetPort` must be `8000` |

> `kubectl get endpoints` is the fastest way to answer "is this a routing problem
> or a pod-health problem?" Empty endpoints = pod problem, not a Service problem.

---

## HPA not scaling

**Symptom:** load is high but replicas don't increase (or `TARGETS` shows
`<unknown>`).

```bash
kubectl get hpa insurance-api            # TARGETS column
kubectl describe hpa insurance-api       # Events + conditions
kubectl top pods                         # does Metrics Server work at all?
```

| Finding | Cause | Fix |
|---|---|---|
| `TARGETS: <unknown>` | Metrics Server broken/missing | Install/repair Metrics Server; `kubectl top pods` must work |
| No `resources.requests.cpu` | HPA can't compute % of nothing | Ensure the Deployment sets a CPU **request** (it does: 25m) |
| Already at `maxReplicas` | Hit the ceiling | Raise `maxReplicas`; check nodes have room (CA) |
| Pods Pending after scale | No node capacity | [Pod stuck Pending](#pod-stuck-pending) → Cluster Autoscaler |

**Confirm:** `kubectl get hpa -w` shows replicas rising as CPU exceeds 50%.

---

## HPA drift

**Symptom:** `kubectl get hpa` shows a `MAXPODS` (or min) value that disagrees
with `k8s/autoscaling/hpa.yaml`. Observed once as live `MAXPODS 20` vs the
committed `maxReplicas: 10` — the running HPA had been patched out of band.

```bash
# See the live value vs the manifest
kubectl get hpa insurance-api -o jsonpath='{.spec.maxReplicas}{"\n"}'
grep maxReplicas k8s/autoscaling/hpa.yaml
```

Git is the source of truth. Reconcile one of two ways:

```bash
# A) revert the cluster to the manifest (10)
kubectl apply -f k8s/autoscaling/hpa.yaml

# B) OR adopt the higher ceiling deliberately — edit the manifest, commit, apply
#    (remember: t3.small holds ~11 pods, so >10 needs the Cluster Autoscaler to
#     add a node; see the sizing note in hpa.yaml before raising it)
```

**Confirm:** the two values above match after reconciling.

---

## Prometheus targets down

```bash
kubectl -n monitoring get pods
kubectl -n monitoring port-forward svc/prometheus-operated 9090:9090
# open http://localhost:9090/targets  → which target is DOWN and why
```

| Cause | Fix |
|---|---|
| App target down because no `/metrics` | **Expected today** — the app doesn't expose `/metrics` yet (see honesty note). Cluster metrics still flow via node-exporter/kube-state-metrics. |
| ServiceMonitor label mismatch | ServiceMonitor selector must match the Service's labels + the release's `serviceMonitorSelector` |
| Scrape network blocked | Check NetworkPolicy / SG between Prometheus and target |

---

## Grafana unreachable

```bash
kubectl -n monitoring get svc | grep grafana
kubectl -n monitoring get pods -l app.kubernetes.io/name=grafana
kubectl -n monitoring logs deploy/monitoring-grafana
```

- No external IP → same path as [LoadBalancer pending](#loadbalancer-stuck-pending).
- Reachable but login fails → default is `admin` / `admin123` (flagged for
  hardening in [../security/README.md](../security/README.md)).
- Fast local access without exposing it:
  ```bash
  kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80
  ```

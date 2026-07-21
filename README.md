# Insurance-Premium Inference Platform on Kubernetes (EKS)

A production-style Kubernetes platform that runs a machine-learning inference
service on Amazon EKS: horizontal and vertical autoscaling, node autoscaling,
consolidated L7 ingress, a full metrics stack, right-sizing, and
disaster-recovery backups. The ML service is the *workload*. The point of this
repository is the **platform** around it, the layer that keeps that workload
available, right-sized, and observable while load changes underneath it.

[![CI/CD Pipeline](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF.svg?logo=githubactions&logoColor=white)](.github/workflows/deploy.yml)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-EKS-326CE5.svg?logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![Docker Image](https://img.shields.io/badge/Docker_Hub-tweakster24%2Finsurance--premium--api-2496ED.svg?logo=docker&logoColor=white)](https://hub.docker.com/r/tweakster24/insurance-premium-api)
[![Prometheus](https://img.shields.io/badge/Metrics-Prometheus-E6522C.svg?logo=prometheus&logoColor=white)](https://prometheus.io/)
[![Grafana](https://img.shields.io/badge/Dashboards-Grafana-F46800.svg?logo=grafana&logoColor=white)](https://grafana.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## The problem this platform solves

An ML inference endpoint is not "done" the moment the container runs. In
production it has to survive the things that actually take services down.
Each of those pressures maps to a specific piece of this platform:

| Real-world pressure | What breaks without a platform | How this repo addresses it |
|---|---|---|
| **Traffic is spiky** (inference load arrives in bursts) | A fixed replica count is wasteful at idle and overwhelmed at peak | **HPA** scales replicas on live CPU (2 to 10) |
| **Right-sizing is unknown up front** | Guessed CPU/memory requests waste money or trigger OOM kills | **VPA + Goldilocks** measure real usage and recommend requests |
| **Pods need machines** | The HPA wants more pods, but every node is full → pods stuck `Pending` | **Cluster Autoscaler** grows and shrinks the node group |
| **A load balancer per service is expensive** | N services → N cloud load balancers → N bills | **Ingress + one shared ALB** routes by path |
| **You can't fix what you can't see** | Latency, error-rate, and OOM regressions slip by silently | **Prometheus + Grafana** store and visualize the time series |
| **Clusters and their config get lost** | Namespaces, RBAC, and Ingress rebuilt by hand after a loss | **Velero** backs up cluster state to S3 daily |
| **A bad image reaching prod** | A broken build takes the live service down | **CI** smoke-tests `/health` + `/predict` before any deploy |

The design philosophy throughout is **measure, then decide.** Node specs alone
never tell you the right pod size or replica count; only real traffic does.
That is why the autoscaling and observability layers exist here instead of a
hand-tuned static config that is stale the day it ships.

---

## Platform architecture

> Larger, layer-by-layer diagrams live in [docs/diagrams/](docs/diagrams/):
> request lifecycle, autoscaling decision flow, scheduling, control-plane
> interaction, the monitoring pipeline, and more.

---

## The stack at a glance

| Layer | Component | Role | Manifest / values |
|---|---|---|---|
| Workload | Deployment + Service | 2+ replicas of the inference API behind a stable ClusterIP | [`k8s/base/`](k8s/base/) |
| Horizontal scaling | HorizontalPodAutoscaler | Replicas by live CPU (target 50%, 2 to 10) | [`k8s/autoscaling/hpa.yaml`](k8s/autoscaling/hpa.yaml) |
| Right-sizing | VerticalPodAutoscaler | Recommends requests (advice-only, `updateMode: Off`) | [`k8s/autoscaling/vpa.yaml`](k8s/autoscaling/vpa.yaml) |
| Node scaling | Cluster Autoscaler | Grows and shrinks the EC2 node group | [`k8s/autoscaling/cluster-autoscaler-values.yaml`](k8s/autoscaling/cluster-autoscaler-values.yaml) |
| Edge | Ingress + AWS LB Controller | One shared ALB, L7 path routing | [`k8s/ingress/`](k8s/ingress/) |
| Metrics | kube-prometheus-stack | Prometheus (internal) + Grafana (LoadBalancer) | [`k8s/observability/kube-prometheus-stack-values.yaml`](k8s/observability/kube-prometheus-stack-values.yaml) |
| Right-sizing UI | Goldilocks | Renders VPA recommendations | [`k8s/observability/goldilocks-values.yaml`](k8s/observability/goldilocks-values.yaml) |
| DR | Velero | Daily backup of cluster state to S3 | [`k8s/backup/velero-schedule.yaml`](k8s/backup/velero-schedule.yaml) |
| Delivery | GitHub Actions | Smoke-test the validated image, then deploy | [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) |

**Validated image:** `tweakster24/insurance-premium-api:latest`, the single
image used across every layer above (Deployments, Service, LoadBalancer, HPA,
VPA, Prometheus, Grafana, Goldilocks, Ingress, load testing). Pinning one
validated image means a fresh clone reproduces the deployment with no
image-related drift or surprises.

---

## Documentation map

| Area | What's inside |
|---|---|
| [docs/architecture/](docs/architecture/) | Design rationale, request lifecycle, control-plane interaction |
| [docs/kubernetes/](docs/kubernetes/) | **Every K8s object explained: what it is and *why* it exists** |
| [docs/kubernetes/DESIGN_DECISIONS.md](docs/kubernetes/DESIGN_DECISIONS.md) | Production design decisions with trade-offs (why replicas=2, why HPA 50%, why ALB over NodePort, …) |
| [docs/monitoring/](docs/monitoring/) | Prometheus/Grafana architecture, the metrics pipeline, alerting |
| [docs/runbooks/](docs/runbooks/) | Step-by-step incident response (scaling, rollback, pod failures, node loss, …) |
| [docs/debugging/](docs/debugging/) | `kubectl` diagnostic playbook: what each command reveals during an incident |
| [docs/operations/](docs/operations/) | Daily / weekly / monthly health checks, DR, backup and restore |
| [docs/performance/](docs/performance/) | Load testing, autoscaling behaviour, resource optimization |
| [docs/security/](docs/security/) | IAM/IRSA least-privilege, RBAC, secrets, container hardening |
| [docs/diagrams/](docs/diagrams/) | The full set of large Mermaid diagrams |
| [docs/APP_README.md](docs/APP_README.md) | The original application README (the ML service itself) |

---

## Quick start

```bash
# 0. Prereqs: an EKS cluster (see docs/operations for eksctl / Terraform),
#    kubectl, helm, and the Metrics Server installed.

# 1. Core workload
kubectl apply -k k8s/base

# 2. Horizontal autoscaling
kubectl apply -f k8s/autoscaling/hpa.yaml

# 3. Ingress (requires the AWS Load Balancer Controller; see k8s/ingress/)
kubectl apply -f k8s/ingress/ingress.yaml

# 4. Observability (Helm)
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f k8s/observability/kube-prometheus-stack-values.yaml

# 5. Verify
kubectl get pods,svc,hpa
kubectl top pods
```

Prefer to see it run before touching a cluster? The same validated image runs
locally with one command:

```bash
docker run -p 8000:8000 tweakster24/insurance-premium-api:latest
# then open http://localhost:8000/docs
```

---

## Cluster evidence

Output from the live cluster (`insurance-cluster`, EKS v1.35, 2× t3.small in
`us-east-1`), captured 2026-07-21 while the cluster was idle. I've pasted the
terminal output inline so it's greppable; the Goldilocks recommendation is a
screenshot under `docs/images/goldilocks.png`.

The Ingress has a live AWS ALB address:

```console
$ kubectl get ingress -A
NAMESPACE   NAME           CLASS   HOSTS   ADDRESS                                                                 PORTS   AGE
default     main-ingress   alb     *       k8s-default-mainingr-1121e791af-713249520.us-east-1.elb.amazonaws.com   80      2d13h
```

Both replicas are Running, scheduled onto a worker node:

```console
$ kubectl get pods -o wide
NAME                             READY   STATUS    RESTARTS   AGE     IP               NODE                             NOMINATED NODE   READINESS GATES
insurance-api-76854984b5-lfhqk   1/1     Running   0          6h29m   192.168.54.113   ip-192-168-50-229.ec2.internal   <none>           <none>
insurance-api-76854984b5-pcplr   1/1     Running   0          6h29m   192.168.61.185   ip-192-168-50-229.ec2.internal   <none>           <none>
```

The HPA had been patched out of band to `maxReplicas: 20`. On a fixed 2-node
group with no Cluster Autoscaler that ceiling can't schedule, so I reverted it to
the committed `maxReplicas: 10` (see [Limitations](#limitations) and the
[HPA drift runbook](docs/runbooks/#hpa-drift)):

```console
$ kubectl apply -f k8s/autoscaling/hpa.yaml
horizontalpodautoscaler.autoscaling/insurance-api configured

$ kubectl get hpa insurance-api
NAME            REFERENCE                  TARGETS        MINPODS   MAXPODS   REPLICAS   AGE
insurance-api   Deployment/insurance-api   cpu: 12%/50%   2         10        2          2d16h
```

Idle reads ~12% of the 25m CPU request (about 3m actual draw), measured after
the Deployment was reconciled to the manifest. Before reconciliation the pods
carried a drifted 100m request, so an earlier capture showed a lower percentage
against the larger denominator.

Under load, I ran six concurrent pods flooding `/health`. The HPA read the CPU
continuously and held at 2 replicas, because utilisation plateaued just below the
50% target. That's the correct call, not a stuck autoscaler:

```console
$ kubectl get hpa insurance-api -w
NAME            REFERENCE                  TARGETS        MINPODS   MAXPODS   REPLICAS   AGE
insurance-api   Deployment/insurance-api   cpu: 46%/50%   2         10        2          2d15h
insurance-api   Deployment/insurance-api   cpu: 45%/50%   2         10        2          2d15h
insurance-api   Deployment/insurance-api   cpu: 47%/50%   2         10        2          2d15h
insurance-api   Deployment/insurance-api   cpu: 44%/50%   2         10        2          2d15h
insurance-api   Deployment/insurance-api   cpu: 46%/50%   2         10        2          2d15h
insurance-api   Deployment/insurance-api   cpu: 45%/50%   2         10        2          2d15h
...   (steady at 44-47% for ~2 min under 6 load pods, replicas held at 2)   ...
insurance-api   Deployment/insurance-api   cpu: 46%/50%   2         10        2          2d15h
```

`/health` is a trivial endpoint, and the per-pod CPU limit caps how hot each pod
runs, so even six flood pods only push utilisation to ~46%. Adding clients
doesn't raise the average past that. To see a real scale-out you'd hit a
CPU-heavy path like `POST /predict` (which runs the model) or lower the target.
This capture is the steady state: the HPA reads live CPU via Metrics Server and
correctly holds at 2 under sustained sub-threshold load.

Prometheus reports 21 of 21 scrape targets UP, queried via its HTTP API. That
covers the control plane (apiserver, kube-proxy), the kubelets and cAdvisor on
both nodes, DNS, and the exporters the dashboards read from (`node-exporter`,
`kube-state-metrics`):

```console
$ curl -s localhost:9090/api/v1/targets | jq -r '.data.activeTargets[] | "\(.health) \(.labels.job)"' | sort | uniq -c
ACTIVE TARGETS: 21   UP: 21   DOWN: 0

   6 up   kubelet                 (metrics + cadvisor + probes, ×2 nodes)
   2 up   apiserver
   2 up   coredns
   2 up   kube-proxy
   2 up   node-exporter
   2 up   alertmanager
   2 up   prometheus              (self-scrape, 2 ports)
   1 up   kube-state-metrics
   1 up   prometheus-operator
   1 up   grafana
```

`insurance-api` is not in that list. The app doesn't expose `/metrics` yet, so
there's no ServiceMonitor for it, which is why its target is absent. The
[Prometheus targets runbook](docs/runbooks/#prometheus-targets-down) documents
this: cluster metrics still flow through node-exporter and kube-state-metrics,
and the app target lights up the moment the app is instrumented.

Instead of a Grafana screenshot, here are the PromQL series behind the
*Kubernetes / Compute Resources / Cluster* dashboard, queried against Prometheus.
They line up with the 25m CPU / 256Mi request the deployment is sized to:

```console
Cluster CPU in use          : 0.23 / 4 cores        (~5.7%, idle cluster)
Cluster CPU requests reserved: 0.775 / 4 cores       (~19%, 21 pods' requests)
Cluster memory used         : 2.55 / 4.0 GB          (~64%, 2x t3.small)
insurance-api CPU (2 pods)  : 0.008 cores  (~8m)     → well under the 25m request
insurance-api memory (2 pods): 496 MB  (~248 MB/pod) → sits at the 256Mi request
Running pods (kube-state)   : 21
```

The metrics pipeline is live end to end (Prometheus scraping, Grafana wired to
it), and the app's footprint of ~8m CPU and ~248 MB/pod matches both the manifest
and the Goldilocks/VPA recommendation. So the 25m CPU request is headroom over a
real ~8m idle draw. Grafana is reachable on its LoadBalancer ALB; Prometheus is
ClusterIP-internal, so I reach it with a port-forward:

```bash
# Service/namespace names vary by install; find them first:
kubectl get svc -A | grep -Ei 'grafana|promet|goldi'

# Grafana: LoadBalancer ALB (EXTERNAL-IP), dashboard "Kubernetes / Compute Resources / Cluster"
kubectl -n prometheus get svc prometheus-grafana

# Prometheus: port-forward, then http://localhost:9090/targets
kubectl -n prometheus port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090

# Goldilocks: port-forward, then http://localhost:8080
kubectl -n goldilocks port-forward svc/goldilocks-dashboard 8080:80
```

---

## Limitations

What the platform does and doesn't do today:

- The service exposes `/health` and `/predict`, not `/metrics`. Cluster, node,
  and pod metrics flow via node-exporter and kube-state-metrics; app-level
  request metrics start showing up as soon as the app adds an instrumentator,
  which is what the `ServiceMonitor` is already wired for.
- The Helm `*-values.yaml` files carry environment-specific placeholders
  (`<ACCOUNT_ID>`, `<VPC_ID>`, IRSA role ARNs).
- `grafana admin/admin123` and a few other convenience defaults are flagged in
  [docs/security/](docs/security/) to harden before any public exposure.
- Known drift: the committed HPA (`k8s/autoscaling/hpa.yaml`) sets
  `maxReplicas: 10`, but I found a live cluster running `maxReplicas: 20` from a
  hand-patch. Git wins, so reconcile with `kubectl apply -f k8s/autoscaling/hpa.yaml`
  (back to 10), or bump the manifest to 20 if the higher ceiling is intended. See
  the [HPA drift runbook](docs/runbooks/#hpa-drift).

# Architecture

The design rationale for the platform, the end-to-end request lifecycle, and how
the control plane and worker nodes interact. This is the "why is it shaped this
way" document. The per-object reference lives in
[../kubernetes/COMPONENTS.md](../kubernetes/COMPONENTS.md), and the full visual
set is in [../diagrams/](../diagrams/).

---

## The one idea the whole platform is built on

> **You cannot derive the right runtime configuration from static specs. Only
> real traffic tells you the right replica count and pod size — so measure,
> then decide.**

Every layer is a direct consequence of that idea:

- Don't guess a replica count → **HPA** sets it from live CPU.
- Don't guess a pod size → **VPA + Goldilocks** measure and recommend it.
- Pods need machines you also can't pre-count → **Cluster Autoscaler**.
- You can't measure what you can't see → **Prometheus + Grafana**.
- You can't afford to lose the config you tuned → **Velero**.

The ML service is the *workload*. The platform is the part that keeps that
workload available, right-sized, and observable as load changes underneath it.

---

## Layered view

One diagram, every real relationship: the request path, the three autoscalers
acting on their *correct* targets, the observability pipeline, DR, and — the part
most diagrams wrongly leave floating — the **control plane actually managing the
cluster**. Solid arrows are the live request path; dashed arrows are
control/observe relationships, each labelled with what it really does.

```mermaid
flowchart TB
    CLIENT([Internet client])

    subgraph CP["Control plane (EKS-managed)"]
        API[kube-apiserver]
        ETCD[(etcd<br/>desired state)]
        SCH[scheduler]
        CM[controller-manager<br/>Deployment · ReplicaSet ·<br/>Service · HPA controllers]
        API <--> ETCD
        API --- SCH
        API --- CM
    end

    subgraph EDGE["Edge"]
        ALB[AWS ALB]
        ING[Ingress<br/>group.name: insurance-platform]
    end

    subgraph WORKLOAD["Workload (default ns)"]
        SVC[Service<br/>ClusterIP :80→8000]
        DEP[Deployment<br/>insurance-api]
        RS[ReplicaSet]
        PODS[Pods<br/>uvicorn:8000 ×2–10]
        DEP --> RS --> PODS
    end

    subgraph NODES["Worker nodes"]
        NG[Managed Node Group<br/>ASG · t3.small] -. launches .-> EC2[EC2 Nodes]
    end

    subgraph AUTOSCALE["Autoscaling controllers"]
        HPA[HPA<br/>count · CPU 50% · 2–10]
        VPA[VPA<br/>recommend-only]
        CA[Cluster Autoscaler]
    end

    subgraph OBSERVE["Observability"]
        MS[Metrics Server]
        PROM[Prometheus<br/>ClusterIP]
        GRAF[Grafana]
    end

    subgraph DR["Disaster recovery"]
        VELERO[Velero]
        S3[(S3<br/>7-day TTL)]
    end

    %% --- live request path (solid) ---
    CLIENT --> ALB --> ING --> SVC --> PODS

    %% --- control plane manages the cluster (dashed) ---
    CM -. reconciles .-> DEP
    SCH -. binds Pods to Nodes .-> EC2
    CM -. manages .-> EC2
    PODS -. run on .-> EC2

    %% --- autoscaling, each on its correct target ---
    MS -. pod CPU .-> HPA
    HPA -. scales .-> DEP
    VPA -. observes .-> PODS
    VPA -. recommends requests .-> DEP
    CA -. watches Pending Pods .-> PODS
    CA -. adjusts desired size .-> NG

    %% --- observability (Prometheus scrapes; Grafana reads) ---
    PROM -. scrapes .-> MS
    PROM -. scrapes .-> EC2
    PROM -. scrapes .-> PODS
    GRAF -. reads .-> PROM

    %% --- DR: Velero (not Prometheus) writes backups ---
    VELERO -. backs up objects .-> S3
    VELERO -. reads objects .-> API

    classDef cp fill:#EEF2FF,stroke:#6366F1,color:#1E1B4B;
    classDef work fill:#ECFDF5,stroke:#10B981,color:#064E3B;
    class API,ETCD,SCH,CM cp;
    class SVC,DEP,RS,PODS work;
```

**How to read it — the relationships reviewers check first:**

- **Request path is Client → ALB → Ingress → Service → Pods.** The ALB never
  wires straight to Pods; the Ingress (one shared ALB via `group.name`) sits
  between them, and the Service load-balances across *Ready* Pods only.
- **HPA scales the Deployment, not the Service and not the Pods directly.** It
  reads pod CPU from the **Metrics Server** and patches the Deployment's replica
  count; the Deployment owns the ReplicaSet, which owns the Pods.
- **Cluster Autoscaler does not create Pods.** It watches *Pending* Pods and, when
  they can't be scheduled, adjusts the **Managed Node Group's** ASG, which
  launches new **Nodes** — then the scheduler places the pending Pods.
- **VPA does not resize running Pods.** In `recommend-only` mode it *observes*
  Pods and writes request *recommendations* (a human applies them to the
  Deployment at the next deploy). It never fights the HPA on CPU.
- **The control plane manages the cluster.** `kubectl` talks to the
  **kube-apiserver**, which persists desired state in **etcd**; the
  **scheduler** binds Pods to Nodes and the **controller-manager** runs the
  Deployment/ReplicaSet/Service/HPA reconcile loops. Pods never call the control
  plane on the request path.
- **Observability flows one way:** Prometheus *scrapes* the Metrics Server, Nodes,
  and Pods; **Grafana reads Prometheus**. Backups are **Velero → S3** — Prometheus
  never writes to S3.

Three autoscalers, three non-overlapping dimensions — HPA (how many pods), VPA
(how big each pod), Cluster Autoscaler (how many nodes) — none steps on another's
decision.

---

## Request lifecycle (narrative)

1. A client hits the **ALB** (provisioned from the Ingress by the AWS Load
   Balancer Controller). The ALB has already dropped unhealthy targets via its
   health check on `/health`, so traffic only reaches pods that can serve it.
2. The ALB forwards to the **Service** (ClusterIP). The Service load-balances
   only across **Ready** pods — the `readinessProbe` decides membership, so a
   pod that is still warming up never receives a request.
3. **kube-proxy** DNATs the Service virtual IP to a concrete pod IP.
4. The **pod** (`uvicorn` on port 8000) runs the model in-memory and returns the
   prediction (`predicted_category` + confidence + class probabilities).
5. Throughout, the `liveness` and `readiness` probes run in parallel, and the
   **Metrics Server** samples CPU — the signal the **HPA** reads to decide
   whether to add or remove pods.

The step-by-step sequence diagram is
[diagram #1](../diagrams/README.md#1-request-lifecycle-client--prediction).

---

## Control-plane ⇄ node interaction

EKS runs the control plane (API server, scheduler, controller-manager, etcd) as
an AWS-managed, highly-available service for roughly \$0.10/hr. The pattern that
matters here:

> **Nothing issues imperative commands. Every component *watches* the API server
> and reconciles toward desired state.** `kubectl apply` only records intent in
> etcd; controllers and kubelets each notice the change and act independently.

That level-triggered, watch-and-reconcile model is exactly why the system
self-heals. A dead pod is not "recreated by a command" — the ReplicaSet
controller notices that reality has drifted from desired state and corrects it,
with no operator in the loop. See
[diagram #9](../diagrams/README.md#9-control-plane-interaction-what-happens-on-kubectl-apply).

---

## Why an EKS-managed control plane

Self-hosting etcd and the control plane is a full-time reliability job with a
large blast radius — a botched etcd upgrade or a lost quorum takes the whole
cluster with it. EKS trades a small hourly fee and some AWS coupling for an HA
control plane, managed patching, and a much smaller operational surface. For
anything beyond a throwaway local cluster, that is the right trade. The full
rationale and the alternatives considered are in
[../kubernetes/DESIGN_DECISIONS.md](../kubernetes/DESIGN_DECISIONS.md).

---

## Where the application ends and the platform begins

| Concern | Owned by | Lives in |
|---|---|---|
| Model, prediction logic, `/health`, `/predict` | The **app** (validated image) | [../APP_README.md](../APP_README.md) |
| Replicas, sizing, nodes, edge, metrics, DR | The **platform** | `k8s/` + these docs |

This separation is deliberate. The platform treats the image as an immutable,
validated black box and provides everything *around* it. That is why swapping the
app — or adding the `/metrics` endpoint — is an image change, not a platform
change: the manifests, autoscalers, and observability wiring stay exactly as they
are.

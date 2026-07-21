# Platform diagrams

Large Mermaid diagrams of every moving part. Each one answers a single "how does
*this* work?" question. They render natively on GitHub.

**Index**
1. [Request lifecycle](#1-request-lifecycle-client--prediction)
2. [Deployment / rollout flow](#2-deployment--rollout-flow)
3. [Kubernetes object hierarchy](#3-kubernetes-object-hierarchy)
4. [The three-layer autoscaling model](#4-the-three-layer-autoscaling-model)
5. [HPA decision loop](#5-hpa-decision-loop)
6. [VPA recommendation loop](#6-vpa-recommendation-loop)
7. [Cluster Autoscaler decision](#7-cluster-autoscaler-decision)
8. [Pod scheduling decision](#8-pod-scheduling-decision)
9. [Control-plane interaction](#9-control-plane-interaction-what-happens-on-kubectl-apply)
10. [Monitoring / metrics pipeline](#10-monitoring--metrics-pipeline)
11. [Ingress & load-balancer routing](#11-ingress--load-balancer-routing)
12. [Service networking (how a ClusterIP resolves to a pod)](#12-service-networking)
13. [Velero backup flow](#13-velero-backup-flow)
14. [CI/CD pipeline](#14-cicd-pipeline)

---

## 1. Request lifecycle (client → prediction)

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant ALB as ALB (from Ingress)
    participant SVC as Service (ClusterIP)
    participant KP as kube-proxy (iptables)
    participant POD as Pod (uvicorn:8000)
    participant M as Model (in-memory)

    C->>ALB: POST /predict {features}
    Note over ALB: L7 route by path,<br/>ALB health-check already<br/>excluded unhealthy targets
    ALB->>SVC: forward to Service VIP
    SVC->>KP: virtual IP lookup
    Note over KP: picks among *Ready* endpoints only<br/>(readinessProbe gates this set)
    KP->>POD: DNAT to a Ready pod IP
    POD->>M: model.predict(features)
    M-->>POD: predicted_category
    POD-->>C: 200 {predicted_category}
    Note over POD: liveness/readiness probes<br/>run continuously in parallel
```

---

## 2. Deployment / rollout flow

```mermaid
flowchart TB
    A["kubectl apply -k k8s/base<br/>(new image tag)"] --> B[kube-apiserver writes<br/>desired state to etcd]
    B --> C[Deployment controller<br/>sees spec change]
    C --> D[Creates a NEW ReplicaSet]
    D --> E{RollingUpdate<br/>maxUnavailable:0<br/>maxSurge:1}
    E --> F[Start 1 new pod<br/>surge above desired]
    F --> G{startupProbe<br/>passes?}
    G -- no, within window --> F
    G -- yes --> H{readinessProbe<br/>passes?}
    H -- yes --> I[New pod added to<br/>Service endpoints]
    I --> J[Scale OLD ReplicaSet down by 1]
    J --> K{All pods on<br/>new ReplicaSet?}
    K -- no --> F
    K -- yes --> L[Rollout complete<br/>old ReplicaSet kept at 0<br/>for rollback]

    L -. kubectl rollout undo .-> M[Scale old RS up,<br/>new RS down]
```

---

## 3. Kubernetes object hierarchy

```mermaid
flowchart TD
    NS[Namespace: default] --> DEP[Deployment: insurance-api]
    DEP --> RS[ReplicaSet<br/>revision N]
    RS --> P1[Pod]
    RS --> P2[Pod]
    P1 --> CT1[Container: uvicorn:8000]
    P2 --> CT2[Container: uvicorn:8000]

    SVC[Service: insurance-api<br/>ClusterIP] -. label selector .-> P1
    SVC -. label selector .-> P2

    HPA[HPA] -. scaleTargetRef .-> DEP
    VPA[VPA recommend-only] -. targetRef .-> DEP
    ING[Ingress] -. backend .-> SVC

    classDef owned fill:#ECFDF5,stroke:#10B981,color:#064E3B;
    classDef ctl fill:#EEF2FF,stroke:#6366F1,color:#1E1B4B;
    class DEP,RS,P1,P2,CT1,CT2,SVC owned;
    class HPA,VPA,ING ctl;
```

---

## 4. The three-layer autoscaling model

The single most important mental model in this repo: three controllers answering
three *different* questions, deliberately non-overlapping.

```mermaid
flowchart LR
    subgraph Q1["How MANY pods?"]
        HPA[HorizontalPodAutoscaler<br/>metric: CPU 50%<br/>range: 2-10]
    end
    subgraph Q2["Are there MACHINES for them?"]
        CA[Cluster Autoscaler<br/>trigger: Pending pods<br/>t3.small ≈ 11 pods/node]
    end
    subgraph Q3["How BIG each pod?"]
        VPA[VerticalPodAutoscaler<br/>mode: recommend-only<br/>feeds Goldilocks]
    end

    LOAD([Traffic rises]) --> HPA
    HPA -- more pods --> PENDING{Fit on<br/>current nodes?}
    PENDING -- no --> CA
    CA -- add EC2 node --> PENDING
    PENDING -- yes --> RUN([Pods Running])
    VPA -. advises request sizes<br/>that shape scheduling .-> PENDING
```

---

## 5. HPA decision loop

```mermaid
flowchart TB
    START([Every 15s sync]) --> M[Read pod CPU<br/>from Metrics Server]
    M --> C["desiredReplicas =<br/>ceil(current × currentCPU / 50%)"]
    C --> UP{desired ><br/>current?}
    UP -- yes --> USTAB[scaleUp window 15s<br/>up to +100% per 30s]
    USTAB --> APPLY[Patch Deployment replicas]
    UP -- no --> DOWN{desired <<br/>current?}
    DOWN -- yes --> DSTAB[scaleDown window 300s<br/>≤50% per 60s<br/>anti-flap]
    DSTAB --> APPLY
    DOWN -- no --> HOLD([No change])
    APPLY --> CLAMP{Within<br/>min 2 / max 10?}
    CLAMP -- clamp --> HOLD
```

---

## 6. VPA recommendation loop

```mermaid
flowchart LR
    HIST[VPA recommender<br/>watches real usage] --> REC["Compute target /<br/>lowerBound / upperBound<br/>per container"]
    REC --> MODE{updateMode}
    MODE -- "Off (here)" --> STORE[Store recommendation<br/>in VPA object]
    STORE --> GOLD[Goldilocks reads it] --> HUMAN[Human applies at<br/>next deploy]
    MODE -- "Auto (NOT used)" --> EVICT[Would evict + resize pods]

    classDef danger fill:#FEF2F2,stroke:#EF4444,color:#7F1D1D;
    class EVICT danger;
```

> `Auto` is drawn only to show the road *not* taken. On a 2-node cluster,
> eviction-to-resize is too disruptive, and it collides with the HPA on CPU.

---

## 7. Cluster Autoscaler decision

```mermaid
flowchart TB
    W([Watch for<br/>unschedulable pods]) --> Q{Any pod<br/>Pending for<br/>lack of capacity?}
    Q -- no --> IDLE{Any node<br/>underused >5min<br/>and drainable?}
    IDLE -- yes --> REMOVE[Cordon, drain,<br/>terminate node]
    IDLE -- no --> W
    Q -- yes --> SIM[Simulate: would a new<br/>node let it schedule?]
    SIM -- no --> GIVEUP[Emit event;<br/>pod stays Pending]
    SIM -- yes --> EXP{expander:<br/>least-waste}
    EXP --> ADD[Increase ASG desired<br/>→ new EC2 node joins]
    ADD --> SCHED[Scheduler places<br/>the Pending pod]
```

---

## 8. Pod scheduling decision

```mermaid
flowchart TB
    NEW([New pod: Pending]) --> FILTER[FILTER nodes:<br/>enough CPU/mem request?<br/>taints tolerated?<br/>affinity satisfied?<br/>free pod-IP slot?]
    FILTER --> FEAS{≥1 feasible<br/>node?}
    FEAS -- no --> PEND[Stay Pending<br/>→ wakes Cluster Autoscaler]
    FEAS -- yes --> SCORE[SCORE feasible nodes:<br/>least-loaded, spread,<br/>image locality]
    SCORE --> BIND[Bind pod → node<br/>write to etcd]
    BIND --> KUBELET[kubelet on that node<br/>pulls image, starts container]
    KUBELET --> PROBE[startup→readiness→liveness]
```

> The `FILTER` step keys on **requests**, not usage, which is exactly why the
> `25m`/`256Mi` requests (and the VPA that tunes them) directly control density.

---

## 9. Control-plane interaction (what happens on `kubectl apply`)

```mermaid
sequenceDiagram
    autonumber
    participant U as kubectl
    participant API as kube-apiserver
    participant ETCD as etcd
    participant DC as Deployment controller
    participant RC as ReplicaSet controller
    participant SCH as scheduler
    participant KL as kubelet (node)

    U->>API: apply Deployment (desired state)
    API->>ETCD: persist object
    API-->>U: 200 accepted
    DC->>API: watch → sees new Deployment
    DC->>API: create ReplicaSet
    RC->>API: watch → create N Pods (Pending)
    SCH->>API: watch → find node, bind pod
    API->>ETCD: record binding
    KL->>API: watch → pod bound to me
    KL->>KL: pull image, start container, run probes
    KL->>API: status: Running/Ready
    API->>ETCD: persist status
```

> Note there is no central orchestrator issuing commands. Every component
> **watches** the API server and reconciles independently. That's the level-
> triggered controller pattern the whole platform is built on.

---

## 10. Monitoring / metrics pipeline

```mermaid
flowchart LR
    subgraph Sources
        NE[node-exporter<br/>per-node OS metrics]
        KSM[kube-state-metrics<br/>object state]
        APP["app /metrics<br/>(planned)"]
    end
    NE --> PROM[Prometheus<br/>ClusterIP, 7d retention]
    KSM --> PROM
    APP -. ServiceMonitor<br/>already wired .-> PROM
    PROM --> GRAF[Grafana<br/>LoadBalancer<br/>~25 dashboards]
    PROM --> ALERT[Alertmanager<br/>rules → routes]

    MS[Metrics Server] --> HPA[HPA / kubectl top]
    note1["Two separate metric paths:<br/>Metrics Server = live, for scaling<br/>Prometheus = history, for humans"]

    classDef planned fill:#FFFBEB,stroke:#F59E0B,color:#78350F;
    class APP planned;
```

---

## 11. Ingress & load-balancer routing

```mermaid
flowchart TB
    ING["Ingress object<br/>group.name: insurance-platform"] --> CTRL[AWS Load Balancer Controller]
    CTRL -- reconciles --> ALB[One shared ALB]
    ALB --> R{path routing}
    R -- "/" --> SVC1[Service: insurance-api]
    R -- "/grafana (optional)" --> SVC2[Service: grafana]
    SVC1 --> PODS[insurance-api pods]

    classDef note fill:#F0FDF4,stroke:#10B981;
    N["Without Ingress:<br/>each Service = its own ELB = its own bill.<br/>group.name collapses them onto ONE ALB."]:::note
    ALB -.-> N
```

---

## 12. Service networking

How a name becomes a pod, with no pod IP ever hardcoded.

```mermaid
sequenceDiagram
    participant APP as Caller in cluster
    participant DNS as CoreDNS
    participant SVC as Service VIP
    participant KP as kube-proxy
    participant EP as Endpoints (Ready pods)

    APP->>DNS: resolve insurance-api.default.svc.cluster.local
    DNS-->>APP: ClusterIP (virtual)
    APP->>SVC: connect to ClusterIP:80
    SVC->>KP: iptables/IPVS rule
    KP->>EP: pick a Ready endpoint
    EP-->>APP: connection to pod:8000
    Note over EP: readinessProbe adds/removes<br/>pods from this set live
```

---

## 13. Velero backup flow

```mermaid
flowchart LR
    SCHED["Velero Schedule<br/>daily 03:00 UTC"] --> BK[Backup job]
    BK --> API[Query kube-apiserver<br/>for objects in<br/>default / monitoring / kube-system]
    API --> OBJ[Serialize: namespaces,<br/>RBAC, ConfigMaps, Secrets,<br/>Ingress, Deployments]
    OBJ --> S3[(S3 bucket<br/>ttl 168h / 7 days)]
    S3 -. velero restore .-> NEW[Rebuild objects<br/>on a fresh cluster]
    note["snapshotVolumes: false:<br/>the app is stateless,<br/>we back up CONFIG not disks"]
```

---

## 14. CI/CD pipeline

```mermaid
flowchart TB
    PUSH([git push / PR]) --> PULL[Pull validated image<br/>tweakster24/insurance-premium-api:latest]
    PULL --> RUN[docker run the image]
    RUN --> W{/docs reachable?}
    W -- no --> FAIL[Fail the build]
    W -- yes --> SMOKE[POST /predict<br/>assert predicted_category]
    SMOKE -- assertion fails --> FAIL
    SMOKE -- ok --> TEARDOWN[Stop container]
    TEARDOWN --> GATE{main branch +<br/>AWS_* secrets set?}
    GATE -- no --> DONE([CI green, no deploy])
    GATE -- yes --> SSH[ssh deploy to EC2<br/>appleboy/ssh-action]
    SSH --> DONE
```

> The pipeline never *builds* the app image. It consumes the **validated**
> `tweakster24` image and gates deployment on a real prediction succeeding.

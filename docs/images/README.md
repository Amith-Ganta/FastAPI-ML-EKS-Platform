# Screenshots

Drop real captures here with these exact filenames and they render in the
top-level [README](../../README.md#screenshots).

| Filename | What to capture | Command |
|---|---|---|
| `loadbalancer.png` | The ALB/LoadBalancer address (ADDRESS column) | `kubectl get ingress -A` |
| `kubectl-pods.png` | `kubectl get pods -o wide` mid scale-out (extra pods appearing) | `kubectl get pods -o wide -w` |
| `hpa-scaling.png` | REPLICAS climbing during a load test | `kubectl get hpa -w` |
| `grafana-dashboard.png` | A cluster dashboard showing CPU/memory | `kubectl -n monitoring port-forward svc/grafana 3000:80` → `localhost:3000` |
| `prometheus-targets.png` | Prometheus `/targets` page (UP targets) | `kubectl -n monitoring port-forward svc/prometheus-server 9090:80` → `localhost:9090/targets` |
| `goldilocks.png` | Goldilocks VPA recommendation for `insurance-api` | `kubectl -n goldilocks port-forward svc/goldilocks-dashboard 8080:80` → `localhost:8080` |

Service/namespace names vary by install — find yours first with
`kubectl get svc -A | grep -Ei 'grafana|promet|goldi'`.

Tips:
- Capture during an actual load test (see [../performance/](../performance/)) so
  the HPA/pods screenshots show real scaling, not an idle cluster.
- Terminal screenshots are more convincing than diagrams here — they show the
  real cluster responded.
- The top-level [README screenshot table](../../README.md#screenshots) tracks
  which of the six are in the repo (✅) vs still pending (⬜) — flip the marker
  when you add a PNG.

# Screenshots

Drop real captures here with these exact filenames and they render in the
top-level [README](../../README.md#screenshots).

| Filename | What to capture |
|---|---|
| `grafana-dashboard.png` | A kube-prometheus-stack cluster dashboard showing CPU/memory |
| `prometheus-targets.png` | Prometheus `/targets` page (UP targets) |
| `goldilocks.png` | Goldilocks dashboard with a VPA recommendation for `insurance-api` |
| `hpa-scaling.png` | `kubectl get hpa -w` (or a Grafana replica-count panel) during load |
| `kubectl-pods.png` | `kubectl get pods -o wide` mid scale-out (extra pods appearing) |
| `loadbalancer.png` | The ALB/LoadBalancer address, or the app's `/docs` reached through it |

Tips:
- Capture during an actual load test (see [../performance/](../performance/)) so
  the HPA/pods screenshots show real scaling, not an idle cluster.
- Terminal screenshots are more convincing than diagrams here — they show the
  real cluster responded.

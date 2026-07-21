# Load test

Drive traffic at the service to watch the autoscaling layers react. See
[../docs/performance/](../docs/performance/) for what to expect and the timeline
of a scale-out.

## In-cluster, one-liner (no local install)

Runs [`hey`](https://github.com/rakyll/hey) as a throwaway pod against the
Service by DNS name:

```bash
kubectl run loadgen --rm -it --image=williamyeh/hey --restart=Never -- \
  -z 5m -c 50 -m POST \
  -H 'Content-Type: application/json' \
  -d @- \
  http://insurance-api.default.svc.cluster.local/predict <<'JSON'
{"age":40,"weight":72,"height":1.75,"income_lpa":12,"smoker":false,"city":"Mumbai","occupation":"private_job"}
JSON
```

## Watch it scale (separate terminals)

```bash
kubectl get hpa insurance-api -w     # TARGETS % and replica count climb
kubectl get pods -w                  # new pods appear and go Ready
kubectl top pods                     # per-pod CPU vs the 50% target
```

## Local (against a port-forward or the ALB)

```bash
# Port-forward the Service, then load the local port:
kubectl port-forward svc/insurance-api 8080:80 &
./run.sh http://localhost:8080
```

`run.sh` is a thin wrapper; edit the target URL and concurrency to taste.

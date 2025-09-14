# IoT Telemetry Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the IoT Telemetry system.

## Prerequisites

- Kubernetes cluster (v1.19+)
- kubectl configured to access your cluster
- Docker images built and pushed to your registry
- (Optional) Prometheus Operator for metrics collection
- (Optional) NGINX Ingress Controller for external access

## Architecture

The deployment includes:

- **ingestion-api**: FastAPI service for receiving telemetry data
- **aggregator-worker**: Kafka consumer that aggregates sensor data
- **alerts-worker**: Kafka consumer that monitors for threshold violations
- **dashboard-api**: FastAPI service for serving telemetry data and alerts

## Quick Start

1. **Build and push Docker images:**
   ```bash
   # From project root
   docker build -t liro/ingestion-api:latest -f ingestion-api/Dockerfile .
   docker build -t liro/aggregator-worker:latest -f aggregator-worker/Dockerfile .
   docker build -t liro/alerts-worker:latest -f alerts-worker/Dockerfile .
   docker build -t liro/dashboard-api:latest -f dashboard-api/Dockerfile .
   
   # Push to your registry
   docker push liro/ingestion-api:latest
   docker push liro/aggregator-worker:latest
   docker push liro/alerts-worker:latest
   docker push liro/dashboard-api:latest
   ```

2. **Deploy to Kubernetes:**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. **Or deploy manually:**
   ```bash
   kubectl apply -f namespace.yaml
   kubectl apply -f configmap.yaml
   kubectl apply -f ingestion-api.yaml
   kubectl apply -f aggregator-worker.yaml
   kubectl apply -f alerts-worker.yaml
   kubectl apply -f dashboard-api.yaml
   kubectl apply -f servicemonitor.yaml  # Optional: for Prometheus
   ```

## Configuration

### Environment Variables

The deployment uses a ConfigMap for shared configuration. Key settings:

- **Kafka**: `KAFKA_BOOTSTRAP_SERVERS=kafka.kafka:9092`
- **MongoDB**: `MONGO_URL=mongodb://mongodb.default:27017`
- **Alert Thresholds**: Configurable via environment variables

### Resource Limits

Each service has resource requests and limits:
- **Requests**: 100m CPU, 128Mi memory
- **Limits**: 500m CPU, 512Mi memory

### Scaling

- **ingestion-api**: 2 replicas (HPA: 2-10 replicas, CPU 60%, Memory 70%)
- **aggregator-worker**: 1 replica (HPA: 1-5 replicas, CPU 50%, Memory 70%)
- **alerts-worker**: 1 replica (no HPA - single instance for consistency)
- **dashboard-api**: 2 replicas (HPA: 2-8 replicas, CPU 50%, Memory 70%)

### Horizontal Pod Autoscaler (HPA)

The deployment includes HPA for automatic scaling based on resource utilization:

- **CPU-based scaling**: Monitors CPU utilization and scales when thresholds are exceeded
- **Memory-based scaling**: Monitors memory utilization for additional scaling triggers
- **Scaling behavior**: Configurable scale-up and scale-down policies to prevent thrashing

## Monitoring

### Health Checks

All services include:
- **Readiness probes**: Check if service is ready to receive traffic
- **Liveness probes**: Check if service is healthy

### Prometheus Metrics

All services expose Prometheus metrics on `/metrics`:
- **ingestion-api**: Telemetry ingestion metrics
- **aggregator-worker**: Message processing and aggregation metrics
- **alerts-worker**: Alert processing metrics
- **dashboard-api**: API request metrics

### ServiceMonitor

If Prometheus Operator is installed, ServiceMonitor resources are included for automatic metrics collection.

## Access

### Ingress

The deployment includes Ingress resources for external access:
- **API**: `http://api.iot.local`
- **Dashboard**: `http://dashboard.iot.local`

Add these to your `/etc/hosts` file:
```
127.0.0.1 api.iot.local
127.0.0.1 dashboard.iot.local
```

### Port Forwarding

For direct access without Ingress:
```bash
# Ingestion API
kubectl port-forward -n iot svc/ingestion-api 8001:80

# Dashboard API
kubectl port-forward -n iot svc/dashboard-api 8002:80

# Aggregator Worker Metrics
kubectl port-forward -n iot svc/aggregator-worker 8003:8000

# Alerts Worker Metrics
kubectl port-forward -n iot svc/alerts-worker 8004:8000
```

## Dependencies

The deployment assumes external dependencies:
- **Kafka**: Running in `kafka` namespace
- **MongoDB**: Running in `default` namespace
- **Prometheus**: For metrics collection (optional)

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n iot
kubectl describe pod <pod-name> -n iot
```

### Check Logs
```bash
kubectl logs -f deployment/ingestion-api -n iot
kubectl logs -f deployment/aggregator-worker -n iot
kubectl logs -f deployment/alerts-worker -n iot
kubectl logs -f deployment/dashboard-api -n iot
```

### Check Services
```bash
kubectl get services -n iot
kubectl get ingress -n iot
kubectl get hpa -n iot
```

### Check HPA Status
```bash
# View HPA status
kubectl describe hpa aggregator-worker-hpa -n iot
kubectl describe hpa ingestion-api-hpa -n iot
kubectl describe hpa dashboard-api-hpa -n iot

# View HPA events
kubectl get events -n iot --sort-by='.lastTimestamp' | grep -i hpa
```

### Test Endpoints
```bash
# Health check
kubectl exec -it deployment/ingestion-api -n iot -- curl localhost:8000/health

# Metrics
kubectl exec -it deployment/ingestion-api -n iot -- curl localhost:8000/metrics
```

## Cleanup

To remove the deployment:
```bash
kubectl delete namespace iot
```

#!/bin/bash

# IoT Telemetry Kubernetes Deployment Script

set -e

echo "🚀 Deploying IoT Telemetry to Kubernetes..."

# Create namespace
echo "📦 Creating namespace..."
kubectl apply -f namespace.yaml

# Create ConfigMap
echo "⚙️  Creating ConfigMap..."
kubectl apply -f configmap.yaml

# Deploy services
echo "🔧 Deploying services..."

echo "  📡 Deploying ingestion-api..."
kubectl apply -f ingestion-api.yaml

echo "  📊 Deploying aggregator-worker..."
kubectl apply -f aggregator-worker.yaml

echo "  🚨 Deploying alerts-worker..."
kubectl apply -f alerts-worker.yaml

echo "  📈 Deploying dashboard-api..."
kubectl apply -f dashboard-api.yaml

# Deploy ServiceMonitor (if Prometheus Operator is installed)
echo "📊 Deploying ServiceMonitor for Prometheus..."
kubectl apply -f servicemonitor.yaml || echo "⚠️  ServiceMonitor deployment failed (Prometheus Operator may not be installed)"

# Wait for deployments to be ready
echo "⏳ Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/ingestion-api -n iot
kubectl wait --for=condition=available --timeout=300s deployment/aggregator-worker -n iot
kubectl wait --for=condition=available --timeout=300s deployment/alerts-worker -n iot
kubectl wait --for=condition=available --timeout=300s deployment/dashboard-api -n iot

echo "✅ Deployment completed successfully!"

# Show status
echo "📋 Deployment Status:"
kubectl get pods -n iot
kubectl get services -n iot
kubectl get ingress -n iot

echo ""
echo "🌐 Access URLs (add to /etc/hosts if needed):"
echo "  API: http://api.iot.local"
echo "  Dashboard: http://dashboard.iot.local"
echo ""
echo "📊 Metrics endpoints:"
echo "  Ingestion API: http://api.iot.local/metrics"
echo "  Dashboard API: http://dashboard.iot.local/metrics"
echo "  Aggregator Worker: kubectl port-forward -n iot svc/aggregator-worker 8003:8000"
echo "  Alerts Worker: kubectl port-forward -n iot svc/alerts-worker 8004:8000"

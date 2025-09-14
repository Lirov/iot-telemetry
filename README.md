# IoT Telemetry System

A comprehensive IoT telemetry processing system built with FastAPI, Kafka, MongoDB, and Kubernetes. This system ingests, processes, aggregates, and monitors IoT sensor data with real-time alerting capabilities.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   IoT Devices   │───▶│  Ingestion API  │───▶│     Kafka       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐              │
                       │  Dashboard API  │◀─────────────┼───┐
                       └─────────────────┘              │   │
                                                        │   │
                       ┌─────────────────┐              │   │
                       │ Aggregator      │◀─────────────┘   │
                       │ Worker          │                  │
                       └─────────────────┘                  │
                                │                           │
                       ┌─────────────────┐              ┌─────────────────┐
                       │    MongoDB      │              │  Alerts Worker  │
                       └─────────────────┘              └─────────────────┘
```

## 🚀 Features

### Core Services
- **Ingestion API**: FastAPI service for receiving telemetry data from IoT devices
- **Aggregator Worker**: Kafka consumer that processes and aggregates sensor data
- **Alerts Worker**: Kafka consumer that monitors data for threshold violations
- **Dashboard API**: FastAPI service for serving telemetry data and alerts

### Key Capabilities
- **Real-time Data Processing**: Kafka-based message streaming
- **Data Aggregation**: Automatic aggregation of sensor data (min, max, average, count)
- **Alert System**: Configurable threshold-based alerting
- **Prometheus Metrics**: Comprehensive observability and monitoring
- **Horizontal Pod Autoscaling**: Automatic scaling based on resource utilization
- **Dead Letter Queue**: Retry logic and error handling
- **MongoDB Indexing**: Optimized database performance

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Kubernetes cluster (for K8s deployment)
- kubectl (for K8s deployment)

## 🛠️ Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd iot-telemetry
```

### 2. Start with Docker Compose
```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Test the System
```bash
# Send test telemetry data
curl -X POST http://localhost:8001/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "dev-1",
    "temperature_c": 25.5,
    "humidity": 60.0
  }'

# Check aggregated data
curl http://localhost:8002/devices/dev-1/aggregates

# Check alerts
curl http://localhost:8002/alerts/recent
```

## 📊 API Endpoints

### Ingestion API (Port 8001)
- `POST /ingest` - Ingest telemetry data
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

### Dashboard API (Port 8002)
- `GET /` - Health check
- `GET /telemetry` - All raw telemetry data
- `GET /aggregated` - All aggregated data
- `GET /alerts` - All alerts
- `GET /alerts/recent` - Recent alerts
- `GET /devices` - List of all devices
- `GET /devices/{device_id}/telemetry` - Device-specific telemetry
- `GET /devices/{device_id}/aggregates` - Device-specific aggregates
- `GET /stats` - System statistics
- `GET /metrics` - Prometheus metrics

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka bootstrap servers |
| `MONGO_URL` | `mongodb://mongo:27017` | MongoDB connection URL |
| `MONGO_DB` | `iotdb` | MongoDB database name |
| `TELEMETRY_TOPIC` | `telemetry.raw` | Kafka topic for telemetry |
| `DLQ_TOPIC` | `telemetry.dlq` | Dead letter queue topic |
| `MAX_RETRIES` | `3` | Maximum retry attempts |
| `TEMP_MIN_THRESHOLD` | `-10` | Minimum temperature threshold |
| `TEMP_MAX_THRESHOLD` | `50` | Maximum temperature threshold |
| `HUMIDITY_MIN_THRESHOLD` | `0` | Minimum humidity threshold |
| `HUMIDITY_MAX_THRESHOLD` | `100` | Maximum humidity threshold |

### Alert Thresholds
Configure alert thresholds via environment variables:
- Temperature: -10°C to 50°C (configurable)
- Humidity: 0% to 100% (configurable)

## 📈 Monitoring & Observability

### Prometheus Metrics
All services expose Prometheus metrics on `/metrics`:

- **Ingestion API**: Telemetry ingestion counters, processing duration
- **Aggregator Worker**: Message processing, aggregation metrics, DLQ counters
- **Alerts Worker**: Alert processing metrics
- **Dashboard API**: API request metrics

### Health Checks
- **Readiness Probes**: Check if service is ready to receive traffic
- **Liveness Probes**: Check if service is healthy

### Metrics Endpoints
- Ingestion API: `http://localhost:8001/metrics`
- Dashboard API: `http://localhost:8002/metrics`
- Aggregator Worker: `http://localhost:8003/metrics`
- Alerts Worker: `http://localhost:8004/metrics`

## 🐳 Docker Services

| Service | Port | Description |
|---------|------|-------------|
| `ingestion-api` | 8001 | Telemetry ingestion API |
| `dashboard-api` | 8002 | Dashboard and data API |
| `aggregator-worker` | 8003 | Metrics port |
| `alerts-worker` | 8004 | Metrics port |
| `kafka` | 9092, 9094 | Message streaming |
| `zookeeper` | 2181 | Kafka coordination |
| `mongo` | 27017 | Data persistence |

## ☸️ Kubernetes Deployment

### Prerequisites
- Kubernetes cluster (v1.19+)
- kubectl configured
- Docker images built and pushed to registry

### Deploy to Kubernetes
```bash
cd k8s

# Build and push images
docker build -t liro/ingestion-api:latest -f ingestion-api/Dockerfile .
docker build -t liro/aggregator-worker:latest -f aggregator-worker/Dockerfile .
docker build -t liro/alerts-worker:latest -f alerts-worker/Dockerfile .
docker build -t liro/dashboard-api:latest -f dashboard-api/Dockerfile .

# Deploy to Kubernetes
./deploy.sh
```

### Kubernetes Features
- **Horizontal Pod Autoscaling**: Automatic scaling based on CPU/memory
- **Resource Limits**: CPU and memory requests/limits
- **Ingress**: External access via NGINX Ingress
- **ServiceMonitor**: Prometheus metrics collection
- **ConfigMap**: Centralized configuration

### Scaling Configuration
- **ingestion-api**: 2-10 replicas (HPA: CPU 60%, Memory 70%)
- **aggregator-worker**: 1-5 replicas (HPA: CPU 50%, Memory 70%)
- **alerts-worker**: 1 replica (no HPA)
- **dashboard-api**: 2-8 replicas (HPA: CPU 50%, Memory 70%)

## 🧪 Load Testing

### Using the Load Generator
```bash
# Install dependencies
pip install requests

# Run load generator
python tools/load_generator.py --devices 10 --rps 2.0 --base-url http://localhost:8001
```

### Load Generator Options
- `--devices`: Number of simulated devices (default: 10)
- `--rps`: Requests per second per device (default: 1.0)
- `--base-url`: Base URL for ingestion API (default: http://localhost:8001)

## 🗄️ Database Schema

### Collections

#### `telemetry_raw`
Raw telemetry data from devices:
```json
{
  "_id": "ObjectId",
  "device_id": "string",
  "ts": "ISO timestamp",
  "temperature_c": "number",
  "humidity": "number",
  "lat": "number",
  "lon": "number"
}
```

#### `aggregated_data`
Aggregated sensor data:
```json
{
  "_id": "ObjectId",
  "device_id": "string",
  "sensor_type": "string",
  "count": "number",
  "sum": "number",
  "min": "number",
  "max": "number",
  "average": "number",
  "timestamp": "ISO timestamp"
}
```

#### `alerts`
Generated alerts:
```json
{
  "_id": "ObjectId",
  "device_id": "string",
  "sensor_type": "string",
  "value": "number",
  "alert_type": "string",
  "severity": "string",
  "message": "string",
  "timestamp": "ISO timestamp",
  "status": "string"
}
```

### Indexes
- `telemetry_raw`: `{device_id: 1, ts: -1}`
- `alerts`: `{created_at: -1}`
- `aggregated_data`: `{device_id: 1, timestamp: -1}`

## 🔄 Data Flow

1. **Ingestion**: IoT devices send telemetry data to `/ingest` endpoint
2. **Streaming**: Data is published to Kafka topic `telemetry.raw`
3. **Storage**: Raw data is stored in MongoDB `telemetry_raw` collection
4. **Processing**: Aggregator worker consumes messages and aggregates data
5. **Alerting**: Alerts worker monitors data for threshold violations
6. **Serving**: Dashboard API serves processed data and alerts

## 🚨 Error Handling

### Dead Letter Queue (DLQ)
- Failed messages are retried up to 3 times
- After max retries, messages are sent to `telemetry.dlq` topic
- DLQ messages include failure reason and timestamp

### Retry Logic
- Configurable retry attempts (default: 3)
- Exponential backoff for failed operations
- Metrics tracking for retry attempts and DLQ messages

## 🛠️ Development

### Project Structure
```
iot-telemetry/
├── ingestion-api/          # Telemetry ingestion service
├── aggregator-worker/      # Data aggregation worker
├── alerts-worker/          # Alert processing worker
├── dashboard-api/          # Dashboard and data API
├── common/                 # Shared configuration
├── k8s/                    # Kubernetes manifests
├── tools/                  # Load testing tools
└── docker-compose.yml      # Docker Compose configuration
```

### Building Images
```bash
# Build all images
docker-compose build

# Build specific service
docker-compose build ingestion-api
```

### Running Tests
```bash
# Test ingestion endpoint
curl -X POST http://localhost:8001/ingest \
  -H "Content-Type: application/json" \
  -d '{"device_id": "test", "temperature_c": 25, "humidity": 50}'

# Test dashboard endpoints
curl http://localhost:8002/health
curl http://localhost:8002/stats
```

## 📚 API Documentation

### Telemetry Data Format
```json
{
  "device_id": "string (required)",
  "ts": "ISO timestamp (optional)",
  "temperature_c": "number (required)",
  "humidity": "number (required)",
  "lat": "number (optional)",
  "lon": "number (optional)"
}
```

### Response Format
```json
{
  "status": "queued",
  "device_id": "dev-1"
}
```

## 🔍 Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check service status
docker-compose ps

# Check logs
docker-compose logs ingestion-api
docker-compose logs aggregator-worker
```

#### Kafka Connection Issues
```bash
# Check Kafka topics
docker exec -it iot-telemetry-kafka-1 kafka-topics.sh --bootstrap-server localhost:9092 --list

# Check consumer groups
docker exec -it iot-telemetry-kafka-1 kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list
```

#### MongoDB Connection Issues
```bash
# Check MongoDB connection
docker exec -it iot-telemetry-mongo-1 mongosh --eval "db.adminCommand('ping')"

# Check collections
docker exec -it iot-telemetry-mongo-1 mongosh --eval "use('iotdb'); db.getCollectionNames()"
```

### Performance Tuning

#### Kafka Configuration
- Adjust `num.partitions` for better parallelism
- Configure `replication.factor` for high availability
- Tune `batch.size` and `linger.ms` for throughput

#### MongoDB Optimization
- Monitor index usage with `db.collection.getIndexes()`
- Use `explain()` to analyze query performance
- Consider sharding for large datasets

#### Resource Limits
- Adjust CPU/memory limits in Kubernetes manifests
- Monitor resource usage with `kubectl top pods`
- Scale services based on actual usage patterns

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the logs for error details

---

**Built with ❤️ using FastAPI, Kafka, MongoDB, and Kubernetes**

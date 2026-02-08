# Grafana Dashboard Setup Guide

## Overview
This guide explains how to set up Grafana dashboards for monitoring the IIT ML Service.

## Prerequisites
- Docker and Docker Compose installed
- Grafana and Prometheus containers running

## Quick Start (Docker)

### 1. Start Monitoring Stack

```bash
# Navigate to project root
cd my-app

# Start Prometheus and Grafana
docker-compose -f docker-compose.yml up -d prometheus grafana
```

### 2. Access Grafana

- **URL**: http://localhost:3000
- **Default Credentials**:
  - Username: `admin`
  - Password: `admin` (change on first login)

### 3. Add Prometheus Data Source

1. Go to **Configuration > Data Sources**
2. Click **Add data source**
3. Select **Prometheus**
4. Configure:
   - **Name**: `Prometheus`
   - **URL**: `http://prometheus:9090`
   - **Access**: `Server (default)`
5. Click **Save & Test**

### 4. Import Dashboard

1. Go to **Dashboards > Import**
2. Click **Upload JSON file**
3. Select `monitoring/grafana-dashboard.json`
4. Click **Import**

## Dashboard Panels

The dashboard includes the following panels:

| Panel | Description |
|--------|-------------|
| Service Health Overview | Shows if the service is UP or DOWN |
| API Error Rate | Percentage of API errors over time |
| Prediction Latency (P95) | 95th percentile of prediction response time |
| System Resources | CPU and Memory usage |
| Database Performance | Query latency and connection pool usage |
| Model Performance | AUC score and drift detection |
| Cache Performance | Hit rates for API and feature store caches |
| Active Alerts | List of currently firing alerts |
| Error Distribution | Error breakdown by category |
| Incident Response Time | Time to respond to incidents |
| Prediction Throughput | Number of predictions per minute |
| Risk Distribution | Distribution of risk levels predicted |

## Manual Setup (Without Docker)

### Install Prometheus

```bash
# Download Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.47.0/prometheus-2.47.0.linux-amd64.tar.gz
tar xvfz prometheus-2.47.0.linux-amd64.tar.gz
cd prometheus-2.47.0.linux-amd64

# Start Prometheus
./prometheus --config.file=../monitoring/prometheus.yml
```

### Install Grafana

```bash
# Add Grafana repository
sudo wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"

# Install Grafana
sudo apt-get update && sudo apt-get install grafana

# Start Grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

## Metrics Available

The FastAPI application exposes metrics at `/metrics`:

- `up` - Service health status
- `iit_api_errors_total` - Total API errors
- `iit_prediction_duration_seconds` - Prediction request duration
- `iit_system_cpu_usage_percent` - CPU usage
- `iit_system_memory_usage_bytes` - Memory usage
- `iit_db_query_duration_seconds` - Database query duration
- `iit_db_connection_pool_checked_out` - Active database connections
- `iit_model_auc_score` - Model AUC score
- `iit_api_cache_hits_total` - API cache hits
- `iit_feature_store_cache_hits_total` - Feature store cache hits
- `iit_model_predictions_total` - Total predictions made

## Alerting

Prometheus alerts are configured in `monitoring/alerts.yml`. Grafana can be used to visualize and manage these alerts.

## Troubleshooting

### Grafana cannot connect to Prometheus

1. Check Prometheus is running: `curl http://localhost:9090/-/healthy`
2. Verify Grafana data source URL is correct
3. Check Docker network connectivity

### No data showing in dashboard

1. Verify the FastAPI app is exposing metrics: `curl http://localhost:8000/metrics`
2. Check Prometheus is scraping: Go to Prometheus UI > Status > Targets
3. Ensure time range in Grafana includes data

### Dashboard import fails

1. Verify JSON file is valid
2. Check Prometheus data source is configured first
3. Try importing manually by copy-pasting JSON content

## Production Considerations

1. **Authentication**: Change default Grafana credentials
2. **Persistence**: Use Docker volumes for data persistence
3. **Security**: Use HTTPS and firewall rules
4. **Retention**: Configure Prometheus data retention based on needs
5. **Backup**: Regularly backup Grafana dashboards and configurations

## Next Steps

- Configure alert notifications (email, Slack, PagerDuty)
- Set up additional dashboards for specific teams
- Configure user permissions and teams
- Set up Grafana provisioning for automatic dashboard loading

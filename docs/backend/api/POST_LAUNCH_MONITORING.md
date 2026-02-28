# Post-Launch Monitoring Guide

## Overview
This guide explains how to set up monitoring for the IIT ML Service after production deployment.

## Health Checks

### API Health Endpoint
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-24T12:00:00Z",
  "database_connected": true,
  "redis_connected": true,
  "model_loaded": true
}
```

### Database Health Check
```http
GET /health/db
```

**Response:**
```json
{
  "database_status": "healthy",
  "connection_pool": {
    "total": 10,
    "active": 2,
    "idle": 8
  },
  "table_stats": {
    "patients": 1500,
    "predictions": 5000,
    "observations": 25000
  }
}
```

## Prometheus Metrics

### Key Metrics to Monitor

| Metric | Description | Alert Threshold |
|---------|-------------|------------------|
| `up` | Service uptime | < 95% |
| `iit_api_errors_total` | Total API errors | > 50/hour |
| `iit_prediction_duration_seconds` | Prediction latency | P95 > 3s |
| `iit_db_query_duration_seconds` | Database query time | P95 > 2s |
| `iit_system_cpu_usage_percent` | CPU usage | > 80% |
| `iit_system_memory_usage_bytes` | Memory usage | > 85% |
| `iit_cache_hit_ratio` | Cache hit rate | < 70% |
| `iit_model_auc_score` | Model AUC | < 0.75 |
| `iit_model_drift_detected` | Model drift | true |

### Prometheus Query Examples

**Check service uptime:**
```promql
up{job="iit-ml-service"}
```

**Get error rate:**
```promql
rate(iit_api_errors_total[5m]) * 100
```

**Get prediction latency P95:**
```promql
histogram_quantile(0.95, rate(iit_prediction_duration_seconds_bucket[5m]))
```

## Grafana Dashboard Panels

### 1. System Overview Panel
- Service uptime status
- Error rate trend
- Request throughput
- Response time P95

### 2. Database Performance Panel
- Connection pool usage
- Query latency P95
- Table sizes and row counts

### 3. Model Performance Panel
- AUC score over time
- Prediction distribution by risk level
- Model drift alerts

### 4. Cache Performance Panel
- Hit rate percentage
- Cache size in bytes
- Miss rate percentage

### 5. Alerting Panel
- Active alerts list
- Alert history
- Alert severity distribution

## Alert Configuration

### Critical Alerts
| Alert | Trigger | Action |
|---------|--------|--------|
| Service down | Restart service |
| Error rate > 100/hour | Scale up |
| Prediction latency P95 > 5s | Investigate model |
| Database query P95 > 3s | Optimize queries |
| Memory usage > 90% | Scale database |
| Model drift detected | Retrain model |
| Cache hit ratio < 50% | Check Redis config |

### Warning Alerts
| Error rate > 50/hour | Monitor traffic |
| Prediction latency P95 > 3s | Check system resources |
| Memory usage > 80% | Check for memory leaks |
| CPU usage > 70% | Profile application |

## Log Aggregation

### Application Logs
- Access logs
- Error logs
- Performance logs
- Security audit logs
- Database query logs

### Log Retention
- Application logs: 30 days
- Security audit logs: 90 days
- Metrics data: 90 days

## Monitoring Setup

### Using Existing Prometheus/Grafana
The monitoring stack is already configured:
- [`monitoring/prometheus.yml`](monitoring/prometheus.yml) - Prometheus configuration
- [`monitoring/grafana-dashboard.json`](monitoring/grafana-dashboard.json) - Grafana dashboard
- [`monitoring/GRAFANA_SETUP.md`](monitoring/GRAFANA_SETUP.md) - Setup guide

### Quick Start
```bash
# Start monitoring stack
docker-compose up -d prometheus grafana

# Access Grafana
# URL: http://localhost:3000
# Default credentials: admin/admin
```

## Production Monitoring Checklist

### Pre-Deployment
- [ ] Configure alert notification channels (email, Slack, PagerDuty)
- [ ] Set up log aggregation (ELK, CloudWatch, Splunk)
- [ ] Configure automated scaling triggers
- [ ] Set up backup monitoring
- [ ] Test all alert integrations

### Post-Deployment
- [ ] Verify all metrics are being collected
- [ ] Test alert notifications
- [ ] Review and adjust alert thresholds
- [ ] Set up on-call rotation for critical alerts
- [ ] Document runbook for incident response

### Ongoing Monitoring
- [ ] Daily: Review Grafana dashboards
- [ ] Daily: Check Prometheus target health
- [ ] Weekly: Review and optimize database performance
- [ ] Monthly: Review and update alert rules
- [ ] Quarterly: Review model performance and retrain if needed

## Troubleshooting

### No metrics showing
1. Check Prometheus is running: `curl http://localhost:9090/metrics`
2. Check Grafana data source is configured
3. Verify backend is exposing metrics: `curl http://localhost:8000/metrics`
4. Check firewall allows traffic from Prometheus to backend

### High error rate
1. Check for API abuse (rate limiting)
2. Review logs for repeated failed requests
3. Check for broken clients or integrations
4. Verify rate limiting is working correctly

### Slow database queries
1. Enable query logging in SQLAlchemy
2. Review slow query logs
3. Add missing indexes
4. Optimize complex queries
5. Consider caching frequently accessed data

## Best Practices

1. **Set appropriate alert thresholds** - Avoid alert fatigue
2. **Use structured logging** - Makes analysis easier
3. **Monitor trends** - Detect issues before they become critical
4. **Regular review** - Adjust thresholds based on actual usage patterns
5. **Test alerts** - Ensure notifications are received
6. **Document everything** - Maintain runbook for incidents

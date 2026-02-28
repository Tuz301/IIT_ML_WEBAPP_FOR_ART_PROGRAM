# IIT ML Service - Troubleshooting and Maintenance Guide

## Overview

This guide provides comprehensive troubleshooting procedures, maintenance tasks, and operational best practices for the IIT ML Service. It covers common issues, preventive maintenance, and recovery procedures.

## Table of Contents

1. [Common Issues and Solutions](#common-issues-and-solutions)
2. [Performance Troubleshooting](#performance-troubleshooting)
3. [Model and Prediction Issues](#model-and-prediction-issues)
4. [Database Issues](#database-issues)
5. [API and Integration Issues](#api-and-integration-issues)
6. [Security Issues](#security-issues)
7. [Monitoring and Alerting](#monitoring-and-alerting)
8. [Maintenance Procedures](#maintenance-procedures)
9. [Backup and Recovery](#backup-and-recovery)
10. [Emergency Procedures](#emergency-procedures)

## Common Issues and Solutions

### Service Unavailable

**Symptoms:**
- API returns 503 Service Unavailable
- Application fails to start
- Container crashes repeatedly

**Troubleshooting Steps:**

1. **Check Service Status:**
   ```bash
   # Kubernetes
   kubectl get pods -n iit-ml-service
   kubectl describe pod <pod-name> -n iit-ml-service

   # Docker Compose
   docker-compose ps
   docker-compose logs ml_api

   # Systemd
   systemctl status iit-ml-service
   ```

2. **Check Application Logs:**
   ```bash
   # Kubernetes
   kubectl logs -f deployment/iit-ml-service -n iit-ml-service

   # Docker
   docker logs -f iit-ml-service

   # File logs
   tail -f /var/log/iit-ml-service/app.log
   ```

3. **Common Causes and Solutions:**

   **Memory Issues:**
   ```bash
   # Check memory usage
   kubectl top pods -n iit-ml-service
   # Increase memory limit if needed
   kubectl set resources deployment iit-ml-service --limits=memory=2Gi -n iit-ml-service
   ```

   **Database Connection:**
   ```bash
   # Test database connectivity
   python -c "import psycopg2; conn = psycopg2.connect('host=localhost dbname=iit_ml user=ml_service'); print('Connected')"
   ```

   **Model Loading:**
   ```bash
   # Check model file existence
   ls -la /app/models/
   # Verify model file integrity
   python -c "import joblib; joblib.load('/app/models/iit_lightgbm_model.pkl')"
   ```

### High Error Rates

**Symptoms:**
- Increased 5xx HTTP status codes
- Error rate > 5% in monitoring dashboard
- User complaints about failed operations

**Investigation:**

1. **Check Error Logs:**
   ```bash
   # Filter error logs
   kubectl logs deployment/iit-ml-service -n iit-ml-service | grep ERROR
   ```

2. **Common Error Patterns:**

   **Validation Errors:**
   - Check input data format
   - Verify required fields are present
   - Review data type constraints

   **Timeout Errors:**
   - Check Redis connectivity
   - Verify model inference time
   - Review database query performance

   **Authentication Errors:**
   - Validate API keys
   - Check token expiration
   - Review rate limiting

## Performance Troubleshooting

### High Latency

**Symptoms:**
- P95 latency > 1 second
- Slow API response times
- User experience degradation

**Diagnosis:**

1. **Check System Resources:**
   ```bash
   # CPU usage
   kubectl top pods -n iit-ml-service

   # Memory usage
   kubectl describe pod <pod-name> -n iit-ml-service | grep -A 5 "Containers:"
   ```

2. **Database Performance:**
   ```sql
   -- Check slow queries
   SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC
   LIMIT 10;

   -- Check table sizes
   SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
   FROM pg_stat_user_tables
   ORDER BY n_tup_ins DESC;
   ```

3. **Cache Performance:**
   ```bash
   # Redis stats
   redis-cli info stats | grep -E "(keyspace_hits|keyspace_misses|evicted_keys)"
   ```

**Optimization Steps:**

1. **Database Optimization:**
   ```sql
   -- Add missing indexes
   CREATE INDEX CONCURRENTLY idx_patients_created_at ON patients(created_at);
   CREATE INDEX CONCURRENTLY idx_predictions_patient_model ON predictions(patient_uuid, model_version);
   ```

2. **Cache Optimization:**
   ```bash
   # Increase Redis memory if needed
   redis-cli config set maxmemory 1gb
   redis-cli config set maxmemory-policy allkeys-lru
   ```

3. **Application Scaling:**
   ```bash
   # Scale deployment
   kubectl scale deployment iit-ml-service --replicas=5 -n iit-ml-service
   ```

### Memory Leaks

**Symptoms:**
- Gradual memory increase over time
- Out of memory errors
- Container restarts due to OOM

**Investigation:**

1. **Memory Profiling:**
   ```python
   # Add to application for debugging
   import tracemalloc
   tracemalloc.start()

   # Check memory usage
   snapshot = tracemalloc.take_snapshot()
   top_stats = snapshot.statistics('lineno')
   for stat in top_stats[:10]:
       print(stat)
   ```

2. **Common Causes:**
   - Unclosed database connections
   - Large data structures in memory
   - Model objects not garbage collected
   - Cache not expiring properly

**Solutions:**

1. **Connection Pooling:**
   ```python
   # Ensure proper connection cleanup
   from sqlalchemy import create_engine
   engine = create_engine('postgresql://...', pool_pre_ping=True, pool_recycle=300)
   ```

2. **Memory Management:**
   ```python
   # Clear large objects after use
   del large_dataframe
   import gc
   gc.collect()
   ```

## Model and Prediction Issues

### Model Drift Detection

**Symptoms:**
- Decreased prediction accuracy
- Model drift alerts triggered
- Inconsistent risk scores

**Investigation:**

1. **Check Model Metrics:**
   ```sql
   SELECT model_id, metric_name, metric_value, recorded_at
   FROM model_metrics
   WHERE recorded_at > NOW() - INTERVAL '7 days'
   ORDER BY recorded_at DESC;
   ```

2. **Data Drift Analysis:**
   ```python
   # Compare recent data distribution with training data
   import pandas as pd
   recent_data = pd.read_sql("SELECT * FROM features WHERE created_at > NOW() - INTERVAL '30 days'", conn)
   # Compare distributions
   ```

**Remediation:**

1. **Model Retraining:**
   ```bash
   # Trigger model retraining pipeline
   python scripts/retrain_model.py --model-version v2.0
   ```

2. **Feature Engineering Update:**
   ```python
   # Update feature engineering logic
   # Add new features or remove outdated ones
   ```

### Prediction Failures

**Symptoms:**
- Individual predictions fail
- Batch predictions incomplete
- Invalid prediction results

**Troubleshooting:**

1. **Input Validation:**
   ```python
   # Check input data quality
   required_fields = ['age', 'bmi', 'blood_pressure']
   missing_fields = [f for f in required_fields if f not in input_data]
   if missing_fields:
       raise ValueError(f"Missing required fields: {missing_fields}")
   ```

2. **Model Loading Issues:**
   ```python
   try:
       model = joblib.load(model_path)
       prediction = model.predict(input_features)
   except Exception as e:
       logger.error(f"Model prediction failed: {e}")
       # Fallback to ensemble or default prediction
   ```

## Database Issues

### Connection Pool Exhaustion

**Symptoms:**
- Database connection errors
- Slow query responses
- Application timeouts

**Solutions:**

1. **Increase Connection Pool:**
   ```python
   engine = create_engine(
       'postgresql://...',
       pool_size=20,
       max_overflow=30,
       pool_timeout=30,
       pool_recycle=3600
   )
   ```

2. **Monitor Connection Usage:**
   ```sql
   SELECT count(*) as active_connections
   FROM pg_stat_activity
   WHERE datname = 'iit_ml_service';
   ```

### Slow Queries

**Symptoms:**
- Query execution time > 1 second
- Database CPU high
- Lock contention

**Optimization:**

1. **Query Analysis:**
   ```sql
   EXPLAIN ANALYZE SELECT * FROM patients WHERE created_at > '2024-01-01';
   ```

2. **Index Optimization:**
   ```sql
   -- Add composite indexes
   CREATE INDEX idx_patients_state_date ON patients(state_province, created_at);
   CREATE INDEX idx_predictions_patient_date ON predictions(patient_uuid, created_at);
   ```

3. **Query Rewriting:**
   ```sql
   -- Use CTEs for complex queries
   WITH recent_patients AS (
       SELECT * FROM patients WHERE created_at > '2024-01-01'
   )
   SELECT * FROM recent_patients WHERE risk_score > 0.7;
   ```

## API and Integration Issues

### Rate Limiting

**Symptoms:**
- 429 Too Many Requests errors
- Uneven request distribution
- Service degradation under load

**Configuration:**

1. **Adjust Rate Limits:**
   ```python
   # In FastAPI
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address

   limiter = Limiter(key_func=get_remote_address)
   app.state.limiter = limiter
   ```

2. **Distributed Rate Limiting:**
   ```python
   # Use Redis for distributed rate limiting
   limiter = Limiter(key_func=get_remote_address, storage_uri="redis://redis:6379")
   ```

### Integration Failures

**Symptoms:**
- HL7 message processing failures
- External API timeouts
- Data synchronization issues

**Troubleshooting:**

1. **HL7 Processing:**
   ```python
   # Validate HL7 message format
   from hl7apy import parser
   try:
       msg = parser.parse_message(hl7_message)
   except Exception as e:
       logger.error(f"HL7 parsing failed: {e}")
   ```

2. **External API Issues:**
   ```python
   # Implement retry logic
   import requests
   from requests.adapters import HTTPAdapter
   from urllib3.util.retry import Retry

   retry_strategy = Retry(
       total=3,
       status_forcelist=[429, 500, 502, 503, 504],
       backoff_factor=1
   )
   adapter = HTTPAdapter(max_retries=retry_strategy)
   session = requests.Session()
   session.mount("https://", adapter)
   ```

## Security Issues

### Authentication Failures

**Symptoms:**
- 401 Unauthorized errors
- Token validation failures
- Session timeouts

**Investigation:**

1. **Token Validation:**
   ```python
   # Check JWT token structure
   import jwt
   try:
       payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
   except jwt.ExpiredSignatureError:
       return "Token expired"
   except jwt.InvalidTokenError:
       return "Invalid token"
   ```

2. **API Key Issues:**
   ```python
   # Validate API key format and permissions
   if not api_key.startswith('iit_'):
       raise ValueError("Invalid API key format")
   ```

### Security Incidents

**Response Procedure:**

1. **Isolate Affected Systems:**
   ```bash
   # Block suspicious IPs
   iptables -A INPUT -s suspicious_ip -j DROP
   ```

2. **Audit Log Review:**
   ```sql
   SELECT * FROM audit_logs
   WHERE timestamp > 'incident_start_time'
   AND event_type IN ('login_failure', 'unauthorized_access')
   ORDER BY timestamp DESC;
   ```

3. **Security Assessment:**
   - Review recent changes
   - Check for vulnerabilities
   - Update security patches

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Application Metrics:**
   - Request rate and latency
   - Error rates by endpoint
   - Memory and CPU usage
   - Active connections

2. **Business Metrics:**
   - Prediction accuracy
   - Model drift indicators
   - User engagement metrics
   - Data quality scores

3. **Infrastructure Metrics:**
   - Database connection pool usage
   - Redis cache hit rates
   - Disk space and I/O
   - Network bandwidth

### Alert Configuration

```yaml
# Prometheus alerting rules
groups:
- name: iit-ml-service
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }}%"

  - alert: HighLatency
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds[5m])) > 2.0
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High latency detected"
      description: "95th percentile latency is {{ $value }}s"
```

## Maintenance Procedures

### Regular Maintenance Tasks

#### Weekly Tasks

1. **Log Rotation:**
   ```bash
   # Rotate application logs
   logrotate -f /etc/logrotate.d/iit-ml-service

   # Archive old logs
   find /var/log/iit-ml-service -name "*.log.1" -mtime +30 -delete
   ```

2. **Database Maintenance:**
   ```sql
   -- Update statistics
   ANALYZE VERBOSE;

   -- Vacuum tables
   VACUUM (ANALYZE, VERBOSE);
   ```

3. **Cache Maintenance:**
   ```bash
   # Clear expired cache entries
   redis-cli --scan --pattern "*:expired" | xargs redis-cli del
   ```

#### Monthly Tasks

1. **Security Updates:**
   ```bash
   # Update system packages
   apt update && apt upgrade -y

   # Update Python packages
   pip install --upgrade -r requirements.txt
   ```

2. **Performance Review:**
   - Review slow query logs
   - Analyze resource usage patterns
   - Optimize database indexes

3. **Backup Verification:**
   ```bash
   # Test backup restoration
   ./scripts/test_backup_restore.sh
   ```

#### Quarterly Tasks

1. **Model Performance Review:**
   ```python
   # Evaluate model performance on recent data
   from sklearn.metrics import classification_report
   # Generate performance report
   ```

2. **Capacity Planning:**
   - Review growth trends
   - Plan infrastructure scaling
   - Update resource allocations

### Automated Maintenance

#### Cron Jobs

```bash
# Daily database maintenance
0 2 * * * /usr/local/bin/iit-ml-service/scripts/daily_maintenance.sh

# Weekly log cleanup
0 3 * * 0 /usr/local/bin/iit-ml-service/scripts/weekly_cleanup.sh

# Monthly performance report
0 4 1 * * /usr/local/bin/iit-ml-service/scripts/monthly_report.sh
```

#### Automated Scripts

**Daily Maintenance Script:**
```bash
#!/bin/bash
# daily_maintenance.sh

# Update database statistics
psql -d iit_ml_service -c "ANALYZE VERBOSE;"

# Clean old cache entries
redis-cli KEYS "cache:*" | xargs redis-cli DEL

# Check disk space
df -h /var/lib/iit-ml-service | awk 'NR==2 {if ($5 > 80) print "WARNING: Disk usage high"}'

# Send daily health report
curl -X POST http://localhost:8000/health/report \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@ihvnigeria.org"}'
```

## Backup and Recovery

### Backup Strategy

#### Database Backups

```bash
# Daily full backup
0 2 * * * pg_dump -U ml_service -h localhost iit_ml_service | gzip > /backup/daily/$(date +\%Y\%m\%d).sql.gz

# Weekly incremental backup
0 2 * * 0 pg_dump -U ml_service -h localhost --format=directory --compress=9 --file=/backup/weekly/$(date +\%Y\%m\%d) iit_ml_service
```

#### Model Backups

```bash
# Model backup script
#!/bin/bash
MODEL_DIR="/app/models"
BACKUP_DIR="/backup/models"

# Create timestamped backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/models_$TIMESTAMP"

mkdir -p $BACKUP_PATH
cp -r $MODEL_DIR/* $BACKUP_PATH/

# Upload to S3
aws s3 sync $BACKUP_PATH s3://iit-ml-backups/models/$TIMESTAMP/

# Clean old backups (keep last 30 days)
find $BACKUP_DIR -name "models_*" -mtime +30 -delete
```

### Recovery Procedures

#### Database Recovery

```bash
# Stop application
kubectl scale deployment iit-ml-service --replicas=0 -n iit-ml-service

# Restore from backup
gunzip < /backup/daily/20240101.sql.gz | psql -U ml_service -h localhost iit_ml_service

# Restart application
kubectl scale deployment iit-ml-service --replicas=3 -n iit-ml-service
```

#### Model Recovery

```bash
# Download from S3
aws s3 sync s3://iit-ml-backups/models/20240101_020000 /tmp/model_restore/

# Validate model
python -c "import joblib; model = joblib.load('/tmp/model_restore/iit_lightgbm_model.pkl'); print('Model loaded successfully')"

# Deploy new model
cp /tmp/model_restore/* /app/models/
kubectl rollout restart deployment/iit-ml-service -n iit-ml-service
```

### Disaster Recovery Testing

#### Quarterly DR Test

```bash
# 1. Create isolated test environment
kubectl create namespace dr-test

# 2. Restore backup to test environment
./scripts/restore_backup.sh --namespace dr-test --backup-date 2024-01-01

# 3. Run integration tests
pytest tests/test_dr_recovery.py -v

# 4. Validate functionality
curl -X POST http://dr-test-service/health/check

# 5. Clean up
kubectl delete namespace dr-test
```

## Emergency Procedures

### Critical System Failure

**Immediate Actions:**

1. **Assess Impact:**
   - Determine affected services
   - Estimate user impact
   - Notify stakeholders

2. **Activate Response Team:**
   ```bash
   # Send emergency notification
   curl -X POST https://api.pagerduty.com/incidents \
     -H "Authorization: Token token=your-token" \
     -d '{"incident": {"type": "incident", "title": "IIT ML Service Critical Failure"}}'
   ```

3. **Implement Mitigation:**
   ```bash
   # Scale up resources
   kubectl scale deployment iit-ml-service --replicas=10 -n iit-ml-service

   # Enable circuit breakers
   kubectl set env deployment/iit-ml-service CIRCUIT_BREAKER_ENABLED=true -n iit-ml-service
   ```

### Data Loss Incident

**Response Steps:**

1. **Stop All Writes:**
   ```sql
   -- Enable read-only mode
   ALTER DATABASE iit_ml_service SET default_transaction_read_only = on;
   ```

2. **Assess Data Loss:**
   ```sql
   -- Check table row counts
   SELECT schemaname, tablename, n_tup_ins - n_tup_del as estimated_rows
   FROM pg_stat_user_tables
   ORDER BY n_tup_ins DESC;
   ```

3. **Execute Recovery:**
   ```bash
   # Restore from latest backup
   ./scripts/emergency_restore.sh --point-in-time "2024-01-01 14:30:00"

   # Validate data integrity
   ./scripts/validate_data_integrity.sh
   ```

### Security Breach

**Containment:**

1. **Isolate Systems:**
   ```bash
   # Disconnect from network
   iptables -F
   iptables -P INPUT DROP
   iptables -P FORWARD DROP
   iptables -P OUTPUT DROP
   ```

2. **Preserve Evidence:**
   ```bash
   # Create forensic image
   dd if=/dev/sda of=/forensic/image.dd bs=4M
   ```

3. **Notify Authorities:**
   - Contact cybersecurity team
   - Report to relevant authorities
   - Notify affected users

## Support and Escalation

### Support Tiers

1. **Tier 1 (L1):** Basic troubleshooting and user support
2. **Tier 2 (L2):** Advanced technical issues and system administration
3. **Tier 3 (L3):** Development team for complex issues and code changes

### Escalation Matrix

| Severity | Response Time | Escalation Path |
|----------|---------------|-----------------|
| Critical | 15 minutes | L1 → L2 → L3 → Management |
| High | 1 hour | L1 → L2 → L3 |
| Medium | 4 hours | L1 → L2 |
| Low | 24 hours | L1 |

### Contact Information

- **Emergency Hotline:** +234-XXX-XXX-XXXX
- **Email Support:** support@ihvnigeria.org
- **Development Team:** dev@ihvnigeria.org
- **Management:** management@ihvnigeria.org

## Conclusion

This troubleshooting and maintenance guide provides comprehensive procedures for maintaining the IIT ML Service. Regular review and updates to this guide are essential for maintaining system reliability and performance. All maintenance activities should be documented and reviewed regularly to ensure continuous improvement of operational procedures.

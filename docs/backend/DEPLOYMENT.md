# Deployment Guide

Complete deployment guide for IIT Prediction ML Service in production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [AWS Cloud Deployment](#aws-cloud-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Production Checklist](#production-checklist)
7. [Monitoring Setup](#monitoring-setup)
8. [Scaling Considerations](#scaling-considerations)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **CPU**: 2+ cores (4+ recommended for production)
- **Memory**: 4GB minimum (8GB+ recommended)
- **Storage**: 10GB minimum
- **OS**: Linux (Ubuntu 20.04+), macOS, or Windows with WSL2

### Software Dependencies

- Docker 20.10+ and Docker Compose 2.0+
- OR Python 3.11+ with pip
- Redis 7.0+ (for feature store)
- PostgreSQL 16+ (optional, for future use)

## Local Development

### Quick Start

```bash
# 1. Clone repository
git clone <repository-url>
cd ml-service

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
cp .env.example .env
# Edit .env with your configuration

# 5. Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Development with Docker Compose

```bash
# Start all services (API, Redis, PostgreSQL, monitoring)
docker-compose up -d

# View logs
docker-compose logs -f ml_api

# Stop services
docker-compose down
```

## Docker Deployment

### Build Production Image

```bash
# Build image
docker build -t iit-ml-service:1.0.0 .

# Test locally
docker run -p 8000:8000 \
  -e MODEL_PATH=/app/models/iit_lightgbm_model.txt \
  -v $(pwd)/models:/app/models:ro \
  iit-ml-service:1.0.0
```

### Docker Compose Production

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  ml_api:
    image: iit-ml-service:1.0.0
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=INFO
      - REDIS_HOST=redis-prod.example.com
      - MODEL_PATH=/app/models/iit_lightgbm_model.txt
    volumes:
      - /data/models:/app/models:ro
    restart: always
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
```

```bash
# Deploy to production
docker-compose -f docker-compose.prod.yml up -d
```

## AWS Cloud Deployment

### Prerequisites
- AWS CLI configured with appropriate permissions
- Terraform 1.0+
- AWS account with necessary permissions for:
  - EC2 instances
  - RDS databases
  - ELB load balancers
  - CloudFront distributions
  - ECS/Fargate
  - ElastiCache
  - IAM roles and policies

### Infrastructure Components
The production infrastructure includes:
- **VPC**: Isolated network with public/private subnets across multiple AZs
- **ECS Fargate**: Container orchestration for the ML service
- **Application Load Balancer**: Distributes traffic across ECS tasks
- **RDS PostgreSQL**: Multi-AZ database with automated backups
- **ElastiCache Redis**: In-memory caching for feature store
- **CloudFront CDN**: Global content delivery for static assets
- **Auto Scaling**: Automatic scaling based on CPU/memory metrics

### Deployment Steps

1. **Initialize Terraform**:
   ```bash
   cd terraform
   terraform init
   ```

2. **Plan Infrastructure**:
   ```bash
   terraform plan -var-file="production.tfvars"
   ```

3. **Deploy Infrastructure**:
   ```bash
   terraform apply -var-file="production.tfvars"
   ```

4. **Configure ECR Repository**:
   ```bash
   # Create ECR repository
   aws ecr create-repository --repository-name iit-ml-service --region us-east-1

   # Build and push Docker image
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
   docker build -t iit-ml-service .
   docker tag iit-ml-service:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/iit-ml-service:latest
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/iit-ml-service:latest
   ```

5. **Update ECS Service**:
   ```bash
   # Update service to use new image
   aws ecs update-service --cluster iit-ml-cluster --service iit-ml-service --force-new-deployment
   ```

### Monitoring and Alerting

1. **Prometheus Setup**:
   ```bash
   # Deploy Prometheus using CloudWatch or managed service
   # Configure scraping for ECS tasks and ALB metrics
   ```

2. **Grafana Dashboard**:
   ```bash
   # Import the provided dashboard JSON from monitoring/grafana-dashboard.json
   # Configure data sources for Prometheus and CloudWatch
   ```

3. **Alerting Rules**:
   ```bash
   # Apply the alerting rules from monitoring/alerts.yml
   # Configure notification channels (SNS, PagerDuty, etc.)
   ```

## Kubernetes Deployment (Alternative)

### Prerequisites

- Kubernetes cluster 1.24+
- kubectl configured
- Helm 3.0+ (optional)

### Deployment Manifests

#### 1. Namespace

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: iit-ml-service
```

#### 2. ConfigMap

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: iit-ml-config
  namespace: iit-ml-service
data:
  LOG_LEVEL: "INFO"
  REDIS_HOST: "redis-service"
  MAX_BATCH_SIZE: "100"
```

#### 3. Secret

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: iit-ml-secrets
  namespace: iit-ml-service
type: Opaque
data:
  redis-password: <base64-encoded-password>
  postgres-password: <base64-encoded-password>
```

#### 4. Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: iit-ml-service
  namespace: iit-ml-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: iit-ml-service
  template:
    metadata:
      labels:
        app: iit-ml-service
        version: v1.0.0
    spec:
      containers:
      - name: api
        image: iit-ml-service:1.0.0
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: MODEL_PATH
          value: /app/models/iit_lightgbm_model.txt
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: iit-ml-secrets
              key: redis-password
        envFrom:
        - configMapRef:
            name: iit-ml-config
        volumeMounts:
        - name: models
          mountPath: /app/models
          readOnly: true
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: ml-models-pvc
```

#### 5. Service

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: iit-ml-service
  namespace: iit-ml-service
spec:
  type: LoadBalancer
  selector:
    app: iit-ml-service
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
    name: http
```

#### 6. HorizontalPodAutoscaler

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: iit-ml-hpa
  namespace: iit-ml-service
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: iit-ml-service
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Deploy to Kubernetes

```bash
# Apply all manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml

# Verify deployment
kubectl get pods -n iit-ml-service
kubectl get svc -n iit-ml-service

# Check logs
kubectl logs -f deployment/iit-ml-service -n iit-ml-service
```

## Production Checklist

### Pre-Deployment

- [ ] Train and validate model with production data
- [ ] Load test API endpoints (target: 1000 req/s)
- [ ] Configure resource limits (CPU, memory)
- [ ] Set up monitoring (Prometheus, Grafana)
- [ ] Configure logging aggregation
- [ ] Set up alerting rules
- [ ] Enable API authentication/authorization
- [ ] Configure CORS for production domains
- [ ] Set up backup strategy for models
- [ ] Document rollback procedures

### Security

- [ ] Use non-root Docker user (✓ included)
- [ ] Enable API key authentication
- [ ] Configure rate limiting
- [ ] Use secrets management (Kubernetes Secrets, AWS Secrets Manager)
- [ ] Enable TLS/SSL for API endpoints
- [ ] Implement network policies
- [ ] Regular security scanning of Docker images
- [ ] Audit logging for all predictions

### Performance

- [ ] Optimize batch size for throughput
- [ ] Configure Redis connection pooling
- [ ] Set appropriate worker count (uvicorn)
- [ ] Enable response compression
- [ ] Implement caching strategy
- [ ] Set up CDN for static assets (if any)

### Reliability

- [ ] Configure health checks (liveness, readiness)
- [ ] Set up circuit breakers
- [ ] Implement retry mechanisms
- [ ] Configure graceful shutdown
- [ ] Set up backup/restore procedures
- [ ] Document disaster recovery plan

## Monitoring Setup

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'iit-ml-service'
    kubernetes_sd_configs:
    - role: pod
      namespaces:
        names:
        - iit-ml-service
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_label_app]
      action: keep
      regex: iit-ml-service
```

### Key Alerts

```yaml
# alerts.yml
groups:
- name: iit-ml-alerts
  rules:
  - alert: HighErrorRate
    expr: rate(iit_api_errors_total[5m]) > 0.05
    for: 5m
    annotations:
      summary: "High error rate detected"
  
  - alert: HighLatency
    expr: histogram_quantile(0.95, iit_prediction_duration_seconds) > 1.0
    for: 5m
    annotations:
      summary: "P95 latency above 1 second"
  
  - alert: ModelDriftDetected
    expr: iit_model_drift_detected == 1
    for: 1h
    annotations:
      summary: "Model drift detected"
```

## Scaling Considerations

### Horizontal Scaling

- Use Kubernetes HPA for automatic scaling
- Target: 70% CPU, 80% memory utilization
- Min replicas: 3, Max replicas: 10
- Scale based on request rate and latency

### Vertical Scaling

- Monitor resource usage patterns
- Adjust CPU/memory requests and limits
- Consider larger instance types for training

### Database Scaling

- Redis: Cluster mode for high availability
- PostgreSQL: Read replicas for reporting
- Consider managed services (AWS RDS, ElastiCache)

## Troubleshooting

### High Latency

```bash
# Check Prometheus metrics
curl http://localhost:8000/metrics | grep latency

# Check feature store cache hit rate
curl http://localhost:8000/metrics | grep cache

# Scale up replicas
kubectl scale deployment iit-ml-service --replicas=5 -n iit-ml-service
```

### Model Loading Errors

```bash
# Check model files
kubectl exec -it deployment/iit-ml-service -n iit-ml-service -- ls -lh /app/models/

# View logs
kubectl logs deployment/iit-ml-service -n iit-ml-service | grep -i model
```

### Redis Connection Issues

```bash
# Test Redis connection
kubectl exec -it deployment/iit-ml-service -n iit-ml-service -- \
  python -c "import redis; r=redis.Redis(host='redis-service'); print(r.ping())"
```

### Memory Issues

```bash
# Check memory usage
kubectl top pods -n iit-ml-service

# Increase memory limit
kubectl set resources deployment iit-ml-service --limits=memory=2Gi -n iit-ml-service
```

## Rolling Updates

```bash
# Update image
kubectl set image deployment/iit-ml-service \
  api=iit-ml-service:1.1.0 -n iit-ml-service

# Monitor rollout
kubectl rollout status deployment/iit-ml-service -n iit-ml-service

# Rollback if needed
kubectl rollout undo deployment/iit-ml-service -n iit-ml-service
```

## Backup and Recovery

### Model Backup

```bash
# Backup models to S3/Cloud Storage
aws s3 sync ./models/ s3://iit-ml-models/backup-$(date +%Y%m%d)/

# Schedule automated backups
# Add to cron: 0 2 * * * /path/to/backup-script.sh
```

### Database Backup

```bash
# PostgreSQL backup
kubectl exec -it postgres-pod -n iit-ml-service -- \
  pg_dump -U ml_service iit_ml_service > backup.sql

# Redis backup
kubectl exec -it redis-pod -n iit-ml-service -- \
  redis-cli BGSAVE
```

## Support

For deployment issues:
- Check logs: `kubectl logs -f deployment/iit-ml-service -n iit-ml-service`
- Review metrics: http://prometheus-url:9090
- Contact: devops@ihvnigeria.org

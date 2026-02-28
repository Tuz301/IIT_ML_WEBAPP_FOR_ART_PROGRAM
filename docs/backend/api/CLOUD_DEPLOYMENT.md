# Cloud Infrastructure Setup Guide

## Overview
This guide explains how to deploy the IIT ML Service to cloud infrastructure.

## Quick Start (Docker Compose)

### Prerequisites
- Docker installed
- Docker Compose installed
- Cloud provider account (AWS/Azure/GCP)

### 1. Build and Start Services

```bash
# Navigate to project root
cd my-app

# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f ml-service
```

### 2. Services Started

| Service | Port | Description |
|---------|-------|-------------|
| ml-service | 8000 | FastAPI backend |
| prometheus | 9090 | Metrics collection |
| grafana | 3000 | Dashboard visualization |
| postgres | 5432 | PostgreSQL database |
| redis | 6379 | Cache layer |

## AWS Deployment

### Using AWS ECS

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1

# Build Docker image
docker build -t iit-ml-service ./backend/ml-service

# Tag image
docker tag iit-ml-service:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/iit-ml-service:latest

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/iit-ml-service:latest
```

### ECS Task Definition

```json
{
  "family": "iit-ml-service",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "iit-ml-service",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/iit-ml-service:latest",
      "portMappings": [
        {"containerPort": 8000, "protocol": "tcp"}
      ],
      "environment": [
        {"name": "DATABASE_URL", "value": "postgresql://user:pass@postgres:5432/iit_ml_service"},
        {"name": "REDIS_URL", "value": "redis://redis:6379/0"},
        {"name": "USE_POSTGRES", "value": "true"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/iit-ml-service",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Using AWS Lambda (Serverless)

```bash
# Package for Lambda
cd backend/ml-service
pip install -r requirements.txt --target ./package

# Create deployment package
cd package
zip -r ../iit-ml-service.zip .

# Deploy to Lambda
aws lambda create-function \
  --function-name iit-ml-service \
  --runtime python3.11 \
  --role arn:aws:iam::123456789012:role/LambdaRole \
  --handler app.main:lambda_handler \
  --zip-file ../iit-ml-service.zip \
  --timeout 30 \
  --memory-size 1024 \
  --environment Variables DATABASE_URL=postgresql://...
```

## Azure Deployment

### Using Azure Container Instances

```bash
# Create resource group
az group create --name iit-ml-service --location eastus

# Create container registry
az acr create --name iitmlservice --resource-group iit-ml-service --sku Basic

# Login to ACR
az acr login --name iitmlservice

# Build and push image
az acr build --registry iitmlservice.azurecr.io --image iit-ml-service:latest .
az acr push --registry iitmlservice.azurecr.io iit-ml-service:latest

# Create container instance
az container create \
  --resource-group iit-ml-service \
  --name iit-ml-service \
  --image iitmlservice.azurecr.io/iit-ml-service:latest \
  --ports 8000 \
  --cpu 1 \
  --memory 2 \
  --environment-variables \
    DATABASE_URL=postgresql://... \
    REDIS_URL=redis://...
```

### Using Azure App Service

```bash
# Create App Service plan
az appservice plan create \
  --name iit-ml-service-plan \
  --resource-group iit-ml-service \
  --sku B1

# Create web app
az webapp create \
  --name iit-ml-service \
  --resource-group iit-ml-service \
  --plan iit-ml-service-plan \
  --runtime "PYTHON|3.11" \
  --deployment-container-image-name iit-ml-service \
  --deployment-container-image-tag latest
```

## Google Cloud Deployment

### Using Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/iit-ml-service

# Deploy to Cloud Run
gcloud run deploy iit-ml-service \
  --image gcr.io/PROJECT_ID/iit-ml-service \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --port 8000 \
  --set-env-vars DATABASE_URL=postgresql://...,REDIS_URL=redis://...
```

### Using Google Kubernetes Engine (GKE)

```bash
# Create cluster
gcloud container clusters create iit-ml-cluster \
  --num-nodes 3 \
  --machine-type n1-standard-2 \
  --region us-central1

# Get credentials
gcloud container clusters get-credentials iit-ml-cluster

# Deploy to Kubernetes
kubectl apply -f k8s/deployment.yaml
```

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| DATABASE_URL | Database connection string | `postgresql://user:pass@host:5432/db` |
| REDIS_URL | Redis connection string | `redis://host:6379/0` |
| USE_POSTGRES | Use PostgreSQL instead of SQLite | `true` |
| API_KEY_ENABLED | Enable API key authentication | `false` |
| CACHE_ENABLED | Enable caching | `true` |
| DEBUG | Enable debug mode | `false` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| LOG_LEVEL | Logging level | `INFO` |
| CORS_ORIGINS | Allowed CORS origins | `*` |
| MAX_BATCH_SIZE | Max prediction batch size | `100` |
| MODEL_PATH | Path to ML model | `./models/iit_lightgbm_model.txt` |

## Docker Compose Configuration

```yaml
version: '3.8'

services:
  ml-service:
    build: ./backend/ml-service
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://ml_service:changeme@postgres:5432/iit_ml_service
      - REDIS_URL=redis://redis:6379/0
      - USE_POSTGRES=true
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=iit_ml_service
      - POSTGRES_USER=ml_service
      - POSTGRES_PASSWORD=changeme
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./backend/ml-service/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./backend/ml-service/monitoring/grafana-dashboard.json:/etc/grafana/provisioning/dashboards

volumes:
  postgres_data:
  grafana_data:
```

## Load Balancing

### Using AWS Application Load Balancer

```bash
# Create target group
aws elbv2 create-target-group \
  --name iit-ml-targets \
  --protocol HTTP \
  --port 8000

# Register targets
aws elbv2 register-targets \
  --target-group-arn arn:aws:elasticloadbalancing:...:targetgroup/iit-ml-targets/... \
  --targets InstanceId=1 InstanceId=2

# Create load balancer
aws elbv2 create-load-balancer \
  --name iit-ml-lb \
  --subnets subnet-1 subnet-2 \
  --security-groups sg-12345 \
  --type application

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...:targetgroup/iit-ml-targets/...,TargetPort=8000
```

## Monitoring

### CloudWatch (AWS)

```bash
# Create log group
aws logs create-log-group /ecs/iit-ml-service

# Create metric filters
aws cloudwatch put-metric-filter \
  --metric-name APIErrorRate \
  --namespace IIT/MLService \
  --filter-pattern "[APIErrorRate]"
```

### Cloud Monitoring (GCP)

```bash
# Create log sink
gcloud logging sinks create iit-ml-logs \
  --logging=write-logs \
  --destination=bigquery.googleapis.com/projects/PROJECT_ID/datasets/iit_ml_logs

# Create alert policy
gcloud alpha monitoring policies create \
  --display-name "High Error Rate" \
  --condition "log_metric(\"APIErrorRate\") > 10" \
  --notification-channels projects/PROJECT_ID/notificationChannels/0
```

## Scaling

### Horizontal Pod Autoscaler (Kubernetes)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: iit-ml-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: iit-ml-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### AWS Auto Scaling

```bash
# Create target tracking policy
aws autoscaling put-scaling-policy \
  --policy-name iit-ml-scaling-policy \
  --target-group-arn arn:aws:autoscaling:...:targetGroup/iit-ml-targets/... \
  --policy-type TargetTrackingScaling \
  --target-value 50 \
  --scale-out-cooldown 300 \
  --scale-in-cooldown 300
```

## Security

### SSL/TLS Certificates

```bash
# AWS Certificate Manager
aws acm request-certificate \
  --domain-name api.yourdomain.com \
  --validation-method DNS

# Let's Encrypt
certbot certonly --standalone -d api.yourdomain.com
```

### Firewall Rules

```bash
# AWS Security Groups
aws ec2 authorize-security-group-ingress \
  --group-id sg-12345 \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0

# Azure Network Security Group
az network nsg rule create \
  --resource-group iit-ml-service \
  --name allow-http \
  --access Allow \
  --protocol Tcp \
  --direction Inbound \
  --priority 100 \
  --source-address-prefixes * \
  --source-port-ranges * \
  --destination-port-ranges 8000
```

## Backup and Disaster Recovery

### Automated Backups

```bash
# AWS Backup
aws backup start-backup-job \
  --backup-vault-name iit-ml-backups \
  --resource-arn arn:aws:backup:...:backup-vault/iit-ml-backups/...

# Azure Backup
az backup protection enable-for-vm \
  --name iit-ml-vm \
  --resource-group iit-ml-service
```

## Troubleshooting

### Container Won't Start

1. Check logs: `docker-compose logs ml-service`
2. Verify environment variables
3. Check port conflicts: `netstat -tuln | grep 8000`
4. Verify database connectivity
5. Check Redis connection

### High Memory Usage

1. Check container limits
2. Review memory usage in monitoring
3. Consider scaling up
4. Optimize ML model size

### Slow API Response

1. Check database query performance
2. Review cache hit ratio
3. Check network latency
4. Consider CDN for static assets

## Cost Optimization

1. **Use spot instances** for non-critical workloads (up to 90% savings)
2. **Right-size instances** based on actual usage
3. **Use auto-scaling** to match demand
4. **Enable reserved instances** for steady workloads (up to 75% savings)
5. **Use lifecycle policies** to terminate unused resources
6. **Monitor and optimize** storage costs

# IIT ML Service - Production Deployment Guide

This guide provides comprehensive instructions for deploying the IIT ML Service to production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Application Deployment](#application-deployment)
4. [Monitoring and Logging](#monitoring-and-logging)
5. [Rollback Procedures](#rollback-procedures)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

- [Terraform](https://www.terraform.io/) >= 1.6.0
- [Docker](https://www.docker.com/) >= 24.0
- [Docker Compose](https://docs.docker.com/compose/) >= 2.20
- [kubectl](https://kubernetes.io/) >= 1.28 (if using EKS)
- [AWS CLI](https://aws.amazon.com/cli/) >= 2.13

### Required Accounts and Services

- AWS Account with appropriate permissions
- Docker Hub account or ECR registry
- Domain name with Route53 configured
- SSL/TLS certificates (AWS ACM)

### Environment Variables

Create a `.env.production` file with the following variables:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=default

# Application Configuration
ENVIRONMENT=production
SECRET_KEY=<your-secret-key>
JWT_SECRET=<your-jwt-secret>
CORS_ORIGINS=https://iit-ml.example.com

# Database Configuration
POSTGRES_USER=iitml_admin
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=iitml_production

# Redis Configuration
REDIS_PASSWORD=<strong-password>

# Docker Registry
DOCKER_USERNAME=<your-dockerhub-username>
DOCKER_REGISTRY=docker.io
IMAGE_TAG=latest

# Monitoring
SENTRY_DSN=<your-sentry-dsn>
GRAFANA_ADMIN_PASSWORD=<strong-password>
ALERTS_EMAIL=alerts@example.com

# Domain
DOMAIN_NAME=iit-ml.example.com
CERTIFICATE_ARN=arn:aws:acm:us-east-1:123456789012:certificate/xxx
```

---

## Infrastructure Setup

### 1. Initialize Terraform

```bash
cd terraform/environments/production
terraform init
```

### 2. Review and Customize Configuration

Edit `terraform.tfvars` to customize:
- VPC CIDR blocks
- Instance types and sizes
- Auto-scaling parameters
- Backup retention periods

### 3. Plan Infrastructure Changes

```bash
terraform plan -out=tfplan
```

Review the planned changes carefully before applying.

### 4. Apply Infrastructure

```bash
terraform apply tfplan
```

This will create:
- VPC with public and private subnets
- ECS Cluster with Fargate
- RDS PostgreSQL database
- ElastiCache Redis cluster
- Application Load Balancer
- CloudWatch Alarms and Dashboards
- Security groups and IAM roles

### 5. Verify Infrastructure

```bash
# Verify ECS cluster
aws ecs describe-clusters --clusters iit-ml-production

# Verify RDS instance
aws rds describe-db-instances --db-instance-identifier iit-ml-production

# Verify ALB
aws elbv2 describe-load-balancers --names iit-ml-production-alb
```

---

## Application Deployment

### Option 1: Using Docker Compose (Simpler)

#### 1. Build and Push Images

```bash
# Backend
cd backend/ml-service
docker build -t ${DOCKER_USERNAME}/iit-ml-backend:${IMAGE_TAG} .
docker push ${DOCKER_USERNAME}/iit-ml-backend:${IMAGE_TAG}

# Frontend
cd ../../
docker build -t ${DOCKER_USERNAME}/iit-ml-frontend:${IMAGE_TAG} .
docker push ${DOCKER_USERNAME}/iit-ml-frontend:${IMAGE_TAG}
```

#### 2. Deploy with Docker Compose

```bash
export $(cat .env.production | xargs)
docker-compose -f docker-compose.prod.yml up -d
```

#### 3. Run Database Migrations

```bash
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

#### 4. Verify Deployment

```bash
# Health check
curl https://iit-ml.example.com/health

# Check logs
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Option 2: Using AWS ECS (Production)

#### 1. Build and Push to ECR

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${ECR_REGISTRY}

# Build and push
docker build -t ${ECR_REGISTRY}/iit-ml-backend:${IMAGE_TAG} backend/ml-service
docker push ${ECR_REGISTRY}/iit-ml-backend:${IMAGE_TAG}
```

#### 2. Update ECS Task Definitions

```bash
# Register new task definition
aws ecs register-task-definition --cli-input-json file://task-definition-backend.json

# Update service
aws ecs update-service --cluster iit-ml-production --service iit-ml-backend --task-definition iit-ml-backend:${IMAGE_TAG}
```

#### 3. Monitor Deployment

```bash
# Watch service events
aws ecs describe-services --cluster iit-ml-production --services iit-ml-backend

# Wait for deployment to complete
aws ecs wait services-stable --cluster iit-ml-production --services iit-ml-backend
```

---

## Monitoring and Logging

### CloudWatch Dashboard

Access the CloudWatch dashboard:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=iit-ml-production-dashboard
```

### Key Metrics to Monitor

| Metric | Description | Warning Threshold | Critical Threshold |
|--------|-------------|-------------------|-------------------|
| CPU Utilization | ECS container CPU | 70% | 90% |
| Memory Utilization | ECS container memory | 80% | 95% |
| 5XX Error Rate | ALB 5XX errors | 1% | 5% |
| Response Time | API response time | 500ms | 1000ms |
| DB Connections | RDS connections | 50 | 100 |
| Free Storage | RDS free space | 5GB | 2GB |

### Grafana Dashboard

Access Grafana:
```
URL: https://grafana.iit-ml.example.com
Username: admin
Password: ${GRAFANA_ADMIN_PASSWORD}
```

### Log Analysis

View logs with CloudWatch Logs:

```bash
# Backend logs
aws logs tail /ecs/iit-ml-production/backend --follow

# Frontend logs
aws logs tail /ecs/iit-ml-production/frontend --follow

# Nginx logs
aws logs tail /ecs/iit-ml-production/nginx --follow
```

---

## Rollback Procedures

### Database Rollback

```bash
# List available snapshots
aws rds describe-db-snapshots --db-instance-identifier iit-ml-production

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier iit-ml-production-rollback \
  --db-snapshot-identifier <snapshot-id>

# Update DNS/connections to point to restored instance
```

### Application Rollback

#### Docker Compose

```bash
# Pull previous image version
docker pull ${DOCKER_USERNAME}/iit-ml-backend:previous-tag

# Update docker-compose.yml with previous tag
# Then restart
docker-compose -f docker-compose.prod.yml up -d backend
```

#### ECS

```bash
# List task definitions
aws ecs list-task-definitions --family-prefix iit-ml-backend

# Update service to previous version
aws ecs update-service \
  --cluster iit-ml-production \
  --service iit-ml-backend \
  --task-definition iit-ml-backend:previous-version
```

### Infrastructure Rollback

```bash
cd terraform/environments/production
terraform rollback
```

---

## Troubleshooting

### Common Issues

#### 1. Container Health Checks Failing

**Symptoms**: ECS tasks restarting frequently

**Solutions**:
- Check application logs: `docker logs <container-id>`
- Verify health check endpoint: `curl http://localhost:8000/health`
- Increase health check grace period in task definition
- Check resource limits (CPU/Memory)

#### 2. Database Connection Issues

**Symptoms**: Application can't connect to RDS

**Solutions**:
- Verify security group allows traffic from ECS
- Check database is accessible: `telnet <rds-endpoint> 5432`
- Verify credentials in environment variables
- Check RDS event logs for issues

#### 3. High Memory Usage

**Symptoms**: OOMKilled containers

**Solutions**:
- Increase memory limits in task definition
- Profile application for memory leaks
- Check for connection leaks (DB, Redis)
- Review cache configuration

#### 4. Slow API Responses

**Symptoms**: High latency, timeouts

**Solutions**:
- Check database query performance
- Enable query caching in Redis
- Scale up ECS tasks
- Review N+1 query issues
- Check for external API calls

### Debug Mode

Enable debug logging:

```bash
# Update environment variable
ENVIRONMENT=production
LOG_LEVEL=DEBUG

# Restart service
docker-compose -f docker-compose.prod.yml restart backend
```

### Health Check Script

```bash
#!/bin/bash
# health-check.sh

echo "Checking IIT ML Service Health..."

# API Health
API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" https://iit-ml.example.com/health)
if [ $API_HEALTH -eq 200 ]; then
    echo "✓ API is healthy"
else
    echo "✗ API is unhealthy (HTTP $API_HEALTH)"
fi

# Database Connection
DB_HEALTH=$(docker exec -it iit-ml-postgres pg_isready -U iitml_admin)
echo "Database: $DB_HEALTH"

# Redis Connection
REDIS_HEALTH=$(docker exec -it iit-ml-redis redis-cli ping)
echo "Redis: $REDIS_HEALTH"

# ECS Tasks
ECS_RUNNING=$(aws ecs describe-services --cluster iit-ml-production --services iit-ml-backend --query 'services[0].runningCount' --output text)
echo "ECS Backend Tasks Running: $ECS_RUNNING"
```

---

## Security Best Practices

1. **Rotate credentials regularly** (every 90 days)
2. **Enable encryption at rest** for all data stores
3. **Use VPC endpoints** for AWS services
4. **Enable AWS Shield** for DDoS protection
5. **Regular security audits** with AWS Inspector
6. **Enable CloudTrail** for API logging
7. **Use secrets manager** for sensitive data

---

## Backup Strategy

### Automated Backups

- **RDS**: Daily backups, 30-day retention
- **ECS**: Task definitions and service configs in Terraform
- **S3**: Versioning enabled for static assets

### Manual Backup

```bash
# Database backup
aws rds create-db-snapshot \
  --db-instance-identifier iit-ml-production \
  --db-snapshot-identifier manual-backup-$(date +%Y%m%d)

# Application data backup
aws s3 sync s3://iit-ml-production-data s3://iit-ml-backups/$(date +%Y%m%d)
```

---

## Support and Maintenance

### Regular Maintenance Tasks

| Task | Frequency | Command |
|------|-----------|---------|
| Database vacuum | Weekly | `docker-compose exec backend alembic vacuum` |
| Log rotation | Daily | Automatic via CloudWatch |
| Security patches | Monthly | `terraform apply` |
| Model retraining | Quarterly | Via admin interface |

### Contact Information

- **Infrastructure Team**: infra@example.com
- **Application Team**: app@example.com
- **On-Call**: +1-555-0123

---

## Appendix

### Useful Commands

```bash
# SSH into ECS container (requires ECS exec enabled)
aws ecs execute-command \
  --cluster iit-ml-production \
  --task <task-id> \
  --container backend \
  --command "/bin/bash" \
  --interactive

# View recent deployments
aws ecs describe-services --cluster iit-ml-production --services iit-ml-backend --query 'services[0].deployments'

# Scale ECS service
aws ecs update-service --cluster iit-ml-production --service iit-ml-backend --desired-count 5

# Get CloudWatch metrics
aws cloudwatch get-metric-statistics --namespace AWS/ECS --metric-name CPUUtilization --dimensions Name=ServiceName,Value=iit-ml-backend --start-time 2024-01-01T00:00:00Z --end-time 2024-01-01T23:59:59Z --period 3600 --statistics Average
```

### Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)

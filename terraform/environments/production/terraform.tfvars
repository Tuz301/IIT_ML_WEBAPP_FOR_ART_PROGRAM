# Production Environment Variables
environment = "production"
aws_region = "us-east-1"

# VPC Configuration
vpc_cidr = "10.0.0.0/16"
public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
private_subnet_cidrs = ["10.0.10.0/24", "10.0.11.0/24", "10.0.12.0/24"]
database_subnet_cidrs = ["10.0.20.0/24", "10.0.21.0/24", "10.0.22.0/24"]

# ECS Configuration
ecs_cluster_name = "iit-ml-production"
backend_container_name = "iit-ml-backend"
frontend_container_name = "iit-ml-frontend"
backend_cpu = 1024
backend_memory = 2048
backend_desired_count = 3
frontend_cpu = 256
frontend_memory = 512
frontend_desired_count = 2

# RDS Configuration
db_instance_class = "db.r6g.xlarge"
db_allocated_storage = 100
db_max_allocated_storage = 1000
db_engine_version = "15.4"
db_backup_retention_period = 30
db_multi_az = true

# ElastiCache Configuration
redis_node_type = "cache.r6g.large"
redis_num_cache_nodes = 3
redis_replication_group_enabled = true

# Application Load Balancer
alb_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
alb_health_check_path = "/health"
alb_health_check_interval = 30
alb_health_check_timeout = 5
alb_healthy_threshold = 3
alb_unhealthy_threshold = 3

# Domain Configuration
domain_name = "iit-ml.example.com"
certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# Monitoring and Logging
enable_cloudwatch_alarms = true
enable_xray_tracing = true
log_retention_days = 30

# Auto Scaling
enable_autoscaling = true
backend_min_capacity = 2
backend_max_capacity = 10
backend_target_cpu_percent = 70
frontend_min_capacity = 2
frontend_max_capacity = 5
frontend_target_cpu_percent = 70

# Tags
tags = {
  Environment = "production"
  Project     = "IIT-ML-Service"
  ManagedBy   = "Terraform"
  CostCenter  = "IHVN"
}

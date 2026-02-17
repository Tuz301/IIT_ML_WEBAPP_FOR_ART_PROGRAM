# Staging Environment Variables
environment = "staging"
aws_region = "us-east-1"

# VPC Configuration
vpc_cidr = "10.1.0.0/16"
public_subnet_cidrs = ["10.1.1.0/24", "10.1.2.0/24"]
private_subnet_cidrs = ["10.1.10.0/24", "10.1.11.0/24"]
database_subnet_cidrs = ["10.1.20.0/24", "10.1.21.0/24"]

# ECS Configuration
ecs_cluster_name = "iit-ml-staging"
backend_container_name = "iit-ml-backend"
frontend_container_name = "iit-ml-frontend"
backend_cpu = 512
backend_memory = 1024
backend_desired_count = 2
frontend_cpu = 256
frontend_memory = 512
frontend_desired_count = 1

# RDS Configuration
db_instance_class = "db.t3.medium"
db_allocated_storage = 20
db_max_allocated_storage = 100
db_engine_version = "15.4"
db_backup_retention_period = 7
db_multi_az = false

# ElastiCache Configuration
redis_node_type = "cache.t3.medium"
redis_num_cache_nodes = 1
redis_replication_group_enabled = false

# Application Load Balancer
alb_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
alb_health_check_path = "/health"
alb_health_check_interval = 30
alb_health_check_timeout = 5
alb_healthy_threshold = 2
alb_unhealthy_threshold = 5

# Domain Configuration
domain_name = "staging.iit-ml.example.com"
certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# Monitoring and Logging
enable_cloudwatch_alarms = true
enable_xray_tracing = false
log_retention_days = 7

# Auto Scaling
enable_autoscaling = false
backend_min_capacity = 1
backend_max_capacity = 3
backend_target_cpu_percent = 70
frontend_min_capacity = 1
frontend_max_capacity = 2
frontend_target_cpu_percent = 70

# Tags
tags = {
  Environment = "staging"
  Project     = "IIT-ML-Service"
  ManagedBy   = "Terraform"
  CostCenter  = "IHVN"
}

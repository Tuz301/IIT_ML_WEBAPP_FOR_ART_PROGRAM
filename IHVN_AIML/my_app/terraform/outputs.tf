# VPC Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.iit_ml_vpc.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

# Load Balancer Outputs
output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.iit_ml_alb.dns_name
}

output "alb_zone_id" {
  description = "ALB zone ID"
  value       = aws_lb.iit_ml_alb.zone_id
}

# Database Outputs
output "db_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.iit_ml_db.endpoint
}

output "db_port" {
  description = "RDS port"
  value       = aws_db_instance.iit_ml_db.port
}

# Cache Outputs
output "cache_endpoint" {
  description = "ElastiCache endpoint"
  value       = aws_elasticache_cluster.iit_ml_cache.cache_nodes[0].address
}

output "cache_port" {
  description = "ElastiCache port"
  value       = aws_elasticache_cluster.iit_ml_cache.port
}

# ECS Outputs
output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.iit_ml_cluster.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.iit_ml_service.name
}

# CloudFront Outputs
output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.iit_ml_cdn.id
}

output "cloudfront_domain_name" {
  description = "CloudFront domain name"
  value       = aws_cloudfront_distribution.iit_ml_cdn.domain_name
}

# IAM Outputs
output "ecs_execution_role_arn" {
  description = "ECS execution role ARN"
  value       = aws_iam_role.ecs_execution_role.arn
}

output "ecs_task_role_arn" {
  description = "ECS task role ARN"
  value       = aws_iam_role.ecs_task_role.arn
}

# CloudWatch Alarms and Monitoring Configuration

# ============================================
# CloudWatch Log Groups
# ============================================
resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/iit-ml-${var.environment}/backend"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/iit-ml-${var.environment}/frontend"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "nginx" {
  name              = "/ecs/iit-ml-${var.environment}/nginx"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# ============================================
# CloudWatch Alarms - Backend
# ============================================
resource "aws_cloudwatch_metric_alarm" "backend_cpu_high" {
  count               = var.enable_cloudwatch_alarms ? 1 : 0
  alarm_name          = "iit-ml-${var.environment}-backend-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    ServiceName = aws_ecs_service.backend.name
    ClusterName = aws_ecs_cluster.main.name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "backend_memory_high" {
  count               = var.enable_cloudwatch_alarms ? 1 : 0
  alarm_name          = "iit-ml-${var.environment}-backend-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "85"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    ServiceName = aws_ecs_service.backend.name
    ClusterName = aws_ecs_cluster.main.name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "backend_5xx_errors" {
  count               = var.enable_cloudwatch_alarms ? 1 : 0
  alarm_name          = "iit-ml-${var.environment}-backend-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HTTPCode_ELB_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "50"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "backend_latency_high" {
  count               = var.enable_cloudwatch_alarms ? 1 : 0
  alarm_name          = "iit-ml-${var.environment}-backend-latency-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Average"
  threshold           = "1"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
    TargetGroup  = aws_lb_target_group.backend.arn_suffix
  }

  tags = var.tags
}

# ============================================
# CloudWatch Alarms - Database
# ============================================
resource "aws_cloudwatch_metric_alarm" "rds_cpu_high" {
  count               = var.enable_cloudwatch_alarms ? 1 : 0
  alarm_name          = "iit-ml-${var.environment}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.identifier
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "rds_storage_low" {
  count               = var.enable_cloudwatch_alarms ? 1 : 0
  alarm_name          = "iit-ml-${var.environment}-rds-storage-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "2000000000"  # 2GB in bytes
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.identifier
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "rds_connections_high" {
  count               = var.enable_cloudwatch_alarms ? 1 : 0
  alarm_name          = "iit-ml-${var.environment}-rds-connections-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "50"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.identifier
  }

  tags = var.tags
}

# ============================================
# CloudWatch Alarms - Redis
# ============================================
resource "aws_cloudwatch_metric_alarm" "redis_cpu_high" {
  count               = var.enable_cloudwatch_alarms ? 1 : 0
  alarm_name          = "iit-ml-${var.environment}-redis-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.main.id
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "redis_memory_high" {
  count               = var.enable_cloudwatch_alarms ? 1 : 0
  alarm_name          = "iit-ml-${var.environment}-redis-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "FreeableMemory"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "100000000"  # 100MB in bytes
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.main.id
  }

  tags = var.tags
}

# ============================================
# CloudWatch Dashboards
# ============================================
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "iit-ml-${var.environment}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", aws_ecs_service.backend.name, "ClusterName", aws_ecs_cluster.main.name],
            [".", "MemoryUtilization", ".", ".", ".", "."],
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Backend ECS Metrics"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", aws_lb.main.arn_suffix],
            [".", "TargetResponseTime", ".", ".", "TargetGroup", aws_lb_target_group.backend.arn_suffix],
            [".", "HTTPCode_ELB_5XX_Count", ".", "."],
            [".", "HTTPCode_ELB_4XX_Count", ".", "."],
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "ALB Metrics"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", aws_db_instance.main.identifier],
            [".", "FreeStorageSpace", ".", "."],
            [".", "DatabaseConnections", ".", "."],
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "RDS Metrics"
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 18
        width  = 24
        height = 6

        properties = {
          logGroupName  = aws_cloudwatch_log_group.backend.name
          region        = var.aws_region
          title         = "Backend Logs"
          view          = "table"
        }
      }
    ]
  })
}

# ============================================
# SNS Topic for Alerts
# ============================================
resource "aws_sns_topic" "alerts" {
  name = "iit-ml-${var.environment}-alerts"

  tags = var.tags
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alerts_email
}

# ============================================
# X-Ray Tracing
# ============================================
resource "aws_xray_sampling_rule" "main" {
  count = var.enable_xray_tracing ? 1 : 0

  rule_name      = "iit-ml-${var.environment}-sampling"
  priority       = 100
  version        = 1
  reservoir_size = 1
  fixed_rate     = 0.1
  url_path       = "*"
  host           = "*"
  http_method    = "*"
  service_type   = "*"
  resource_arn   = "*"
  tags           = var.tags
}

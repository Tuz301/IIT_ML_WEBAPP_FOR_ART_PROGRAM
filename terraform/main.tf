# AWS Provider Configuration
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC Configuration
resource "aws_vpc" "iit_ml_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "iit-ml-vpc"
    Environment = var.environment
    Project     = "IIT-ML-Service"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "iit_ml_igw" {
  vpc_id = aws_vpc.iit_ml_vpc.id

  tags = {
    Name        = "iit-ml-igw"
    Environment = var.environment
  }
}

# Public Subnets
resource "aws_subnet" "public" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = aws_vpc.iit_ml_vpc.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name        = "iit-ml-public-subnet-${count.index + 1}"
    Environment = var.environment
    Type        = "Public"
  }
}

# Private Subnets
resource "aws_subnet" "private" {
  count             = length(var.private_subnet_cidrs)
  vpc_id            = aws_vpc.iit_ml_vpc.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name        = "iit-ml-private-subnet-${count.index + 1}"
    Environment = var.environment
    Type        = "Private"
  }
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.iit_ml_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.iit_ml_igw.id
  }

  tags = {
    Name        = "iit-ml-public-rt"
    Environment = var.environment
  }
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# NAT Gateway for Private Subnets
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name        = "iit-ml-nat-eip"
    Environment = var.environment
  }
}

resource "aws_nat_gateway" "iit_ml_nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name        = "iit-ml-nat"
    Environment = var.environment
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.iit_ml_vpc.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.iit_ml_nat.id
  }

  tags = {
    Name        = "iit-ml-private-rt"
    Environment = var.environment
  }
}

resource "aws_route_table_association" "private" {
  count          = length(aws_subnet.private)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# Security Groups
resource "aws_security_group" "alb" {
  name_prefix = "iit-ml-alb-"
  vpc_id      = aws_vpc.iit_ml_vpc.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "iit-ml-alb-sg"
    Environment = var.environment
  }
}

resource "aws_security_group" "ecs" {
  name_prefix = "iit-ml-ecs-"
  vpc_id      = aws_vpc.iit_ml_vpc.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "iit-ml-ecs-sg"
    Environment = var.environment
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "iit-ml-rds-"
  vpc_id      = aws_vpc.iit_ml_vpc.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "iit-ml-rds-sg"
    Environment = var.environment
  }
}

# Application Load Balancer
resource "aws_lb" "iit_ml_alb" {
  name               = "iit-ml-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = var.environment == "production"

  tags = {
    Name        = "iit-ml-alb"
    Environment = var.environment
  }
}

resource "aws_lb_target_group" "iit_ml_tg" {
  name_prefix = "iit-ml-"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.iit_ml_vpc.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = {
    Name        = "iit-ml-tg"
    Environment = var.environment
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.iit_ml_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.iit_ml_tg.arn
  }
}

# RDS Multi-AZ Database
resource "aws_db_subnet_group" "iit_ml_db" {
  name       = "iit-ml-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name        = "iit-ml-db-subnet-group"
    Environment = var.environment
  }
}

resource "aws_db_instance" "iit_ml_db" {
  identifier             = "iit-ml-db"
  engine                 = "postgres"
  engine_version         = "16.1"
  instance_class         = var.db_instance_class
  allocated_storage      = var.db_allocated_storage
  storage_type           = "gp3"
  multi_az               = true
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.iit_ml_db.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  skip_final_snapshot    = var.environment != "production"
  backup_retention_period = 7

  tags = {
    Name        = "iit-ml-db"
    Environment = var.environment
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "iit_ml_cluster" {
  name = "iit-ml-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "iit-ml-cluster"
    Environment = var.environment
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "iit_ml_task" {
  family                   = "iit-ml-service"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "iit-ml-service"
      image = "${var.ecr_repository_url}:latest"

      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "DATABASE_URL"
          value = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.iit_ml_db.endpoint}/${var.db_name}"
        },
        {
          name  = "REDIS_URL"
          value = aws_elasticache_cluster.iit_ml_cache.cache_nodes[0].address
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/iit-ml-service"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval = 30
        timeout  = 5
        retries  = 3
      }
    }
  ])

  tags = {
    Name        = "iit-ml-task"
    Environment = var.environment
  }
}

# ECS Service
resource "aws_ecs_service" "iit_ml_service" {
  name            = "iit-ml-service"
  cluster         = aws_ecs_cluster.iit_ml_cluster.id
  task_definition = aws_ecs_task_definition.iit_ml_task.arn
  desired_count   = var.desired_count

  network_configuration {
    security_groups  = [aws_security_group.ecs.id]
    subnets          = aws_subnet.private[*].id
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.iit_ml_tg.arn
    container_name   = "iit-ml-service"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Name        = "iit-ml-service"
    Environment = var.environment
  }
}

# Auto Scaling
resource "aws_appautoscaling_target" "ecs_target" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.iit_ml_cluster.name}/${aws_ecs_service.iit_ml_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ecs_cpu_policy" {
  name               = "cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

resource "aws_appautoscaling_policy" "ecs_memory_policy" {
  name               = "memory-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value = 80.0
  }
}

# ElastiCache (Redis) for Feature Store
resource "aws_elasticache_subnet_group" "iit_ml_cache" {
  name       = "iit-ml-cache-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_cluster" "iit_ml_cache" {
  cluster_id           = "iit-ml-cache"
  engine               = "redis"
  node_type            = var.cache_node_type
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.iit_ml_cache.name
  security_group_ids   = [aws_security_group.ecs.id]

  tags = {
    Name        = "iit-ml-cache"
    Environment = var.environment
  }
}

# CloudFront CDN
resource "aws_cloudfront_distribution" "iit_ml_cdn" {
  origin {
    domain_name = aws_lb.iit_ml_alb.dns_name
    origin_id   = "iit-ml-alb"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "IIT ML Service CDN"
  default_root_object = ""

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "iit-ml-alb"

    forwarded_values {
      query_string = true
      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name        = "iit-ml-cdn"
    Environment = var.environment
  }
}

# IAM Roles
resource "aws_iam_role" "ecs_execution_role" {
  name = "iit-ml-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "iit-ml-ecs-execution-role"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task_role" {
  name = "iit-ml-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "iit-ml-ecs-task-role"
    Environment = var.environment
  }
}

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "iit_ml_logs" {
  name              = "/ecs/iit-ml-service"
  retention_in_days = 30

  tags = {
    Name        = "iit-ml-logs"
    Environment = var.environment
  }
}

# Data source for availability zones
data "aws_availability_zones" "available" {
  state = "available"
}

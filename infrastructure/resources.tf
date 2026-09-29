# =============================================================================
# SQS QUEUES
# =============================================================================
resource "aws_sqs_queue" "discovery" {
  name                       = "${var.project_name}-discovery"
  visibility_timeout_seconds = 300
  message_retention_seconds  = 86400
}

resource "aws_sqs_queue" "evaluation" {
  name                       = "${var.project_name}-evaluation"
  visibility_timeout_seconds = 300
  message_retention_seconds  = 86400
}

resource "aws_sqs_queue" "applications" {
  name                       = "${var.project_name}-applications"
  visibility_timeout_seconds = 600
  message_retention_seconds  = 86400
}

resource "aws_sqs_queue" "notifications" {
  name                       = "${var.project_name}-notifications"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 86400
}

resource "aws_sqs_queue" "approvals" {
  name                       = "${var.project_name}-approvals"
  visibility_timeout_seconds = 3600
  message_retention_seconds  = 604800   # 7 days
}

# =============================================================================
# S3 BUCKETS
# =============================================================================
resource "aws_s3_bucket" "resumes" {
  bucket = "${var.project_name}-resumes-${var.environment}"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "resumes" {
  bucket = aws_s3_bucket.resumes.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "resumes" {
  bucket                  = aws_s3_bucket.resumes.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "config" {
  bucket = "${var.project_name}-config-${var.environment}"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "config" {
  bucket = aws_s3_bucket.config.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "config" {
  bucket                  = aws_s3_bucket.config.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# =============================================================================
# SECRETS MANAGER
# =============================================================================
resource "aws_secretsmanager_secret" "database" {
  name                    = "${var.project_name}/database"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "database" {
  secret_id = aws_secretsmanager_secret.database.id
  secret_string = jsonencode({
    username = "jobagent"
    password = var.db_password
    host     = aws_db_instance.postgres.address
    port     = 5432
    dbname   = "job_agent"
  })
}

# =============================================================================
# RDS POSTGRESQL
# =============================================================================
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "postgres" {
  identifier             = "${var.project_name}-db"
  engine                 = "postgres"
  engine_version         = "16.1"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  storage_encrypted      = true
  db_name                = "job_agent"
  username               = "jobagent"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  skip_final_snapshot    = false
  final_snapshot_identifier = "${var.project_name}-final-snapshot"
  backup_retention_period = 7
  deletion_protection    = true
}

# =============================================================================
# VPC
# =============================================================================
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "${var.project_name}-vpc" }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags = { Name = "${var.project_name}-private-${count.index}" }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 10}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  tags = { Name = "${var.project_name}-public-${count.index}" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  depends_on    = [aws_internet_gateway.main]
}

resource "aws_eip" "nat" { domain = "vpc" }

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

data "aws_availability_zones" "available" { state = "available" }

# =============================================================================
# SECURITY GROUPS
# =============================================================================
resource "aws_security_group" "rds" {
  name   = "${var.project_name}-rds-sg"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }
  egress { from_port = 0; to_port = 0; protocol = "-1"; cidr_blocks = ["0.0.0.0/0"] }
}

resource "aws_security_group" "ecs_tasks" {
  name   = "${var.project_name}-ecs-sg"
  vpc_id = aws_vpc.main.id
  egress { from_port = 0; to_port = 0; protocol = "-1"; cidr_blocks = ["0.0.0.0/0"] }
}

# =============================================================================
# ECS CLUSTER + FARGATE TASK (Agent Runner)
# =============================================================================
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"
}

resource "aws_ecs_task_definition" "agent" {
  family                   = "${var.project_name}-agent"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "agent"
    image = var.ecr_image_uri
    environment = [
      { name = "ENV",        value = var.environment },
      { name = "AWS_REGION", value = var.aws_region },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/${var.project_name}"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "agent"
      }
    }
  }])
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 30
}

# =============================================================================
# EVENTBRIDGE SCHEDULES
# =============================================================================
resource "aws_scheduler_schedule" "discovery" {
  name       = "${var.project_name}-discovery"
  group_name = "default"

  flexible_time_window { mode = "OFF" }
  schedule_expression = "rate(4 hours)"

  target {
    arn      = aws_ecs_cluster.main.arn
    role_arn = aws_iam_role.scheduler.arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.agent.arn
      launch_type         = "FARGATE"
      network_configuration {
        subnets          = aws_subnet.private[*].id
        security_groups  = [aws_security_group.ecs_tasks.id]
        assign_public_ip = false
      }
    }

    input = jsonencode({ task = "discovery" })
  }
}

resource "aws_scheduler_schedule" "matching" {
  name       = "${var.project_name}-matching"
  group_name = "default"

  flexible_time_window { mode = "OFF" }
  schedule_expression = "rate(30 minutes)"

  target {
    arn      = aws_ecs_cluster.main.arn
    role_arn = aws_iam_role.scheduler.arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.agent.arn
      launch_type         = "FARGATE"
      network_configuration {
        subnets          = aws_subnet.private[*].id
        security_groups  = [aws_security_group.ecs_tasks.id]
        assign_public_ip = false
      }
    }

    input = jsonencode({ task = "matching" })
  }
}

resource "aws_scheduler_schedule" "daily_summary" {
  name       = "${var.project_name}-daily-summary"
  group_name = "default"

  flexible_time_window { mode = "OFF" }
  schedule_expression = "cron(30 2 * * ? *)"   # 2:30 AM UTC = 8:00 AM IST

  target {
    arn      = aws_ecs_cluster.main.arn
    role_arn = aws_iam_role.scheduler.arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.agent.arn
      launch_type         = "FARGATE"
      network_configuration {
        subnets          = aws_subnet.private[*].id
        security_groups  = [aws_security_group.ecs_tasks.id]
        assign_public_ip = false
      }
    }

    input = jsonencode({ task = "daily_summary" })
  }
}

# =============================================================================
# IAM ROLES
# =============================================================================
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task" {
  name = "${var.project_name}-ecs-task-policy"
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.resumes.arn,
          "${aws_s3_bucket.resumes.arn}/*",
          aws_s3_bucket.config.arn,
          "${aws_s3_bucket.config.arn}/*",
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage"]
        Resource = [
          aws_sqs_queue.discovery.arn,
          aws_sqs_queue.evaluation.arn,
          aws_sqs_queue.applications.arn,
          aws_sqs_queue.notifications.arn,
          aws_sqs_queue.approvals.arn,
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_secretsmanager_secret.database.arn
      },
      {
        Effect   = "Allow"
        Action   = ["ses:SendEmail"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role" "ecs_execution" {
  name = "${var.project_name}-ecs-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "scheduler" {
  name = "${var.project_name}-scheduler-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "scheduler" {
  name = "${var.project_name}-scheduler-policy"
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ecs:RunTask"]
      Resource = aws_ecs_task_definition.agent.arn
    }, {
      Effect   = "Allow"
      Action   = ["iam:PassRole"]
      Resource = [aws_iam_role.ecs_task.arn, aws_iam_role.ecs_execution.arn]
    }]
  })
}

# =============================================================================
# SES EMAIL IDENTITY
# =============================================================================
resource "aws_ses_email_identity" "candidate" {
  email = var.candidate_email
}

# =============================================================================
# OUTPUTS
# =============================================================================
output "rds_endpoint"          { value = aws_db_instance.postgres.address }
output "resumes_bucket"        { value = aws_s3_bucket.resumes.bucket }
output "discovery_queue_url"   { value = aws_sqs_queue.discovery.url }
output "notification_queue_url" { value = aws_sqs_queue.notifications.url }
output "ecs_cluster_name"      { value = aws_ecs_cluster.main.name }

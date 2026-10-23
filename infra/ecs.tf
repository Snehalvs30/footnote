# Runs the Footnote container on Fargate: AWS manages the servers.

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.name}"
  retention_in_days = 7
}

resource "aws_ecs_cluster" "main" {
  name = var.name
}

# ---- Permissions ECS itself needs to start the container ----------------------

resource "aws_iam_role" "execution" {
  name = "${var.name}-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Pull from ECR and write logs.
resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Read exactly one secret: least privilege.
resource "aws_iam_role_policy" "read_app_secret" {
  name = "read-app-secret"
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "secretsmanager:GetSecretValue"
      Resource = aws_secretsmanager_secret.app.arn
    }]
  })
}

# ---- What to run --------------------------------------------------------------

locals {
  secret_arn = aws_secretsmanager_secret.app.arn
}

resource "aws_ecs_task_definition" "app" {
  family                   = var.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024 # 1 vCPU
  memory                   = 2048 # 2 GB: the embedding model needs room
  execution_role_arn       = aws_iam_role.execution.arn

  # ARM (Graviton): matches images built on Apple Silicon Macs, and costs less.
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([{
    name         = "app"
    image        = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
    essential    = true
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]

    environment = [
      { name = "FOOTNOTE_LLM_PROVIDER", value = "anthropic" },
      # CloudFront serves the site over HTTPS, so cookies can require it.
      { name = "FOOTNOTE_COOKIE_SECURE", value = "true" },
    ]

    secrets = [
      { name = "FOOTNOTE_DATABASE_URL", valueFrom = "${local.secret_arn}:DATABASE_URL::" },
      { name = "FOOTNOTE_JWT_SECRET", valueFrom = "${local.secret_arn}:JWT_SECRET::" },
      { name = "FOOTNOTE_ANTHROPIC_API_KEY", valueFrom = "${local.secret_arn}:ANTHROPIC_API_KEY::" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "app"
      }
    }
  }])
}

resource "aws_ecs_service" "app" {
  name            = var.name
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = 8000
  }

  # Startup runs migrations and loads the embedding model: give it time before
  # health checks count.
  health_check_grace_period_seconds = 120

  # If a new version never becomes healthy, roll back to the previous one.
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [aws_lb_listener.http, aws_secretsmanager_secret_version.app]
}

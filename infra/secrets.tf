# One secret holding everything sensitive the app needs. ECS reads it when a
# container starts and passes each key in as an environment variable, so secrets
# never appear in the image, the task definition, or the logs.
#
# Note: Terraform state also contains these values, which is why terraform.tfstate
# must never be committed.

resource "random_password" "jwt" {
  length  = 64
  special = false
}

resource "aws_secretsmanager_secret" "app" {
  name = "${var.name}/app"
  # Delete immediately on destroy (default is a 7-30 day recovery window, which
  # would block re-creating a secret with the same name).
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    DATABASE_URL      = "postgresql+psycopg://${aws_db_instance.main.username}:${random_password.db.result}@${aws_db_instance.main.address}:5432/${aws_db_instance.main.db_name}?sslmode=require"
    JWT_SECRET        = random_password.jwt.result
    ANTHROPIC_API_KEY = var.anthropic_api_key
  })
}

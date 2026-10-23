# PostgreSQL 17 on RDS. pgvector is available as an extension; migration 0001
# enables it with CREATE EXTENSION.

resource "random_password" "db" {
  length  = 32
  special = false # letters and digits only, so the password is safe inside a URL
}

resource "aws_db_subnet_group" "main" {
  name       = var.name
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "main" {
  identifier     = var.name
  engine         = "postgres"
  engine_version = "17"
  instance_class = "db.t4g.micro" # smallest Graviton (ARM) instance

  db_name  = "footnote"
  username = "footnote"
  password = random_password.db.result

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false

  # Demo settings: make `terraform destroy` quick and complete.
  # Production: deletion_protection = true, a final snapshot, longer backups, Multi-AZ.
  backup_retention_period = 1
  skip_final_snapshot     = true
  deletion_protection     = false
  apply_immediately       = true
}

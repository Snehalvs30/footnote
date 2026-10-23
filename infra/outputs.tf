output "app_url" {
  description = "Open this in a browser."
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "ecr_repository_url" {
  description = "Where to push the Footnote image."
  value       = aws_ecr_repository.app.repository_url
}

output "log_group" {
  description = "CloudWatch log group for the app's logs."
  value       = aws_cloudwatch_log_group.app.name
}

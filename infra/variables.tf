variable "region" {
  description = "AWS region to deploy into. Must match the AWS project's region."
  type        = string
  default     = "us-east-2"
}

variable "name" {
  description = "Prefix for resource names."
  type        = string
  default     = "footnote"
}

variable "image_tag" {
  description = "Tag of the image in ECR to run."
  type        = string
  default     = "latest"
}

variable "anthropic_api_key" {
  description = "Anthropic API key. Pass it as TF_VAR_anthropic_api_key, never in a file in the repo."
  type        = string
  sensitive   = true
}

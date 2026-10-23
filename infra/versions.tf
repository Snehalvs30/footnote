terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # State is stored locally in terraform.tfstate (gitignored: it contains secrets).
  # A team would keep it in an encrypted S3 bucket with locking instead.
}

provider "aws" {
  region = var.region

  # Every resource gets these tags, so it's obvious what belongs to Footnote.
  default_tags {
    tags = {
      Project   = "footnote"
      ManagedBy = "terraform"
    }
  }
}

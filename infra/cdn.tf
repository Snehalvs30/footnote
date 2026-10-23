# CloudFront: the public front door. Gives Footnote HTTPS on a *.cloudfront.net
# address without buying a domain, and is the only thing allowed to reach the
# load balancer (see security.tf).

data "aws_cloudfront_cache_policy" "disabled" {
  name = "Managed-CachingDisabled" # every request is dynamic or per-user
}

data "aws_cloudfront_origin_request_policy" "all_viewer" {
  name = "Managed-AllViewerExceptHostHeader" # pass cookies, headers and query strings through
}

resource "aws_cloudfront_distribution" "main" {
  enabled     = true
  comment     = "Footnote"
  price_class = "PriceClass_100" # North America and Europe edge locations only: cheapest

  origin {
    domain_name = aws_lb.main.dns_name
    origin_id   = "alb"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
      origin_read_timeout    = 60 # longest wait for the next bytes of a streamed answer
    }
  }

  default_cache_behavior {
    target_origin_id         = "alb"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = data.aws_cloudfront_cache_policy.disabled.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer.id
    compress                 = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

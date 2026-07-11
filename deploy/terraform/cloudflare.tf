provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# ============================================
# DNS
# ============================================

resource "cloudflare_dns_record" "babylon" {
  count   = var.manage_cloudflare ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = var.cloudflare_record_name
  content = hcloud_server.vps[0].ipv4_address
  type    = "A"
  proxied = true
  ttl     = 1
}

# ============================================
# ZONE SETTINGS
# ============================================

resource "cloudflare_zone_setting" "ssl" {
  count      = (var.manage_cloudflare && var.enable_cloudflare_zone_settings) ? 1 : 0
  zone_id    = var.cloudflare_zone_id
  setting_id = "ssl"
  value      = "strict"
}

resource "cloudflare_zone_setting" "always_use_https" {
  count      = (var.manage_cloudflare && var.enable_cloudflare_zone_settings) ? 1 : 0
  zone_id    = var.cloudflare_zone_id
  setting_id = "always_use_https"
  value      = "on"
}

resource "cloudflare_zone_setting" "min_tls_version" {
  count      = (var.manage_cloudflare && var.enable_cloudflare_zone_settings) ? 1 : 0
  zone_id    = var.cloudflare_zone_id
  setting_id = "min_tls_version"
  value      = "1.2"
}

resource "cloudflare_zone_setting" "tls_1_3" {
  count      = (var.manage_cloudflare && var.enable_cloudflare_zone_settings) ? 1 : 0
  zone_id    = var.cloudflare_zone_id
  setting_id = "tls_1_3"
  value      = "on"
}

resource "cloudflare_zone_setting" "automatic_https_rewrites" {
  count      = (var.manage_cloudflare && var.enable_cloudflare_zone_settings) ? 1 : 0
  zone_id    = var.cloudflare_zone_id
  setting_id = "automatic_https_rewrites"
  value      = "on"
}

# ============================================
# RULESETS
# ============================================

resource "cloudflare_ruleset" "cache" {
  count       = (var.manage_cloudflare && var.enable_cloudflare_rulesets) ? 1 : 0
  zone_id     = var.cloudflare_zone_id
  name        = "Babylon cache rules"
  description = "Cache static assets, bypass API"
  kind        = "zone"
  phase       = "http_request_cache_settings"

  rules = [
    {
      action = "set_cache_settings"
      action_parameters = {
        cache = true
        edge_ttl = {
          mode    = "override_origin"
          default = 31536000
        }
        browser_ttl = {
          mode    = "override_origin"
          default = 31536000
        }
      }
      expression  = "(http.request.uri.path matches \"^/static/\")"
      description = "Cache static assets for 1 year"
      enabled     = true
    },
    {
      action = "set_cache_settings"
      action_parameters = {
        cache = false
      }
      expression  = "(http.request.uri.path matches \"^/api/\" or http.request.uri.path matches \"^/admin/\")"
      description = "Bypass cache for API and admin"
      enabled     = true
    }
  ]
}

resource "cloudflare_ruleset" "rate_limit" {
  count       = (var.manage_cloudflare && var.enable_cloudflare_rulesets) ? 1 : 0
  zone_id     = var.cloudflare_zone_id
  name        = "Babylon API rate limiting"
  description = "Prevent API abuse"
  kind        = "zone"
  phase       = "http_ratelimit"

  rules = [
    {
      action = "block"
      ratelimit = {
        characteristics     = ["cf.colo.id", "ip.src"]
        period              = 60
        requests_per_period = 60
        mitigation_timeout  = 600
      }
      expression  = "(http.request.uri.path matches \"^/api/\")"
      description = "API rate limit: 60 req/min per IP"
      enabled     = true
    }
  ]
}

# ============================================
# R2 BUCKETS
# ============================================

resource "cloudflare_r2_bucket" "backups" {
  count      = var.manage_cloudflare ? 1 : 0
  account_id = var.cloudflare_account_id
  name       = "babylon-backups"
  location   = "enam"
}

resource "cloudflare_r2_bucket" "reference" {
  count      = var.manage_cloudflare ? 1 : 0
  account_id = var.cloudflare_account_id
  name       = "babylon-reference"
  location   = "enam"
}

resource "cloudflare_r2_bucket" "archives" {
  count      = var.manage_cloudflare ? 1 : 0
  account_id = var.cloudflare_account_id
  name       = "babylon-archives"
  location   = "enam"
}

resource "cloudflare_r2_bucket_lifecycle" "backups" {
  count       = var.manage_cloudflare ? 1 : 0
  account_id  = var.cloudflare_account_id
  bucket_name = cloudflare_r2_bucket.backups[0].name

  rules = [
    {
      id      = "daily-retention"
      enabled = true
      conditions = {
        prefix = "daily/"
      }
      delete_objects_transition = {
        condition = {
          type    = "Age"
          max_age = 604800
        }
      }
    },
    {
      id      = "weekly-retention"
      enabled = true
      conditions = {
        prefix = "weekly/"
      }
      delete_objects_transition = {
        condition = {
          type    = "Age"
          max_age = 2419200
        }
      }
    }
  ]
}

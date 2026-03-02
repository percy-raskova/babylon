# Hetzner VPS Provisioning with Terraform
# Provisions VPS servers on Hetzner Cloud with proper configuration

terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }
}
provider "hcloud" {
  token = var.hcloud_token
}

# ============================================
# SSH KEY
# ============================================

resource "hcloud_ssh_key" "babylon" {
  count      = var.existing_ssh_key_id == null ? 1 : 0
  name       = var.ssh_key_name
  public_key = file(var.ssh_public_key_path)
}

locals {
  hcloud_ssh_key_id = var.existing_ssh_key_id != null ? var.existing_ssh_key_id : hcloud_ssh_key.babylon[0].id
}

# ============================================
# FIREWALL
# ============================================

resource "hcloud_firewall" "default" {
  name = "${var.project_name}-firewall"

  # SSH access
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = var.ssh_allowed_ips
  }

  # HTTPS from Cloudflare IPv4 ranges
  dynamic "rule" {
    for_each = var.cloudflare_ipv4_ranges
    content {
      direction  = "in"
      protocol   = "tcp"
      port       = "443"
      source_ips = [rule.value]
    }
  }

  # HTTPS from Cloudflare IPv6 ranges
  dynamic "rule" {
    for_each = var.cloudflare_ipv6_ranges
    content {
      direction  = "in"
      protocol   = "tcp"
      port       = "443"
      source_ips = [rule.value]
    }
  }

  # Dokploy (if applicable)
  dynamic "rule" {
    for_each = var.enable_dokploy_port ? [1] : []
    content {
      direction  = "in"
      protocol   = "tcp"
      port       = "3000"
      source_ips = var.dokploy_allowed_ips
    }
  }

  # Custom ports
  dynamic "rule" {
    for_each = var.custom_tcp_ports
    content {
      direction  = "in"
      protocol   = "tcp"
      port       = rule.value.port
      source_ips = rule.value.allowed_ips
    }
  }

  # Allow all outbound traffic
  rule {
    direction       = "out"
    protocol        = "tcp"
    port            = "any"
    destination_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction       = "out"
    protocol        = "udp"
    port            = "any"
    destination_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction       = "out"
    protocol        = "icmp"
    destination_ips = ["0.0.0.0/0", "::/0"]
  }
}

# ============================================
# VPS SERVERS
# ============================================

resource "hcloud_server" "vps" {
  count        = var.server_count
  name         = "${var.project_name}-${count.index + 1}"
  server_type  = var.server_type
  image        = var.server_image
  location     = var.server_location
  ssh_keys     = [local.hcloud_ssh_key_id]
  firewall_ids = [hcloud_firewall.default.id]

  labels = merge(
    var.server_labels,
    {
      project     = var.project_name
      environment = var.environment
      managed_by  = "terraform"
    }
  )

  # User data for initial setup
  user_data = templatefile("${path.module}/cloud-init.yaml", {
    hostname       = "${var.project_name}-${count.index + 1}"
    ssh_public_key = file(var.ssh_public_key_path)
  })

  # Attach to private network if enabled
  dynamic "network" {
    for_each = var.enable_private_network ? [1] : []
    content {
      network_id = hcloud_network.private[0].id
      ip         = cidrhost(var.private_subnet_ip_range, 10 + count.index)
    }
  }

  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = false
  }
}

# ============================================
# NETWORK (Optional - for private networking)
# ============================================

resource "hcloud_network" "private" {
  count    = var.enable_private_network ? 1 : 0
  name     = "${var.project_name}-network"
  ip_range = var.private_network_ip_range
}

resource "hcloud_network_subnet" "private" {
  count        = var.enable_private_network ? 1 : 0
  network_id   = hcloud_network.private[0].id
  type         = "cloud"
  network_zone = var.network_zone
  ip_range     = var.private_subnet_ip_range
}

# ============================================
# VOLUME (Optional - additional storage)
# ============================================

resource "hcloud_volume" "storage" {
  count     = var.enable_additional_storage ? var.server_count : 0
  name      = "${var.project_name}-storage-${count.index + 1}"
  size      = var.storage_size_gb
  server_id = hcloud_server.vps[count.index].id
  automount = true
  format    = "ext4"

  labels = {
    project     = var.project_name
    environment = var.environment
  }
}

# ============================================
# LOAD BALANCER (Optional - for multiple servers)
# ============================================

resource "hcloud_load_balancer" "lb" {
  count              = var.enable_load_balancer ? 1 : 0
  name               = "${var.project_name}-lb"
  load_balancer_type = var.load_balancer_type
  location           = var.server_location

  labels = {
    project     = var.project_name
    environment = var.environment
  }
}

resource "hcloud_load_balancer_target" "lb_target" {
  count            = var.enable_load_balancer ? var.server_count : 0
  type             = "server"
  load_balancer_id = hcloud_load_balancer.lb[0].id
  server_id        = hcloud_server.vps[count.index].id
  use_private_ip   = var.enable_private_network
}

resource "hcloud_load_balancer_service" "lb_service_http" {
  count            = var.enable_load_balancer ? 1 : 0
  load_balancer_id = hcloud_load_balancer.lb[0].id
  protocol         = "http"
  listen_port      = 80
  destination_port = 80

  health_check {
    protocol = "http"
    port     = 80
    interval = 10
    timeout  = 5
    retries  = 3
    http {
      path         = "/"
      status_codes = ["200", "301", "302"]
    }
  }
}

resource "hcloud_load_balancer_service" "lb_service_https" {
  count            = var.enable_load_balancer ? 1 : 0
  load_balancer_id = hcloud_load_balancer.lb[0].id
  protocol         = "https"
  listen_port      = 443
  destination_port = 443

  health_check {
    protocol = "tcp"
    port     = 443
    interval = 10
    timeout  = 5
    retries  = 3
  }
}

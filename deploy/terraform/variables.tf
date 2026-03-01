# Hetzner VPS Provisioning - Terraform Variables

# ============================================
# HETZNER API
# ============================================

variable "hcloud_token" {
  description = "Hetzner Cloud API token"
  type        = string
  sensitive   = true
}

# ============================================
# PROJECT CONFIGURATION
# ============================================

variable "project_name" {
  description = "Project name (used for resource naming)"
  type        = string
  default     = "my-project"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens"
  }
}

variable "environment" {
  description = "Environment (dev, staging, production)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production"
  }
}

# ============================================
# SSH KEY
# ============================================

variable "ssh_key_name" {
  description = "Name for the SSH key in Hetzner"
  type        = string
  default     = "terraform-key"
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key file"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

# ============================================
# FIREWALL RULES
# ============================================

variable "ssh_allowed_ips" {
  description = "List of IPs allowed to SSH (CIDR notation)"
  type        = list(string)
  default     = ["0.0.0.0/0", "::/0"]  # WARNING: Change this in production!
}

variable "enable_dokploy_port" {
  description = "Enable Dokploy port (3000) in firewall"
  type        = bool
  default     = false
}

variable "dokploy_allowed_ips" {
  description = "List of IPs allowed to access Dokploy port (CIDR notation)"
  type        = list(string)
  default     = ["0.0.0.0/0", "::/0"]
}

variable "custom_tcp_ports" {
  description = "Additional TCP ports to allow in firewall"
  type = list(object({
    port        = string
    allowed_ips = list(string)
  }))
  default = []
}

# ============================================
# SERVER CONFIGURATION
# ============================================

variable "server_count" {
  description = "Number of VPS servers to create"
  type        = number
  default     = 1

  validation {
    condition     = var.server_count > 0 && var.server_count <= 10
    error_message = "Server count must be between 1 and 10"
  }
}

variable "server_type" {
  description = "Hetzner server type (cpx11, cpx21, cpx31, etc.)"
  type        = string
  default     = "cpx21"  # 3 vCPU, 4GB RAM, 80GB disk
}

variable "server_image" {
  description = "Server OS image"
  type        = string
  default     = "ubuntu-22.04"
}

variable "server_location" {
  description = "Server location (fsn1, nbg1, hel1, ash, hil)"
  type        = string
  default     = "nbg1"  # Nuremberg, Germany

  validation {
    condition     = contains(["fsn1", "nbg1", "hel1", "ash", "hil"], var.server_location)
    error_message = "Location must be one of: fsn1 (Falkenstein), nbg1 (Nuremberg), hel1 (Helsinki), ash (Ashburn), hil (Hillsboro)"
  }
}

variable "server_labels" {
  description = "Additional labels for servers"
  type        = map(string)
  default     = {}
}

# ============================================
# NETWORKING
# ============================================

variable "enable_private_network" {
  description = "Enable private networking between servers"
  type        = bool
  default     = false
}

variable "private_network_ip_range" {
  description = "IP range for private network (CIDR)"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_ip_range" {
  description = "IP range for private subnet (CIDR)"
  type        = string
  default     = "10.0.1.0/24"
}

variable "network_zone" {
  description = "Network zone (eu-central, us-east, us-west)"
  type        = string
  default     = "eu-central"
}

# ============================================
# STORAGE
# ============================================

variable "enable_additional_storage" {
  description = "Attach additional volume to each server"
  type        = bool
  default     = false
}

variable "storage_size_gb" {
  description = "Size of additional storage volume in GB"
  type        = number
  default     = 50

  validation {
    condition     = var.storage_size_gb >= 10 && var.storage_size_gb <= 10000
    error_message = "Storage size must be between 10GB and 10000GB"
  }
}

# ============================================
# LOAD BALANCER
# ============================================

variable "enable_load_balancer" {
  description = "Enable load balancer for servers"
  type        = bool
  default     = false
}

variable "load_balancer_type" {
  description = "Load balancer type (lb11, lb21, lb31)"
  type        = string
  default     = "lb11"
}

# Hetzner VPS Provisioning - Terraform Outputs

# ============================================
# SERVER INFORMATION
# ============================================

output "server_ips" {
  description = "Public IP addresses of all servers"
  value = {
    for idx, server in hcloud_server.vps :
    server.name => server.ipv4_address
  }
}

output "server_ipv6" {
  description = "IPv6 addresses of all servers"
  value = {
    for idx, server in hcloud_server.vps :
    server.name => server.ipv6_address
  }
}

output "server_ids" {
  description = "Server IDs"
  value = {
    for idx, server in hcloud_server.vps :
    server.name => server.id
  }
}

output "server_status" {
  description = "Server status"
  value = {
    for idx, server in hcloud_server.vps :
    server.name => server.status
  }
}

# ============================================
# NETWORK INFORMATION
# ============================================

output "private_network_id" {
  description = "Private network ID (if enabled)"
  value       = var.enable_private_network ? hcloud_network.private[0].id : null
}

output "private_ips" {
  description = "Private IP addresses (if private network enabled)"
  value = var.enable_private_network ? {
    for idx, server in hcloud_server.vps :
    server.name => try(server.network[0].ip, null)
  } : {}
}

# ============================================
# LOAD BALANCER INFORMATION
# ============================================

output "load_balancer_ip" {
  description = "Load balancer IP address (if enabled)"
  value       = var.enable_load_balancer ? hcloud_load_balancer.lb[0].ipv4 : null
}

output "load_balancer_id" {
  description = "Load balancer ID (if enabled)"
  value       = var.enable_load_balancer ? hcloud_load_balancer.lb[0].id : null
}

# ============================================
# STORAGE INFORMATION
# ============================================

output "volume_ids" {
  description = "Volume IDs (if additional storage enabled)"
  value = var.enable_additional_storage ? {
    for idx, volume in hcloud_volume.storage :
    volume.name => volume.id
  } : {}
}

# ============================================
# SSH CONNECTION STRINGS
# ============================================

output "ssh_commands" {
  description = "SSH connection commands for each server"
  value = {
    for idx, server in hcloud_server.vps :
    server.name => "ssh root@${server.ipv4_address}"
  }
}

# ============================================
# ANSIBLE INVENTORY
# ============================================

output "ansible_inventory_ini" {
  description = "Ansible inventory in INI format"
  value = templatefile("${path.module}/templates/inventory.ini.tpl", {
    servers = [
      for server in hcloud_server.vps : {
        name       = server.name
        ip         = server.ipv4_address
        private_ip = var.enable_private_network ? try(server.network[0].ip, null) : null
      }
    ]
  })
}

output "ansible_inventory_yaml" {
  description = "Ansible inventory in YAML format"
  value = templatefile("${path.module}/templates/inventory.yml.tpl", {
    servers = [
      for server in hcloud_server.vps : {
        name       = server.name
        ip         = server.ipv4_address
        private_ip = var.enable_private_network ? try(server.network[0].ip, null) : null
      }
    ]
  })
}

# ============================================
# SUMMARY
# ============================================

output "summary" {
  description = "Deployment summary"
  value = <<-EOT
    ========================================
    Hetzner VPS Deployment Summary
    ========================================

    Project: ${var.project_name}
    Environment: ${var.environment}

    Servers Created: ${var.server_count}
    Server Type: ${var.server_type}
    Location: ${var.server_location}

    Public IPs:
    ${join("\n  ", [for name, ip in { for idx, server in hcloud_server.vps : server.name => server.ipv4_address } : "${name}: ${ip}"])}

    ${var.enable_private_network ? "Private Network: Enabled" : "Private Network: Disabled"}
    ${var.enable_load_balancer ? "Load Balancer: ${hcloud_load_balancer.lb[0].ipv4}" : "Load Balancer: Disabled"}
    ${var.enable_additional_storage ? "Additional Storage: ${var.storage_size_gb}GB per server" : "Additional Storage: Disabled"}

    Next Steps:
    1. Save Ansible inventory:
       terraform output -raw ansible_inventory_yaml > ../ansible/inventory.yml

    2. Configure servers with Ansible:
       cd ../ansible && ansible-playbook -i inventory.yml playbook.yml

    3. SSH to servers:
       ${join("\n     ", [for cmd in values({ for idx, server in hcloud_server.vps : server.name => "ssh root@${server.ipv4_address}" }) : cmd])}

    ========================================
  EOT
}

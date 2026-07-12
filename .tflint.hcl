# TFLint configuration for deploy/terraform.
#
# No tflint-ruleset plugin exists for the hcloud (Hetzner Cloud) provider, and
# no cloudflare ruleset plugin is registered here either — so this config
# enables only the built-in "terraform" ruleset (deprecated-interpolation,
# unused-declarations, comment-syntax, naming-convention, etc.).
# Provider-specific linting (hcloud_*, cloudflare_*) is out of reach until/
# unless such a plugin ships.

config {
  format = "compact"
}

plugin "terraform" {
  enabled = true
  preset  = "all"
}

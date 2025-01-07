# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.cu.name
}

output "provides" {
  value = {
    "fiveg_f1" = "fiveg_f1"
  }
}

output "requires" {
  value = {
    "fiveg_n2"       = "fiveg_n2"
    "fiveg_core_gnb" = "fiveg_core_gnb"
    "logging"        = "logging"
  }
}

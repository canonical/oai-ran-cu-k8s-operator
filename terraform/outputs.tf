# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.cu.name
}

# Required integration endpoints

output "fiveg_n2_endpoint" {
  description = "Name of the endpoint used to provide information on connectivity to the N2 plane."
  value       = "fiveg_n2"
}

# Provided integration endpoints

output "fiveg_gnb_identity_endpoint" {
  description = "Name of the endpoint used to provide information about simulated gNB instance."
  value       = "fiveg_gnb_identity"
}

output "fiveg_f1_endpoint" {
  description = "Name of the endpoint used to provide information about F1 interface."
  value       = "fiveg_f1"
}
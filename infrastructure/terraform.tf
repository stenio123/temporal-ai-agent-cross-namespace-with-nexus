terraform {
  required_providers {
    temporalcloud = {
      source = "temporalio/temporalcloud"
    }
  }
}

variable "temporal_api_key" {
  type      = string
  sensitive = true
}

variable "prefix" {
  type    = string
  default = "stenio"
}

provider "temporalcloud" {
  api_key = var.temporal_api_key
}

# --- Namespaces ---

resource "temporalcloud_namespace" "it_namespace" {
  name           = "${var.prefix}-it-namespace"
  regions        = ["aws-us-east-1"]
  api_key_auth   = true
  retention_days = 14
  timeouts {
    create = "10m"
    delete = "10m"
  }
}

resource "temporalcloud_namespace" "finance_namespace" {
  name           = "${var.prefix}-finance-namespace"
  regions        = ["aws-us-east-1"]
  api_key_auth   = true
  retention_days = 14
  timeouts {
    create = "10m"
    delete = "10m"
  }
}

# --- Nexus Endpoints ---

# 1. Endpoint for calling IT (Target: IT, Caller: Finance)
resource "temporalcloud_nexus_endpoint" "it_nexus_endpoint" {
  name        = "${var.prefix}-it-service-endpoint"
  description = "Allows Finance to call services in the IT namespace"

  worker_target = {
    namespace_id = temporalcloud_namespace.it_namespace.id
    task_queue   = "it-task-queue"
  }

  allowed_caller_namespaces = [
    temporalcloud_namespace.finance_namespace.id
  ]
}

# 2. Endpoint for calling Finance (Target: Finance, Caller: IT)
resource "temporalcloud_nexus_endpoint" "finance_nexus_endpoint" {
  name        = "${var.prefix}-finance-service-endpoint"
  description = "Allows IT to call services in the Finance namespace"

  worker_target = {
    namespace_id = temporalcloud_namespace.finance_namespace.id
    task_queue   = "finance-task-queue"
  }

  allowed_caller_namespaces = [
    temporalcloud_namespace.it_namespace.id
  ]
}

output "finance_namespace_id" {
  value       = temporalcloud_namespace.finance_namespace.id
  description = "Use this exact string in your Application Code"
}

output "finance_grpc_endpoint" {
  # The provider often gives you the specific address directly
  value = temporalcloud_namespace.finance_namespace.endpoints.grpc_address
}
output "it_namespace_id" {
  value       = temporalcloud_namespace.it_namespace.id
  description = "Use this exact string in your Application Code"
}

output "it_grpc_endpoint" {
  # The provider often gives you the specific address directly
  value = temporalcloud_namespace.finance_namespace.endpoints.grpc_address
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for the cluster and registry"
  type        = string
  default     = "us-central1"
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
  default     = "uptime-probe"
}

variable "github_repository" {
  description = "GitHub repository allowed to deploy, in owner/name form"
  type        = string
  default     = "joaooln/uptime-probe"
}

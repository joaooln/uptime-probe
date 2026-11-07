output "cluster_name" {
  value = google_container_cluster.this.name
}

output "registry" {
  description = "Image registry host/path"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "workload_identity_provider" {
  description = "Set as GitHub secret GCP_WORKLOAD_IDENTITY_PROVIDER"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deployer_service_account" {
  description = "Set as GitHub secret GCP_SERVICE_ACCOUNT"
  value       = google_service_account.deployer.email
}

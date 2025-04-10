output "landing_bucket_url" {
  description = "URL du bucket GCS pour les données brutes."
  value       = google_storage_bucket.landing_zone.url
}

output "processed_bucket_url" {
  description = "URL du bucket GCS pour les données traitées."
  value       = google_storage_bucket.processed_data.url
}

output "spark_scripts_bucket_url" {
  description = "URL du bucket GCS pour les scripts Spark."
  value       = google_storage_bucket.spark_scripts.url
}

output "bigquery_dataset_id" {
  description = "ID complet du dataset BigQuery."
  value       = google_bigquery_dataset.aeronautics_data.id # Renvoie project:dataset_id
}
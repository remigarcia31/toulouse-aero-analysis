resource "google_bigquery_dataset" "aeronautics_data" {
  dataset_id                  = var.bq_dataset_name
  project                     = var.gcp_project_id
  location                    = var.bq_location
  description                 = "Dataset contenant les données traitées sur l'activité aérienne."
  delete_contents_on_destroy  = false # Sécurité : ne pas vider le dataset si on détruit la ressource TF
}
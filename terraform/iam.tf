# Compte de service pour la fonction d'ingestion
resource "google_service_account" "ingest_function_sa" {
  account_id   = "cf-ingest-opensky-sa" # Nom court du compte de service
  display_name = "Service Account for OpenSky Ingestion Cloud Function"
  project      = var.gcp_project_id
}

# Permission d'écrire dans le bucket Landing Zone
resource "google_storage_bucket_iam_member" "ingest_sa_gcs_writer" {
  bucket = google_storage_bucket.landing_zone.name # Référence au bucket défini dans gcs.tf
  role   = "roles/storage.objectCreator" # Permission de créer des objets (fichiers)
  member = "serviceAccount:${google_service_account.ingest_function_sa.email}"
}

# Permission pour Cloud Scheduler d'invoquer la Cloud Function (si HTTP + OIDC)
resource "google_cloud_run_service_iam_member" "scheduler_invoker" {
   service  = "ingest-opensky-data" # nom de fonction ici
   location = var.gcp_region
   project  = var.gcp_project_id
   role     = "roles/run.invoker"
   # Le compte de service par défaut de Cloud Scheduler ou un compte dédié si créé
   member   = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-cloudscheduler.iam.gserviceaccount.com" # Compte de service par défaut de Scheduler
 }

 # Nécessaire pour obtenir le numéro du projet pour le compte de service Scheduler
 data "google_project" "project" {
   project_id = var.gcp_project_id
 }
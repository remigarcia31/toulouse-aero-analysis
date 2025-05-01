resource "google_pubsub_topic" "opensky_fetch_trigger" {
  project = var.gcp_project_id
  name    = "opensky-fetch-trigger" # Nom du topic
}


resource "google_pubsub_topic_iam_member" "scheduler_publishes" {
  project = google_pubsub_topic.opensky_fetch_trigger.project
  topic   = google_pubsub_topic.opensky_fetch_trigger.name
  role    = "roles/pubsub.publisher"
  # SA par défaut de Scheduler (utilisé lors de la création du job Pub/Sub)
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-cloudscheduler.iam.gserviceaccount.com"
}

# permission au compte de service de la Cloud Function de créer une souscription implicite (nécessaire pour le trigger)
resource "google_project_iam_member" "cf_subscriber" {
   project = var.gcp_project_id
   # Le rôle 'roles/pubsub.subscriber' est souvent suffisant, mais 'roles/pubsub.editor'
   # peut être nécessaire pour la création/gestion de la souscription par le trigger CF
   role    = "roles/pubsub.editor"
   member  = "serviceAccount:${google_service_account.ingest_function_sa.email}" 
   depends_on = [google_service_account.ingest_function_sa]
}
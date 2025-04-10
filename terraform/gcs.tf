# Bucket pour l'état Terraform (doit être unique globalement)
resource "google_storage_bucket" "terraform_state" {
  name          = var.gcs_terraform_state_bucket_name
  location      = var.gcp_region
  force_destroy = false # Sécurité : ne pas supprimer si non vide par défaut

  uniform_bucket_level_access = true # Recommandé

  versioning {
    enabled = true # Important pour l'historique de l'état TF
  }

  lifecycle {
    prevent_destroy = true # Sécurité additionnelle pour le bucket d'état
  }
}

# Bucket pour les données brutes (landing zone)
resource "google_storage_bucket" "landing_zone" {
  name          = var.gcs_landing_bucket_name
  location      = var.gcp_region
  force_destroy = false # Mettre à true SEULEMENT en dev/test si besoin

  uniform_bucket_level_access = true

  # On pourrait ajouter un cycle de vie ici plus tard (ex: supprimer après X jours)
  # lifecycle_rule { ... }
}

# Bucket pour les données traitées
resource "google_storage_bucket" "processed_data" {
  name          = var.gcs_processed_bucket_name
  location      = var.gcp_region
  force_destroy = false
  uniform_bucket_level_access = true
}

# Bucket pour les scripts Spark
resource "google_storage_bucket" "spark_scripts" {
  name          = var.gcs_spark_scripts_bucket_name
  location      = var.gcp_region
  force_destroy = false
  uniform_bucket_level_access = true
}
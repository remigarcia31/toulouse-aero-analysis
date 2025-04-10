variable "gcp_project_id" {
  description = "L'ID projet Google Cloud."
  type        = string
}

variable "gcp_region" {
  description = "La région GCP où déployer les ressources (ex: europe-west1)."
  type        = string
  default     = "europe-west9" 
}

variable "gcs_terraform_state_bucket_name" {
  description = "Nom unique du bucket GCS pour stocker l'état Terraform."
  type        = string
}

variable "gcs_landing_bucket_name" {
  description = "Nom unique du bucket GCS pour les données brutes ADS-B."
  type        = string
}

variable "gcs_processed_bucket_name" {
  description = "Nom unique du bucket GCS pour les données ADS-B traitées."
  type        = string
}

variable "gcs_spark_scripts_bucket_name" {
  description = "Nom unique du bucket GCS pour stocker les scripts PySpark."
  type        = string
}

variable "bq_dataset_name" {
  description = "Nom du dataset BigQuery pour les données aéronautiques."
  type        = string
  default     = "aeronautics_data"
}

variable "bq_location" {
  description = "Location pour le dataset BigQuery (ex: EU, US, europe-west9)."
  type        = string
  default     = "EU" # Multi-région EU
}
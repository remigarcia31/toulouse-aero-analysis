terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0" 
    }
  }

  # Configuration du Backend GCS (pour stocker l'état Terraform)
  backend "gcs" {
    bucket = "gcs_tf_state" 
    prefix = "terraform/state"
  }
}

# Configuration du provider Google Cloud
provider "google" {
  project = var.gcp_project_id # Récupère l'ID projet depuis les variables
  region  = var.gcp_region     # Récupère la région depuis les variables
  # Terraform utilisera les credentials trouvés par 'gcloud auth application-default login'
}
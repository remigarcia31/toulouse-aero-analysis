resource "google_bigquery_dataset" "aeronautics_data" {
  dataset_id                  = var.bq_dataset_name
  project                     = var.gcp_project_id
  location                    = var.bq_location
  description                 = "Dataset contenant les données traitées sur l'activité aérienne."
  delete_contents_on_destroy  = false # Sécurité : ne pas vider le dataset si on détruit la ressource TF
}

resource "google_bigquery_table" "flight_data_external" {
  project    = var.gcp_project_id
  dataset_id = google_bigquery_dataset.aeronautics_data.dataset_id
  table_id   = "flight_data_external" # Gardons le même nom pour l'instant

  external_data_configuration {
    source_format = "PARQUET"
    autodetect    = true # Laisser BigQuery détecter le schéma des fichiers Parquet

    # Pointer vers le dossier de base contenant les partitions year=...
    # Le '*' final est important pour que BQ explore les sous-dossiers
    source_uris = [
      "gs://clean_data_ads/processed_flight_data/*"
    ]

    # Configuration pour le partitionnement Hive
    hive_partitioning_options {
      # Mode "AUTO" : BQ détecte les clés (year, month, day, hour) et types depuis les chemins
      mode = "AUTO"
      # Préfixe URI : Chemin GCS *avant* la première clé de partition (year=)
      source_uri_prefix = "gs://clean_data_ads/processed_flight_data/"
    }
  }

  description = "Table externe pointant vers les données Parquet partitionnées (Hive-style) des vols ADS-B sur GCS."
  depends_on = [google_bigquery_dataset.aeronautics_data]
}
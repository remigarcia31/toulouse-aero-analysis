#!/bin/bash

# === Charger la configuration depuis .env (Méthode plus robuste) ===
if [ -f .env ]; then
  echo "Chargement de la configuration depuis .env..."
  # Exporte uniquement les lignes valides CLE=VALEUR (ignore commentaires/vides)
  set -o allexport # Active l'export auto des variables assignées
  source .env      # Lit le fichier .env
  set +o allexport # Désactive l'export auto
else
  echo "ATTENTION: Fichier .env non trouvé. Utilisation des valeurs par défaut ou arrêt si variable obligatoire manquante."
fi
# ==========================================

# === Configuration (Lues depuis l'environnement chargé ou valeurs par défaut) ===
PROJECT_ID="${GCP_PROJECT_ID:-toulouse-aero-analysis}"
REGION="${GCP_REGION:-europe-west1}"
CLUSTER_NAME="${DATAPROC_CLUSTER_NAME:-aero-cluster-test}"
LANDING_BUCKET_NAME="${LANDING_BUCKET_NAME:?Erreur: La variable LANDING_BUCKET_NAME doit être définie dans le fichier .env}"
SPARK_SCRIPTS_BUCKET_NAME="${SPARK_SCRIPTS_BUCKET_NAME:?Erreur: La variable SPARK_SCRIPTS_BUCKET_NAME doit être définie dans le fichier .env}"
PROCESSED_BUCKET_NAME="${PROCESSED_BUCKET_NAME:-clean_data_ads}"

# Dates/Heures à traiter (Plage)
START_DATE_STR="${START_DATE:?Erreur: La variable START_DATE (format AAAA-MM-JJ) doit être définie dans le fichier .env}"
END_DATE_STR="${END_DATE:?Erreur: La variable END_DATE (format AAAA-MM-JJ) doit être définie dans le fichier .env}"
START_HOUR="${START_HOUR:-0}"
END_HOUR="${END_HOUR:-23}"

# --- Variables dérivées ---
SCRIPT_GCS_PATH="gs://${SPARK_SCRIPTS_BUCKET_NAME}/process_adsb_data.py"
OUTPUT_GCS_BASE_PATH="gs://${PROCESSED_BUCKET_NAME}/processed_flight_data/"
# ============================================

echo "--- Démarrage du Backfill Spark ---"
echo "Projet: ${PROJECT_ID}"
echo "Région: ${REGION}"
echo "Cluster: ${CLUSTER_NAME}"
echo "Script Spark: ${SCRIPT_GCS_PATH}"
echo "Bucket Landing: ${LANDING_BUCKET_NAME}"
echo "Chemin de Sortie Base: ${OUTPUT_GCS_BASE_PATH}"
echo "Traitement pour la période: ${START_DATE_STR} à ${END_DATE_STR}, Heures: ${START_HOUR} à ${END_HOUR}"
echo "------------------------------------"

# Initialiser la date courante (syntaxe macOS)
current_date=$(date -j -f "%Y-%m-%d" "$START_DATE_STR" "+%Y-%m-%d")
# Calculer la date de fin + 1 jour pour la comparaison (syntaxe macOS)
end_date_plus_one=$(date -j -v+1d -f "%Y-%m-%d" "$END_DATE_STR" "+%Y-%m-%d")


# Boucle sur les jours
while [[ "$current_date" < "$end_date_plus_one" ]]; do

  # Extraire Année, Mois, Jour de la date courante (syntaxe macOS)
  YEAR=$(date -j -f "%Y-%m-%d" "$current_date" "+%Y")
  MONTH=$(date -j -f "%Y-%m-%d" "$current_date" "+%m")
  DAY=$(date -j -f "%Y-%m-%d" "$current_date" "+%d")

  echo ""
  echo "========= Traitement du Jour: ${YEAR}-${MONTH}-${DAY} ========="

  # Boucle sur les heures pour la journée courante
  for HOUR_INT in $(seq ${START_HOUR} ${END_HOUR}); do
    HOUR=$(printf "%02d" $HOUR_INT)
    INPUT_GCS_PATH="gs://${LANDING_BUCKET_NAME}/${YEAR}/${MONTH}/${DAY}/${HOUR}/"

    echo ""
    echo "--- Traitement pour ${YEAR}-${MONTH}-${DAY} Heure ${HOUR} ---"

    gsutil -q stat "${INPUT_GCS_PATH}*"
    if [ $? -eq 0 ]; then
      echo "Données trouvées dans ${INPUT_GCS_PATH}. Soumission du job..."
      gcloud dataproc jobs submit pyspark ${SCRIPT_GCS_PATH} \
          --project=${PROJECT_ID} \
          --region=${REGION} \
          --cluster=${CLUSTER_NAME} \
          -- \
          --input=${INPUT_GCS_PATH} \
          --output=${OUTPUT_GCS_BASE_PATH}

      if [ $? -ne 0 ]; then
          echo "ERREUR: La soumission du job pour l'heure ${HOUR} a échoué."
      else
          echo "Job pour l'heure ${HOUR} soumis avec succès."
      fi
      echo "Pause de 10 secondes..."
      sleep 10
    else
      echo "Pas de données trouvées dans ${INPUT_GCS_PATH}. Heure ${HOUR} sautée."
    fi
  done # Fin boucle heures

  # Passer au jour suivant (syntaxe macOS)
  current_date=$(date -j -v+1d -f "%Y-%m-%d" "$current_date" "+%Y-%m-%d")

done # Fin boucle jours

echo ""
echo "--- Backfill Terminé pour la période ${START_DATE_STR} à ${END_DATE_STR} ---"
echo " NE PAS OUBLIER : Vérifier les jobs dans Dataproc et de supprimer le cluster '${CLUSTER_NAME}'"
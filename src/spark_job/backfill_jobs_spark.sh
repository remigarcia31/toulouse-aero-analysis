#!/bin/bash

# === Charger la configuration depuis .env ===
if [ -f .env ]; then
  echo "Chargement de la configuration depuis .env..."
  # Exporte les variables du .env (ignore les commentaires '#', suppose format CLE=VALEUR simple)
  export $(grep -v '^#' .env | xargs)
else
  echo "ATTENTION: Fichier .env non trouvé. Utilisation des valeurs par défaut ou arrêt si variable obligatoire manquante."
fi
# ==========================================

# === Configuration (Lues depuis l'environnement chargé ou valeurs par défaut) ===
PROJECT_ID="${GCP_PROJECT_ID:-toulouse-aero-analysis}"
REGION="${GCP_REGION:-europe-west1}"
CLUSTER_NAME="${DATAPROC_CLUSTER_NAME:-aero-cluster-test}"
# Les noms de bucket sont obligatoires, arrêt si non définis dans .env
LANDING_BUCKET_NAME="${LANDING_BUCKET_NAME:?Erreur: La variable LANDING_BUCKET_NAME doit être définie dans le fichier .env}"
SPARK_SCRIPTS_BUCKET_NAME="${SPARK_SCRIPTS_BUCKET_NAME:?Erreur: La variable SPARK_SCRIPTS_BUCKET_NAME doit être définie dans le fichier .env}"
PROCESSED_BUCKET_NAME="${PROCESSED_BUCKET_NAME:-clean_data_ads}"

# Dates/Heures à traiter
YEAR="${BACKFILL_YEAR:-2025}"
MONTH="${BACKFILL_MONTH:-04}"
DAY="${BACKFILL_DAY:-11}"
START_HOUR="${BACKFILL_START_HOUR:-0}"
END_HOUR="${BACKFILL_END_HOUR:-23}"

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
echo "Traitement pour: ${YEAR}-${MONTH}-${DAY}, Heures: ${START_HOUR} à ${END_HOUR}"
echo "------------------------------------"

# Boucle sur les heures à traiter
for HOUR_INT in $(seq ${START_HOUR} ${END_HOUR}); do
  # Formater l'heure sur 2 chiffres (ex: 8 -> 08)
  HOUR=$(printf "%02d" $HOUR_INT)

  # Construire le chemin d'entrée GCS pour cette heure
  INPUT_GCS_PATH="gs://${LANDING_BUCKET_NAME}/${YEAR}/${MONTH}/${DAY}/${HOUR}/"

  echo "" # Saut de ligne pour la lisibilité
  echo "--- Traitement pour ${YEAR}-${MONTH}-${DAY} Heure ${HOUR} ---"

  # si le dossier d'entrée contient des données avant de soumettre
  # L'option -q supprime la sortie normale, on vérifie juste le code de retour ($?)
  # Le wildcard '*' à la fin est pour voir si *quelque chose* existe dans le dossier
  gsutil -q stat "${INPUT_GCS_PATH}*"
  if [ $? -eq 0 ]; then
    echo "Données trouvées dans ${INPUT_GCS_PATH}. Soumission du job..."

    # Soumettre le job Dataproc
    gcloud dataproc jobs submit pyspark ${SCRIPT_GCS_PATH} \
        --project=${PROJECT_ID} \
        --region=${REGION} \
        --cluster=${CLUSTER_NAME} \
        -- \
        --input=${INPUT_GCS_PATH} \
        --output=${OUTPUT_GCS_BASE_PATH}

    # Vérifier le code de retour de la soumission
    if [ $? -ne 0 ]; then
        echo "ERREUR: La soumission du job pour l'heure ${HOUR} a échoué."
        # exit 1 # pour arrêter en cas d'erreur de soumission
    else
        echo "Job pour l'heure ${HOUR} soumis avec succès."
    fi

    # Petite pause pour éviter de surcharger l'API Dataproc
    echo "Pause de 10 secondes..."
    sleep 10

  else
    echo "Pas de données trouvées dans ${INPUT_GCS_PATH}. Heure ${HOUR} sautée."
  fi

done

echo ""
echo "--- Backfill Terminé ---"
echo " NE PAS OUBLIER : Vérifier les jobs dans Dataproc et de supprimer le cluster '${CLUSTER_NAME}'"
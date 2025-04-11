import datetime
from airflow import DAG
# from airflow.providers.google.cloud.operators.dataproc import DataprocSubmitPySparkJobOperator
from airflow.providers.google.cloud.operators.dataproc import DataprocSubmitJobOperator
from airflow.utils.dates import days_ago
import pendulum # Pendulum est souvent pré-installé dans Composer et gère mieux les timezones

# Arguments communs pour les tâches
default_args = {
    'owner': 'airflow',
    'depends_on_past': False, # Ne dépend pas de l'exécution précédente
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1, # Nombre de tentatives en cas d'échec
    'retry_delay': datetime.timedelta(minutes=5), # Délai entre les tentatives
}

# --- Variables de Configuration ---
GCP_PROJECT_ID = "toulouse-aero-analysis"
# Région où tourne Dataproc ET Composer (doivent être compatibles)
GCP_REGION = "europe-west1"
# Nom du cluster Dataproc créé manuellement
DATAPROC_CLUSTER_NAME = "aero-cluster-test"
# Chemin GCS COMPLET vers le script PySpark
GCS_SPARK_SCRIPT_PATH = "gs://gcs_scripts_spark/process_adsb_data.py"
# Nom du bucket GCS contenant les données brutes
GCS_LANDING_BUCKET_NAME = "raw_data_ads"
# Chemin GCS de BASE où écrire les données traitées
GCS_PROCESSED_BASE_PATH = "gs://clean_data_ads/processed_flight_data/"
# --------------------------------------------------------------

# Définition du DAG
# Utilisation de pendulum pour une gestion plus robuste des fuseaux horaires
with DAG(
    dag_id='aero_data_processing_pipeline',
    default_args=default_args,
    description='Pipeline pour traiter les données ADS-B depuis GCS avec Spark sur Dataproc',
    # Déclencher toutes les heures, 15 minutes après l'heure pleine (ex: 01:15, 02:15...)
    schedule_interval='15 * * * *',
    # Date de début : hier (pour permettre un déclenchement rapide si besoin)
    start_date=pendulum.datetime(2025, 4, 10, tz="Europe/Paris"), # Ajuster la date si besoin
    catchup=False, # Important: Ne pas essayer de rattraper les exécutions passées au premier déploiement
    tags=['aeronautics', 'dataproc', 'gcp'],
) as dag:

    # Construction dynamique du chemin d'entrée basé sur l'heure PRECEDENTE l'exécution logique
    # execution_date est le début de l'intervalle. Si le DAG tourne à 10:15, execution_date = 10:00.
    # On veut traiter les données de 09:00, donc on fait execution_date - 1 heure.
    # Le format YYYY/MM/DD/HH est attendu par notre structure de bucket landing.
    gcs_input_path = (
        f"gs://{GCS_LANDING_BUCKET_NAME}/"
        "{{ (execution_date - macros.timedelta(hours=1)).strftime('%Y/%m/%d/%H') }}/"
    )

    # Définir la configuration spécifique pour un job PySpark
    pyspark_job_config = {
        "main_python_file_uri": GCS_SPARK_SCRIPT_PATH,
        "args": [
            f"--input={gcs_input_path}",
            f"--output={GCS_PROCESSED_BASE_PATH}"
        ]
    }

    # Tâche pour soumettre le job
    submit_spark_job = DataprocSubmitJobOperator(
        task_id='submit_process_adsb_spark_job',
        project_id=GCP_PROJECT_ID,
        region=GCP_REGION,
        # configuration spécifique du job PySpark
        job={
            # "reference": {"job_id": f"aero_process_{{{{ ds_nodash }}}}_{{{{ ti.try_number }}}}"}, # Nom de job unique
            "placement": {"cluster_name": DATAPROC_CLUSTER_NAME}, # Confirmer le cluster cible
            "pyspark_job": pyspark_job_config # Passer la config
        }
    )
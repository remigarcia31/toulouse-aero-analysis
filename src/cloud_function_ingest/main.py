import json
import logging
import os
from datetime import datetime

import requests
from google.cloud import storage

# Configuration du logging
logging.basicConfig(level=logging.INFO)

# Initialiser le client GCS
# storage_client = storage.Client()


def fetch_and_store_opensky_data(request):
    """
    Point d'entrée de la Cloud Function. Récupère les données d'OpenSky
    et les stocke dans GCS.
    """
    # === LIRE LES VARIABLES D'ENVIRONNEMENT ===
    try:
        gcs_bucket_name = os.environ["GCS_BUCKET_NAME"]
        lat_min = os.environ.get("LAT_MIN", "43.4")
        lon_min = os.environ.get("LON_MIN", "1.2")
        lat_max = os.environ.get("LAT_MAX", "43.8")
        lon_max = os.environ.get("LON_MAX", "1.7")
    except KeyError as e:
        # Logguer l'erreur et probablement retourner une erreur 500 car la fonction ne peut pas tourner
        logging.error(f"Configuration Error: Missing environment variable: {e}")
        return "Internal Server Error: Missing configuration", 500
    # =============================================

    opensky_api_url = f"https://opensky-network.org/api/states/all?lamin={lat_min}&lomin={lon_min}&lamax={lat_max}&lomax={lon_max}"

    logging.info(
        f"Fetching data for bucket {gcs_bucket_name}..."
    )  # Log pour confirmer la lecture

    try:
        # 1. Récupérer les données depuis OpenSky API
        response = requests.get(opensky_api_url, timeout=20)  # Timeout de 20 secondes
        response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP (4xx ou 5xx)
        logging.info(f"Réponse API reçue (status: {response.status_code})")

        # Vérifier si la réponse contient des données exploitables
        try:
            data = response.json()
            if data is None or "states" not in data:
                logging.warning(
                    "Réponse JSON vide ou sans champ 'states'. Aucune donnée à traiter."
                )
                # On peut choisir de retourner ici ou de quand même stocker le JSON vide.
                # Stockons le quand même pour tracer les appels API réussis mais vides.
                raw_data = response.text  # Utiliser .text pour stocker le JSON brut
            else:
                # vérifier si states est None ou vide
                if data["states"] is None or not data["states"]:
                    logging.info(
                        "Champ 'states' est vide ou null. Aucun avion détecté dans la zone."
                    )
                else:
                    logging.info(f"{len(data['states'])} états d'avions reçus.")
                raw_data = (
                    response.text
                )  # Utiliser .text pour garantir stockage du JSON brut

        except json.JSONDecodeError:
            logging.error("Impossible de décoder la réponse JSON de l'API.")
            raw_data = response.text  # Stocker la réponse brute même si non JSON valide
            # Optionnellement, on pourrait décider de ne pas stocker si ce n'est pas du JSON.

        storage_client = storage.Client()

        # 2. Préparer le stockage dans GCS
        now = datetime.utcnow()
        # Créer un chemin de fichier partitionné par année/mois/jour/heure
        gcs_file_path = (
            f"{now.strftime('%Y/%m/%d/%H')}/states_{now.strftime('%Y%m%d_%H%M%S')}.json"
        )

        # Récupérer le bucket GCS
        bucket = storage_client.bucket(gcs_bucket_name)
        # Créer un "blob" (objet) dans le bucket
        blob = bucket.blob(gcs_file_path)

        # 3. Uploader les données brutes dans GCS
        blob.upload_from_string(data=raw_data, content_type="application/json")
        logging.info(
            f"Données brutes OpenSky stockées dans : gs://{gcs_bucket_name}/{gcs_file_path}"
        )

        return "Ingestion réussie.", 200

    except requests.exceptions.RequestException as e:
        logging.error(f"Erreur lors de l'appel à l'API OpenSky: {e}")
        # On pourrait vouloir lever l'exception pour que Cloud Functions la marque comme échouée
        # raise e # Ou juste retourner une erreur HTTP si déclenchée par HTTP
        return f"Erreur API: {e}", 500
    except Exception as e:
        # Utiliser la variable locale ici aussi
        logging.error(
            f"Unexpected error during execution for bucket {gcs_bucket_name if 'gcs_bucket_name' in locals() else 'UNKNOWN'}: {e}"
        )
        return f"Internal Error: {e}", 500


# --- Section pour test local (optionnel) ---
# if __name__ == '__main__':
#     # Pour tester localement, définissez les variables d'environnement
#     # export GCS_BUCKET_NAME='votre-bucket-landing'
#     # export GOOGLE_APPLICATION_CREDENTIALS='/chemin/vers/votre/keyfile.json' # Si nécessaire
#     print("Test local de la fonction...")
#     event_mock = {}
#     context_mock = None
#     fetch_and_store_opensky_data(event_mock, context_mock)

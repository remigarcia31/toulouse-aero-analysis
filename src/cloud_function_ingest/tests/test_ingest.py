import json
import os
from unittest import mock

from freezegun import freeze_time

# la fonction à tester
from src.cloud_function_ingest.main import fetch_and_store_opensky_data

# --- Tests ---


# Utiliser patch pour remplacer les appels externes
@mock.patch("src.cloud_function_ingest.main.storage.Client")  # Mock le client GCS
@mock.patch("src.cloud_function_ingest.main.requests.get")  # Mock requests.get
@mock.patch.dict(
    os.environ,
    {  # Définir les variables d'environnement pour le test
        "GCS_BUCKET_NAME": "test-bucket-landing",
        "LAT_MIN": "40.0",
        "LON_MIN": "1.0",
        "LAT_MAX": "41.0",
        "LON_MAX": "2.0",
    },
)
# Figer le temps pour que le chemin GCS soit prédictible
@freeze_time("2025-04-14 10:30:00 UTC")
def test_successful_ingestion(mock_requests_get, mock_storage_client):
    """
    Teste le chemin d'exécution nominal : API OK -> GCS Upload OK.
    """
    # --- Configuration des Mocks ---

    # 1. Configurer le mock pour requests.get
    mock_response = mock.Mock()
    mock_response.status_code = 200
    # Simuler une réponse JSON valide de l'API OpenSky
    mock_api_data = {
        "time": 1744597800,
        "states": [
            [
                "123456",
                "TST1",
                "Testland",
                None,
                1744597800,
                1.5,
                40.5,
                5000.0,
                False,
                100.0,
                90.0,
                0.0,
                None,
                5000.0,
                "1000",
                False,
                0,
            ]
        ],
    }
    mock_response.json.return_value = mock_api_data
    mock_response.text = json.dumps(mock_api_data)  # Le .text doit correspondre au JSON
    mock_requests_get.return_value = mock_response

    # 2. Configurer la chaîne de mocks pour google.cloud.storage
    # On a besoin de mocker client -> bucket -> blob -> upload_from_string
    mock_blob = mock.Mock()
    mock_bucket = mock.Mock()
    mock_bucket.blob.return_value = mock_blob
    # L'instance du client retournera notre mock_bucket
    mock_storage_client.return_value.bucket.return_value = mock_bucket

    # Assigner un mock à la méthode upload_from_string pour qu'elle ne fasse rien
    mock_blob.upload_from_string = mock.Mock()

    # --- Appel de la Fonction Testée ---
    # La fonction HTTP attend un objet 'request', même si on ne l'utilise pas.
    # On peut passer un simple mock ou None si la fonction le gère.
    mock_flask_request = mock.Mock()
    result, status_code = fetch_and_store_opensky_data(mock_flask_request)

    # --- Assertions ---

    # 1. Vérifier l'appel à requests.get
    expected_api_url = "https://opensky-network.org/api/states/all?lamin=40.0&lomin=1.0&lamax=41.0&lomax=2.0"
    mock_requests_get.assert_called_once_with(expected_api_url, timeout=20)

    # 2. Vérifier l'appel à GCS (chemin et contenu)
    # Le chemin doit être basé sur le temps figé ("2025-04-14 10:30:00 UTC")
    expected_gcs_path = "2025/04/14/10/states_20250414_103000.json"
    # Vérifier que client().bucket('test-bucket-landing') a été appelé
    mock_storage_client.return_value.bucket.assert_called_once_with(
        "test-bucket-landing"
    )
    # Vérifier que bucket.blob(...) a été appelé avec le bon chemin
    mock_bucket.blob.assert_called_once_with(expected_gcs_path)
    # Vérifier que blob.upload_from_string(...) a été appelé avec les bonnes données
    mock_blob.upload_from_string.assert_called_once_with(
        data=json.dumps(mock_api_data), content_type="application/json"
    )

    # 3. Vérifier le résultat de la fonction
    assert status_code == 200
    assert result == "Ingestion réussie."

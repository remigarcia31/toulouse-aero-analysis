import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    """Fixture pour créer une SparkSession locale pour les tests."""
    print("----> Création de la SparkSession pour les tests...")
    session = (
        SparkSession.builder.master("local[1]")
        .appName("PySparkTestSession")
        .config("spark.sql.session.timeZone", "UTC")  # Force la session en UTC
        # ===========================
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    session.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

    yield session

    print("----> Arrêt de la SparkSession de test...")
    session.stop()

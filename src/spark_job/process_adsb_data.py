import argparse
import logging

from pyspark.sql import SparkSession
# Importer les fonctions et types nécessaires
from pyspark.sql.functions import col, explode, from_unixtime, year, month, dayofmonth, hour
from pyspark.sql.types import (
    ArrayType,
    BooleanType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Schéma explicite pour les fichiers JSON bruts lus depuis GCS
# On s'attend à un champ 'time' (long) et 'states' (array d'array de string nullable)
expected_raw_schema = StructType([
    StructField("time", LongType(), True),
    StructField("states", ArrayType(ArrayType(StringType(), True), True), True) # Défini comme Array, nullable
])


# Définir le schéma attendu pour les données 'states' (pour l'étape d'extraction par index)
# Cette partie n'est pas utilisée directement pour la lecture initiale, mais pour la logique métier ensuite.
opensky_state_schema_list = [
    ("icao24", StringType(), True),
    ("callsign", StringType(), True),
    ("origin_country", StringType(), True),
    ("time_position", LongType(), True),
    ("last_contact", LongType(), True),
    ("longitude", DoubleType(), True),
    ("latitude", DoubleType(), True),
    ("baro_altitude", DoubleType(), True),
    ("on_ground", BooleanType(), True),
    ("velocity", DoubleType(), True),
    ("true_track", DoubleType(), True),
    ("vertical_rate", DoubleType(), True),
    # ("sensors", ArrayType(IntegerType(), True), True), # On ignore sensors
    ("geo_altitude", DoubleType(), True), # Index 13
    ("squawk", StringType(), True), # Index 14
    ("spi", BooleanType(), True), # Index 15
    ("position_source", IntegerType(), True) # Index 16
]


def process_data(spark, input_path, output_path):
    """
    Fonction principale du job Spark.
    Lit les JSON bruts depuis input_path, les transforme, et écrit en Parquet dans output_path.
    """
    logging.info("Démarrage du traitement Spark...")
    logging.info(f"Lecture depuis : {input_path}")
    logging.info(f"Écriture vers : {output_path}")

    # === Étape 1: Lecture des fichiers JSON (AVEC SCHÉMA EXPLICITE) ===
    try:
        logging.info(f"Lecture JSON avec schéma explicite depuis {input_path}")
        raw_df = spark.read \
            .schema(expected_raw_schema) \
            .option("multiLine", "true") \
            .json(input_path)

        logging.info("Schéma après lecture avec schéma explicite:")
        raw_df.printSchema()

        # Vérification post-lecture (bonne pratique)
        if 'states' not in raw_df.columns or not isinstance(raw_df.schema['states'].dataType, ArrayType):
             logging.error(f"La colonne 'states' est manquante ou n'a pas le type Array attendu après lecture ! Vérifiez schéma/données.")
             raise TypeError("La colonne 'states' n'a pas le type Array attendu après lecture.")
        if 'time' not in raw_df.columns:
             raise ValueError("Colonne 'time' manquante après lecture.")

    except Exception as e:
        # Si la lecture échoue même avec schéma (ex: JSON très corrompu), on loggue et arrête.
        logging.error(f"Erreur lors de la lecture JSON (même avec schéma) depuis {input_path}: {e}")
        raise e # Relance l'exception pour faire échouer le job Dataproc

    # === Filtrage des lignes où 'states' est null ===
    logging.info("Filtrage des lignes où 'states' est null...")
    filtered_df = raw_df.filter(col("states").isNotNull())
    # ----------------------------------------------------------

    # === Vérification si des données restent après filtrage === 
    count_after_filter = filtered_df.count()
    if count_after_filter == 0:
        logging.warning(f"Aucune ligne avec des données 'states' valides (non null) trouvée dans {input_path}. Arrêt du traitement pour cette période.")
        return # Quitte la fonction proprement, le job Spark sera marqué comme SUCCEEDED mais n'écrira rien.
    # --------------------------------------------------------------------

    logging.info(f"Nombre de lignes après filtrage: {count_after_filter}")

    # === Étape 2: Transformation Initiale - Explode (sur le DF filtré) ===
    logging.info("Explosion de la colonne 'states'...")
    exploded_df = filtered_df.select(
        col("time").alias("fetch_timestamp_unix"),
        explode(col("states")).alias("state_info") # Ne recevra plus de null ici
    )

    logging.info("Schéma après explosion de la colonne 'states':")
    exploded_df.printSchema()
    logging.info("Exemple de données après explosion:")
    exploded_df.show(5, truncate=False)


    # === Étape 2b: Extraction et Typage des Champs ===
    logging.info("Extraction et typage des champs depuis 'state_info'...")
    processed_df = exploded_df.select(
        from_unixtime(col("fetch_timestamp_unix")).cast(TimestampType()).alias("fetch_time"),
        col("state_info")[0].cast(StringType()).alias("icao24"),
        col("state_info")[1].cast(StringType()).alias("callsign"),
        col("state_info")[2].cast(StringType()).alias("origin_country"),
        from_unixtime(col("state_info")[3].cast(LongType())).cast(TimestampType()).alias("time_position"),
        from_unixtime(col("state_info")[4].cast(LongType())).cast(TimestampType()).alias("last_contact"),
        col("state_info")[5].cast(DoubleType()).alias("longitude"),
        col("state_info")[6].cast(DoubleType()).alias("latitude"),
        col("state_info")[7].cast(DoubleType()).alias("baro_altitude"),
        col("state_info")[8].cast(BooleanType()).alias("on_ground"),
        col("state_info")[9].cast(DoubleType()).alias("velocity"),
        col("state_info")[10].cast(DoubleType()).alias("true_track"),
        col("state_info")[11].cast(DoubleType()).alias("vertical_rate"),
        col("state_info")[13].cast(DoubleType()).alias("geo_altitude"), # Index 13
        col("state_info")[14].cast(StringType()).alias("squawk"), # Index 14
        col("state_info")[15].cast(BooleanType()).alias("spi"), # Index 15
        col("state_info")[16].cast(IntegerType()).alias("position_source") # Index 16
    )

    logging.info("Schéma final après transformation:")
    processed_df.printSchema()
    logging.info("Exemple de données transformées:")
    processed_df.show(10, truncate=False)

    # === Étape 2c: Ajout des Colonnes de Partition ===
    logging.info(
        "Ajout des colonnes de partition (year, month, day, hour) basées sur fetch_time..."
    )
    processed_df_with_partitions = (
        processed_df.withColumn("year", year(col("fetch_time")))
        .withColumn("month", month(col("fetch_time")))
        .withColumn("day", dayofmonth(col("fetch_time")))
        .withColumn("hour", hour(col("fetch_time")))
    )

    logging.info("Schéma après ajout des colonnes de partition:")
    processed_df_with_partitions.printSchema()

    # === Étape 3: Écriture en Parquet Partitionné ===
    partition_columns = ["year", "month", "day", "hour"]
    logging.info(
        f"Écriture des données traitées au format Parquet vers {output_path}, partitionné par {partition_columns}..."
    )
    try:
        # Le mode overwrite avec partitionOverwriteMode=dynamic est configuré dans le __main__
        processed_df_with_partitions.write \
            .partitionBy(*partition_columns) \
            .mode("overwrite") \
            .parquet(output_path)

        logging.info("Écriture Parquet partitionnée terminée avec succès.")
    except Exception as e:
        logging.error(f"Erreur lors de l'écriture Parquet vers {output_path}: {e}")
        raise e


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        required=True,
        help="Chemin GCS vers les données JSON brutes (ex: gs://bucket/landing/YYYY/MM/DD/HH/)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Chemin GCS de BASE où écrire les données Parquet partitionnées (ex: gs://bucket/processed/base_path/)",
    )
    args = parser.parse_args()

    spark = SparkSession.builder.appName("OpenSky ADSB Data Processing").getOrCreate()

    # Activer l'écrasement dynamique des partitions
    spark.conf.set("spark.sql.sources.partitionOverwriteMode","dynamic")

    # Appeler la fonction de traitement
    process_data(spark, args.input, args.output)

    spark.stop()
    logging.info("Session Spark arrêtée.")
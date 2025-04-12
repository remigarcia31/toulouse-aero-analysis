import argparse
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_unixtime, to_timestamp, lit
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, DoubleType,
    BooleanType, IntegerType, TimestampType, ArrayType
)
import logging
from pyspark.sql.functions import year, month, dayofmonth, hour


# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Définir le schéma attendu pour les données 'states' DANS le JSON brut
# C'est une liste de listes, donc on définit le type pour chaque élément de la sous-liste
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
    ("sensors", ArrayType(IntegerType(), True), True), # Liste d'entiers pour sensors
    ("geo_altitude", DoubleType(), True),
    ("squawk", StringType(), True),
    ("spi", BooleanType(), True),
    ("position_source", IntegerType(), True)
]

# Créer le StructType pour une ligne/état d'avion
flight_state_struct = StructType([StructField(name, dtype, nullable) for name, dtype, nullable in opensky_state_schema_list])

# Schéma global du fichier JSON lu (approximatif, peut-être devoir l'ajuster)
# On s'attend à 'time' et 'states' (une liste de notre structure ci-dessus)
# Note : Lire directement un JSON multilignes complexe avec un schéma défini peut être délicat.
# On va probablement devoir lire le JSON brut puis l'exploser/parser.

def process_data(spark, input_path, output_path):
    """
    Fonction principale du job Spark.
    Lit les JSON bruts depuis input_path, les transforme, et écrit en Parquet dans output_path.
    """
    logging.info(f"Démarrage du traitement Spark...")
    logging.info(f"Lecture depuis : {input_path}")
    logging.info(f"Écriture vers : {output_path}")

    # === Étape 1: Lecture des fichiers JSON ===
    # Lire tous les fichiers JSON du chemin d'entrée.
    # 'multiLine=True' car chaque fichier JSON peut s'étendre sur plusieurs lignes.
    # Spark essaiera d'inférer le schéma, mais c'est souvent là que ça coince avec des structures complexes.
    try:
        # Lire en inférant le schéma. 'multiLine=True' est crucial.
        raw_df = spark.read.option("multiLine", "true").json(input_path)
        logging.info("Schéma inféré par Spark pour les JSON bruts:")
        raw_df.printSchema()
        # raw_df.show(1, truncate=False) # Décommenter pour voir un exemple de ligne brute

        # Vérification essentielle: les colonnes attendues sont-elles là?
        if 'states' not in raw_df.columns or 'time' not in raw_df.columns:
            logging.error("Colonnes 'states' ou 'time' manquantes dans le JSON lu. Vérifiez le format des fichiers d'entrée.")
            logging.error(f"Colonnes trouvées: {raw_df.columns}")
            raise ValueError("Schéma JSON d'entrée inattendu.")

    except Exception as e:
        logging.error(f"Erreur lors de la lecture JSON depuis {input_path}: {e}")
        raise e

    # === Étape 2: Transformation et Nettoyage ===
    # À ce stade, raw_df contient probablement des colonnes comme 'time', 'states'.
    # La colonne 'states' est une LISTE de structures (ou de listes).
    # Il faut "exploser" cette liste pour avoir une ligne par état d'avion.
    from pyspark.sql.functions import explode, col, from_unixtime

    logging.info("Explosion de la colonne 'states'...")
    # Sélectionner 'time' (sera notre fetch_time) et exploser 'states'
    # explode_outer est plus sûr si 'states' peut être null ou vide
    exploded_df = raw_df.select(
        col("time").alias("fetch_timestamp_unix"),
        explode(col("states")).alias("state_info")
        # Utiliser explode_outer(col("states")) si la colonne states peut être absente ou nulle dans certains JSON
    )

    logging.info("Schéma après explosion de la colonne 'states':")
    exploded_df.printSchema() # Très important pour voir le type de 'state_info'
    logging.info("Exemple de données après explosion:")
    exploded_df.show(5, truncate=False) # Important pour voir le contenu de 'state_info'

    # TODO:
    # 1. Sélectionner les colonnes 'time' (fetch_time) et 'states'.
    # 2. Utiliser la fonction `explode` sur la colonne 'states' pour créer une ligne par état.
    # 3. Accéder aux éléments de la structure/liste 'state' résultante pour créer les colonnes finales.
    #    Si 'state' est une liste : state[0] as icao24, state[1] as callsign, ...
    #    Si 'state' est une struct : state.icao24, state.callsign, ...
    # 4. Convertir les timestamps Unix (time_position, last_contact) en TimestampType.
    # 5. Sélectionner et renommer les colonnes selon notre schéma cible.
    # 6. Ajouter la colonne fetch_time (convertie depuis 'time').
    # 7. Gérer les valeurs nulles si nécessaire (ex: remplir avec des valeurs par défaut ?).

    # === Étape 2b: Extraction et Typage des Champs ===
    from pyspark.sql.functions import from_unixtime, to_timestamp, col
    from pyspark.sql.types import ( StringType, LongType, DoubleType, BooleanType,
                                   IntegerType, TimestampType ) # Assurez-vous d'importer TimestampType

    logging.info("Extraction et typage des champs depuis 'state_info'...")

    # Rappel des index OpenSky:
    # 0:icao24, 1:callsign, 2:origin_country, 3:time_position, 4:last_contact,
    # 5:longitude, 6:latitude, 7:baro_altitude, 8:on_ground, 9:velocity,
    # 10:true_track, 11:vertical_rate, 13:geo_altitude, 14:squawk, 15:spi, 16:position_source
    # On ignore l'index 12 (sensors)

    processed_df = exploded_df.select(
        # Convertir fetch_timestamp_unix en TimestampType
        from_unixtime(col("fetch_timestamp_unix")).cast(TimestampType()).alias("fetch_time"),

        # Extraire chaque élément de la liste state_info par son index,
        # caster vers le bon type, et lui donner un nom de colonne (alias)
        col("state_info")[0].cast(StringType()).alias("icao24"),
        col("state_info")[1].cast(StringType()).alias("callsign"),
        col("state_info")[2].cast(StringType()).alias("origin_country"),
        # Pour les timestamps, caster en Long puis convertir depuis les secondes Unix
        from_unixtime(col("state_info")[3].cast(LongType())).cast(TimestampType()).alias("time_position"),
        from_unixtime(col("state_info")[4].cast(LongType())).cast(TimestampType()).alias("last_contact"),
        col("state_info")[5].cast(DoubleType()).alias("longitude"),
        col("state_info")[6].cast(DoubleType()).alias("latitude"),
        col("state_info")[7].cast(DoubleType()).alias("baro_altitude"),
        col("state_info")[8].cast(BooleanType()).alias("on_ground"),
        col("state_info")[9].cast(DoubleType()).alias("velocity"),
        col("state_info")[10].cast(DoubleType()).alias("true_track"),
        col("state_info")[11].cast(DoubleType()).alias("vertical_rate"),
        # Index 12 (sensors) est sauté
        col("state_info")[13].cast(DoubleType()).alias("geo_altitude"),
        col("state_info")[14].cast(StringType()).alias("squawk"),
        col("state_info")[15].cast(BooleanType()).alias("spi"),
        col("state_info")[16].cast(IntegerType()).alias("position_source")
    )

    logging.info("Schéma final après transformation:")
    processed_df.printSchema()
    logging.info("Exemple de données transformées:")
    processed_df.show(10, truncate=False) # Afficher plus de lignes pour vérifier

    # === Étape 2c: Ajout des Colonnes de Partition ===
    logging.info("Ajout des colonnes de partition (year, month, day, hour) basées sur fetch_time...")
    processed_df_with_partitions = processed_df.withColumn("year", year(col("fetch_time"))) \
                                             .withColumn("month", month(col("fetch_time"))) \
                                             .withColumn("day", dayofmonth(col("fetch_time"))) \
                                             .withColumn("hour", hour(col("fetch_time")))

    logging.info("Schéma après ajout des colonnes de partition:")
    processed_df_with_partitions.printSchema()
    # processed_df_with_partitions.show(5, truncate=False) # Décommenter pour vérifier

    # === Étape 3: Écriture en Parquet ===
    partition_columns = ["year", "month", "day", "hour"]
    # Le output_path est maintenant le chemin de base où les dossiers de partition seront créés
    logging.info(f"Écriture des données traitées au format Parquet vers {output_path}, partitionné par {partition_columns}...")
    try:
        # Écrire en écrasant la partition correspondante si elle existe déjà.
        # Pour un traitement fiable, on utilise souvent "append" et on s'assure
        # de ne traiter chaque période qu'une seule fois (géré par l'orchestrateur).
        # Pour les tests, "overwrite" est ok, mais il effacera les données précédentes
        # DANS les partitions concernées par ce batch.
        # Attention: Le mode "overwrite" simple peut supprimer TOUT le dossier de base.
        # Pour écraser dynamiquement seulement les partitions traitées:
        # spark.conf.set("spark.sql.sources.partitionOverwriteMode","dynamic") # A ajouter avant l'écriture si besoin
        # Simplifions pour l'instant : Assurez-vous que l'input correspond bien à ce que vous voulez écraser/écrire.
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
        '--input', required=True, help="Chemin GCS vers les données JSON brutes (ex: gs://bucket/landing/YYYY/MM/DD/HH/)"
    )
    parser.add_argument(
        '--output', required=True, help="Chemin GCS où écrire les données Parquet traitées (ex: gs://bucket/processed/YYYY/MM/DD/HH/)"
    )
    args = parser.parse_args()

    # Initialisation de la Spark Session (pour exécution locale ou sur Dataproc)
    spark = SparkSession.builder.appName("OpenSky ADSB Data Processing").getOrCreate()

    # Configuration pour lire/écrire sur GCS (peut nécessiter ajustements locaux)
    # spark.conf.set("google.cloud.auth.service.account.enable", "true")
    # spark.conf.set("google.cloud.auth.service.account.json.keyfile", "/path/to/your/keyfile.json") # Si ADC ne marche pas localement

    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

    # Appeler la fonction de traitement
    process_data(spark, args.input, args.output)

    # Arrêter la session Spark
    spark.stop()
    logging.info("Session Spark arrêtée.")
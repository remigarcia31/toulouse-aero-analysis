from datetime import datetime, timezone

import chispa
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    dayofmonth,
    explode,
    from_unixtime,
    hour,
    month,
    year,
)
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

# Importer la logique à tester ou le schéma brut si nécessaire
# from src.spark_job.process_adsb_data import expected_raw_schema # Importer si défini globalement
# Schéma explicite pour les fichiers JSON bruts lus depuis GCS
expected_raw_schema = StructType(
    [
        StructField("time", LongType(), True),
        StructField("states", ArrayType(ArrayType(StringType(), True), True), True),
    ]
)


def test_data_transformation(spark: SparkSession):
    """
    Teste la transformation complète des données avec un exemple simple
    en utilisant chispa pour la comparaison.
    """
    # 1. Données d'Entrée (simule ce qu'on obtient après lecture JSON)
    input_data = [
        # Avion 1: En vol | Avion 2: Au sol, altitude/vitesse nulles
        (
            1700000000,
            [
                [
                    "4b1800",
                    "TESTFL",
                    "France",
                    1700000000,
                    1700000000,
                    1.5,
                    43.5,
                    10000.0,
                    False,
                    200.0,
                    90.0,
                    0.0,
                    None,
                    10100.0,
                    "1234",
                    False,
                    0,
                ],
                [
                    "4b1801",
                    "TESTGND",
                    "Spain",
                    1699999995,
                    1700000000,
                    2.5,
                    44.5,
                    None,
                    True,
                    5.0,
                    180.0,
                    None,
                    None,
                    None,
                    "7700",
                    False,
                    0,
                ],
            ],
        )
    ]
    input_df = spark.createDataFrame(input_data, schema=expected_raw_schema)

    # 2. Appliquer la Logique de Transformation (copiée/adaptée du script principal)
    exploded_df = input_df.select(
        col("time").alias("fetch_timestamp_unix"),
        explode(col("states")).alias("state_info"),
    )

    processed_df = exploded_df.select(
        from_unixtime(col("fetch_timestamp_unix"))
        .cast(TimestampType())
        .alias("fetch_time"),
        col("state_info")[0].cast(StringType()).alias("icao24"),
        col("state_info")[1].cast(StringType()).alias("callsign"),
        col("state_info")[2].cast(StringType()).alias("origin_country"),
        from_unixtime(col("state_info")[3].cast(LongType()))
        .cast(TimestampType())
        .alias("time_position"),
        from_unixtime(col("state_info")[4].cast(LongType()))
        .cast(TimestampType())
        .alias("last_contact"),
        col("state_info")[5].cast(DoubleType()).alias("longitude"),
        col("state_info")[6].cast(DoubleType()).alias("latitude"),
        col("state_info")[7].cast(DoubleType()).alias("baro_altitude"),
        col("state_info")[8].cast(BooleanType()).alias("on_ground"),
        col("state_info")[9].cast(DoubleType()).alias("velocity"),
        col("state_info")[10].cast(DoubleType()).alias("true_track"),
        col("state_info")[11].cast(DoubleType()).alias("vertical_rate"),
        col("state_info")[13].cast(DoubleType()).alias("geo_altitude"),
        col("state_info")[14].cast(StringType()).alias("squawk"),
        col("state_info")[15].cast(BooleanType()).alias("spi"),
        col("state_info")[16].cast(IntegerType()).alias("position_source"),
    )

    actual_df = (
        processed_df.withColumn("year", year(col("fetch_time")))
        .withColumn("month", month(col("fetch_time")))
        .withColumn("day", dayofmonth(col("fetch_time")))
        .withColumn("hour", hour(col("fetch_time")))
    )

    # 3. Définir le DataFrame Attendu en Sortie AVEC Timezone UTC
    expected_data = [
        (
            datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc),  # UTC
            "4b1800",
            "TESTFL",
            "France",
            datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc),  # UTC
            datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc),  # UTC
            1.5,
            43.5,
            10000.0,
            False,
            200.0,
            90.0,
            0.0,
            10100.0,
            "1234",
            False,
            0,
            2023,
            11,
            14,
            22,
        ),
        (
            datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc),  # UTC
            "4b1801",
            "TESTGND",
            "Spain",
            datetime(2023, 11, 14, 22, 13, 15, tzinfo=timezone.utc),  # UTC
            datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc),  # UTC
            2.5,
            44.5,
            None,
            True,
            5.0,
            180.0,
            None,
            None,
            "7700",
            False,
            0,
            2023,
            11,
            14,
            22,
        ),
    ]

    expected_df = spark.createDataFrame(expected_data, schema=actual_df.schema)

    # 4. Assertion avec Chispa
    chispa.assert_df_equality(
        actual_df, expected_df, ignore_row_order=True, ignore_nullable=True
    )

    print("----> Test data_transformation passed!")

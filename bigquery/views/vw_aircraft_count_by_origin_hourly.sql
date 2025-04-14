
CREATE OR REPLACE VIEW `toulouse-aero-analysis.aeronautics_data.vw_aircraft_count_by_origin_hourly`
OPTIONS(
  description="Nombre d'avions uniques par pays d'origine et par heure (basé sur fetch_time)."
)
AS (
  SELECT
    year,
    month,
    day,
    hour,
    -- Colonne d'agrégation
    origin_country,
    -- Calcul
    COUNT(DISTINCT icao24) AS nombre_avions_uniques
  FROM
    `toulouse-aero-analysis.aeronautics_data.flight_data_external`
  WHERE
    origin_country IS NOT NULL AND origin_country != '' -- Nettoyage de base
  GROUP BY
    -- Grouper par les partitions ET le pays
    year, month, day, hour, origin_country
)
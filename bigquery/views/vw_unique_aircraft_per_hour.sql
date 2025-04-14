CREATE OR REPLACE VIEW `toulouse-aero-analysis.aeronautics_data.vw_unique_aircraft_per_hour`
OPTIONS(
  description="Vue calculant le nombre d'avions uniques détectés par heure, incluant les colonnes de partition."
)
AS (
  SELECT
    TIMESTAMP_TRUNC(fetch_time, HOUR) AS heure,
    year,
    month,
    day,
    hour,
    COUNT(DISTINCT icao24) AS nombre_avions_uniques
  FROM
    `toulouse-aero-analysis.aeronautics_data.flight_data_external`
  GROUP BY
    heure, year, month, day, hour
);
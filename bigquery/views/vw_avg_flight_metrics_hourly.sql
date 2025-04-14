CREATE OR REPLACE VIEW `toulouse-aero-analysis.aeronautics_data.vw_avg_flight_metrics_hourly`
OPTIONS(
  description="Altitude barométrique et vitesse sol moyennes par heure pour les avions en vol."
)
AS (
  SELECT
    year,
    month,
    day,
    hour,
    -- Calculs
    AVG(baro_altitude) AS altitude_moyenne_m,
    AVG(velocity) AS vitesse_moyenne_mps
  FROM
    `toulouse-aero-analysis.aeronautics_data.flight_data_external`
  WHERE
    on_ground = false      -- Uniquement les avions en vol
    AND baro_altitude IS NOT NULL
    AND velocity IS NOT NULL
  GROUP BY
    -- Grouper par les partitions
    year, month, day, hour
)
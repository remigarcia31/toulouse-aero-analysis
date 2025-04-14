CREATE OR REPLACE VIEW `toulouse-aero-analysis.aeronautics_data.vw_aircraft_in_tls_zone_hourly`
OPTIONS(
  description="Nombre d'avions uniques par heure dans une zone prédéfinie autour de TLS."
)
AS (
  WITH ZoneTLS AS (
    SELECT ST_GEOGFROMTEXT('POLYGON((1.25 43.55, 1.45 43.55, 1.45 43.70, 1.25 43.70, 1.25 43.55))') as zone_polygon
  )
  SELECT
    -- Colonnes de partition
    t.year,
    t.month,
    t.day,
    t.hour,
    -- Heure tronquée pour l'agrégation
    TIMESTAMP_TRUNC(t.fetch_time, HOUR) AS heure,
    -- Calcul
    COUNT(DISTINCT t.icao24) AS nombre_avions_uniques_zone_tls
  FROM
    `toulouse-aero-analysis.aeronautics_data.flight_data_external` AS t,
    ZoneTLS -- Jointure implicite (CROSS JOIN car ZoneTLS n'a qu'une ligne)
  WHERE
    -- Filtrer les points valides
    t.longitude IS NOT NULL
    AND t.latitude IS NOT NULL
    -- Vérifier l'intersection géographique
    AND ST_INTERSECTS(ZoneTLS.zone_polygon, ST_GEOGPOINT(t.longitude, t.latitude))
  GROUP BY
    -- Grouper par les partitions ET l'heure tronquée
    t.year, t.month, t.day, t.hour, heure
)
CREATE OR REPLACE VIEW `toulouse-aero-analysis.aeronautics_data.vw_flight_trajectories_sequenced`
OPTIONS(
  description="Ajoute un numéro de séquence et les informations du point précédent pour chaque vol (basé sur icao24 et time_position)."
)
AS (
  SELECT
    icao24,
    callsign,
    origin_country,
    time_position,
    last_contact,
    longitude,
    latitude,
    baro_altitude,
    on_ground,
    velocity,
    true_track,
    vertical_rate,
    geo_altitude,
    squawk,
    spi,
    position_source,
    fetch_time,
    year,
    month,
    day,
    hour,
    -- Ajout du numéro de séquence
    ROW_NUMBER() OVER (PARTITION BY icao24 ORDER BY time_position ASC, fetch_time ASC) as sequence_num,
    -- Ajout des infos du point précédent
    LAG(time_position, 1) OVER (PARTITION BY icao24 ORDER BY time_position ASC, fetch_time ASC) as prev_time_position,
    LAG(longitude, 1) OVER (PARTITION BY icao24 ORDER BY time_position ASC, fetch_time ASC) as prev_longitude,
    LAG(latitude, 1) OVER (PARTITION BY icao24 ORDER BY time_position ASC, fetch_time ASC) as prev_latitude,
    LAG(baro_altitude, 1) OVER (PARTITION BY icao24 ORDER BY time_position ASC, fetch_time ASC) as prev_baro_altitude
  FROM
    `toulouse-aero-analysis.aeronautics_data.flight_data_external`
  WHERE
    time_position IS NOT NULL
)
"""Region-parametrized extraction SQL for the OpenSky visualization.

Ported verbatim from ../data-prep/gen_sql.py, with the source table made
configurable ({catalog}.{schema}.state_vectors) so the runtime "Regenerate from
Marketplace" path can target whichever catalog/schema the dataset was installed
under. Keep the query bodies byte-identical to the offline generator so the
produced artifacts match the shipped snapshot.
"""

REGIONS = {
    "europe": {"lon": (-12, 30), "lat": (35, 60)},
    "north-america": {"lon": (-125, -66), "lat": (24, 50)},
    "australia": {"lon": (112, 154), "lat": (-44, -10)},
}

PRISM = """-- Space-Time Prism: top ~1500 {region} flights on 2026-03-01, resampled to 60s.
WITH top_flights AS (
  SELECT icao24, callsign, COUNT(*) AS pts
  FROM {src}
  WHERE latitude BETWEEN {lat0} AND {lat1} AND longitude BETWEEN {lon0} AND {lon1}
    AND latitude IS NOT NULL AND on_ground = false
    AND callsign IS NOT NULL AND trim(callsign) <> ''
  GROUP BY icao24, callsign
  ORDER BY pts DESC
  LIMIT 1500
),
resampled AS (
  SELECT s.icao24, trim(s.callsign) AS callsign,
         CAST(unix_timestamp(s.time_position) / 60 AS INT) AS mb,
         ROUND(AVG(s.latitude), 4)     AS lat,
         ROUND(AVG(s.longitude), 4)    AS lon,
         ROUND(AVG(s.geo_altitude), 0) AS alt,
         ROUND(AVG(s.velocity), 0)     AS vel,
         MIN(unix_timestamp(s.time_position)) AS ts
  FROM {src} s
  JOIN top_flights f ON s.icao24 = f.icao24 AND s.callsign = f.callsign
  WHERE s.latitude BETWEEN {lat0} AND {lat1} AND s.longitude BETWEEN {lon0} AND {lon1}
    AND s.latitude IS NOT NULL AND s.on_ground = false
  GROUP BY s.icao24, trim(s.callsign), CAST(unix_timestamp(s.time_position) / 60 AS INT)
)
SELECT icao24, callsign, COUNT(*) AS n, MIN(ts) AS t0, MAX(ts) AS t1,
       collect_list(struct(ts, lat, lon, alt, vel)) AS pts_unsorted
FROM resampled
GROUP BY icao24, callsign
ORDER BY icao24, callsign
"""

DENSITY = """-- Breathing Sky: H3 res4 x 10-min density of distinct aircraft over {region}.
WITH pts AS (
  SELECT h3_longlatash3(longitude, latitude, 4) AS hex,
         CAST(unix_timestamp(time_position) / 600 AS INT) AS tb,
         CASE WHEN geo_altitude < 3000 THEN 0 WHEN geo_altitude < 8000 THEN 1 ELSE 2 END AS band,
         icao24
  FROM {src}
  WHERE latitude BETWEEN {lat0} AND {lat1} AND longitude BETWEEN {lon0} AND {lon1}
    AND latitude IS NOT NULL AND on_ground = false
)
SELECT h3_h3tostring(hex) AS hex, tb,
       COUNT(DISTINCT CASE WHEN band = 0 THEN icao24 END) AS c0,
       COUNT(DISTINCT CASE WHEN band = 1 THEN icao24 END) AS c1,
       COUNT(DISTINCT CASE WHEN band = 2 THEN icao24 END) AS c2
FROM pts
GROUP BY h3_h3tostring(hex), tb
ORDER BY tb, hex
"""

CURVE = """-- True distinct-aircraft breathing curve per 10-min bucket over {region}.
SELECT CAST(unix_timestamp(time_position) / 600 AS INT) AS tb,
       COUNT(DISTINCT icao24) AS total,
       COUNT(DISTINCT CASE WHEN geo_altitude < 3000 THEN icao24 END) AS c0,
       COUNT(DISTINCT CASE WHEN geo_altitude >= 3000 AND geo_altitude < 8000 THEN icao24 END) AS c1,
       COUNT(DISTINCT CASE WHEN geo_altitude >= 8000 THEN icao24 END) AS c2
FROM {src}
WHERE latitude BETWEEN {lat0} AND {lat1} AND longitude BETWEEN {lon0} AND {lon1}
  AND latitude IS NOT NULL AND on_ground = false
GROUP BY 1 ORDER BY 1
"""

ANOMALY = """-- Anomalies over {region}: emergency squawks (7500/7600/7700) + top-20 steepest
-- vertical-rate flights. One row per flight with a resampled (60s) track + reason flags.
WITH flags AS (
  SELECT icao24, trim(callsign) AS callsign,
         MAX(CASE WHEN squawk = '7500' THEN 1 ELSE 0 END) AS e75,
         MAX(CASE WHEN squawk = '7600' THEN 1 ELSE 0 END) AS e76,
         MAX(CASE WHEN squawk = '7700' THEN 1 ELSE 0 END) AS e77,
         MAX(ABS(vertical_rate)) AS max_vr,
         MIN(CASE WHEN squawk IN ('7500','7600','7700') THEN unix_timestamp(time_position) END) AS t_emerg
  FROM {src}
  WHERE latitude BETWEEN {lat0} AND {lat1} AND longitude BETWEEN {lon0} AND {lon1}
    AND on_ground = false AND callsign IS NOT NULL AND trim(callsign) <> ''
  GROUP BY icao24, trim(callsign)
),
ranked AS (
  SELECT *, ROW_NUMBER() OVER (ORDER BY max_vr DESC NULLS LAST) AS vr_rank FROM flags
),
anom AS (
  SELECT * FROM ranked WHERE e75 = 1 OR e76 = 1 OR e77 = 1 OR vr_rank <= 20
),
resampled AS (
  SELECT s.icao24, trim(s.callsign) AS callsign,
         CAST(unix_timestamp(s.time_position) / 60 AS INT) AS mb,
         ROUND(AVG(s.latitude), 4) AS lat, ROUND(AVG(s.longitude), 4) AS lon,
         ROUND(AVG(s.geo_altitude), 0) AS alt, MIN(unix_timestamp(s.time_position)) AS ts
  FROM {src} s
  JOIN anom a ON s.icao24 = a.icao24 AND trim(s.callsign) = a.callsign
  WHERE s.latitude BETWEEN {lat0} AND {lat1} AND s.longitude BETWEEN {lon0} AND {lon1}
    AND s.latitude IS NOT NULL AND s.on_ground = false
  GROUP BY s.icao24, trim(s.callsign), CAST(unix_timestamp(s.time_position) / 60 AS INT)
)
SELECT a.icao24, a.callsign, a.e75, a.e76, a.e77, ROUND(a.max_vr, 1) AS max_vr, a.t_emerg,
       COUNT(*) AS n, collect_list(struct(r.ts, r.lat, r.lon, r.alt)) AS pts_unsorted
FROM resampled r JOIN anom a ON r.icao24 = a.icao24 AND r.callsign = a.callsign
GROUP BY a.icao24, a.callsign, a.e75, a.e76, a.e77, a.max_vr, a.t_emerg
ORDER BY a.icao24, a.callsign
"""

_TEMPLATES = {"prism": PRISM, "density": DENSITY, "curve": CURVE, "anomaly": ANOMALY}


def build(region: str, catalog: str = "marketplace", schema: str = "opensky") -> dict:
    """Return {"prism","density","curve","anomaly"} SQL for a region.

    The source table is `{catalog}.{schema}.state_vectors`. Identifier parts are
    backtick-quoted so hyphenated catalog/schema names survive.
    """
    r = REGIONS[region]
    src = f"`{catalog}`.`{schema}`.state_vectors"
    ctx = {
        "region": region, "src": src,
        "lon0": r["lon"][0], "lon1": r["lon"][1],
        "lat0": r["lat"][0], "lat1": r["lat"][1],
    }
    return {name: tpl.format(**ctx) for name, tpl in _TEMPLATES.items()}

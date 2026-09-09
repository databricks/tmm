"""
Receive the OpenSky Marketplace data locally with the open Delta Sharing client.

No Spark, no Java — just Python + delta-sharing + pandas. Lists the shared tables,
then pushes a predicate to the sharing server so only matching files cross the
network (baro_altitude < 3000 m), and re-applies the filter in pandas for an exact
result.

Setup (see ./README.md or Module 7):
    uv venv --python 3.12 --seed
    source .venv/bin/activate
    uv pip install delta-sharing pandas

Run:
    python receive_opensky.py
"""

import json

import delta_sharing

# Point this at your Delta Sharing profile (.share) file — download it from the
# Databricks Marketplace listing ("Download credential file"). The table path is
# "<profile>#<share>.<schema>.<table>"; adjust <share> to the share name in your
# credential file (list_all_tables prints it).
PROFILE = "opensky.share"
TABLE = f"{PROFILE}#opensky_marketplace.opensky.state_vectors"

client = delta_sharing.SharingClient(PROFILE)
for t in client.list_all_tables():          # what the share exposes
    print(f"{t.share}.{t.schema}.{t.name}")

# Push a predicate down to the server so it skips non-matching files:
# baro_altitude < 3000. It's a file-skipping hint (may return a superset),
# so we re-apply the filter in pandas for an exact result.
low_altitude = {
    "op": "lessThan",
    "children": [
        {"op": "column", "name": "baro_altitude", "valueType": "double"},
        {"op": "literal", "value": "3000", "valueType": "double"},
    ],
}

df = delta_sharing.load_as_pandas(TABLE, jsonPredicateHints=json.dumps(low_altitude), limit=1000)
df = df[df["baro_altitude"] < 3000]
print(df.shape)
print(df[["icao24", "callsign", "time_position", "latitude", "longitude", "baro_altitude"]].head())

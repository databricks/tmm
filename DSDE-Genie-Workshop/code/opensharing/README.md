# Receive shared data locally (Module 7)

Minimal local client that **receives** Databricks-shared OpenSky data over the open Delta Sharing
/ OpenSharing protocol — pure Python, **no Spark and no Java**.

## Setup (uv)

```bash
uv venv --python 3.12 --seed
source .venv/bin/activate
uv pip install delta-sharing pandas
```

(Plain pip works too: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.)

## Get a credential file

- **Real data:** on the Databricks Marketplace listing, use **Download credential file** to save a
  `.share` profile (endpoint + bearer token) next to `receive_opensky.py` as `opensky.share`.
- **Try the mechanics first (no Databricks):** use the public demo profile
  `https://raw.githubusercontent.com/delta-io/delta-sharing/main/examples/open-datasets.share`
  and point `receive_opensky.py` at a demo table such as
  `open-datasets.share#delta_sharing.default.boston-housing`.

## Run

```bash
python receive_opensky.py
```

`SharingClient(profile).list_all_tables()` lists what the share exposes; `load_as_pandas(url, limit=...)`
pulls rows into a pandas DataFrame. Verified locally with delta-sharing 1.4.2 / pandas 2.3.3 / Python 3.12.

## Scale up (optional)

For large tables use `delta_sharing.load_as_spark(...)`, which needs Java 17 + PySpark — the same
stack as the [OSS Spark Declarative Pipelines guide](https://github.com/databricks/tmm/tree/main/OSS-SDP-OpenSkyNetwork).

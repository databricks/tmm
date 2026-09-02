"""
Receive the OpenSky Marketplace data locally with the open Delta Sharing client.

No Spark, no Java — just Python + delta-sharing + pandas.

Setup (see ../opensharing/README.md or Module 7):
    uv venv --python 3.12 --seed
    source .venv/bin/activate
    uv pip install delta-sharing pandas

Run:
    python receive_opensky.py
"""

import delta_sharing

# 1. Point this at your Delta Sharing profile (.share) file.
#    Download it from the Databricks Marketplace listing ("Download credential file"),
#    or use the public demo profile from the README to try the mechanics first.
PROFILE = "opensky.share"

# 2. Table path is "<profile>#<share>.<schema>.<table>".
#    Adjust <share> to the share name in your credential file (list_all_tables prints it).
TABLE = f"{PROFILE}#opensky_share.opensky.state_vectors"


def main() -> None:
    client = delta_sharing.SharingClient(PROFILE)

    print("Tables in this share:")
    for t in client.list_all_tables():
        print(f"  {t.share}.{t.schema}.{t.name}")

    # Receive straight into a pandas DataFrame. Keep `limit` while exploring —
    # the full share is hundreds of millions of rows.
    df = delta_sharing.load_as_pandas(TABLE, limit=1000)

    print(f"\nReceived {len(df):,} rows x {df.shape[1]} columns")
    print(df.head())


if __name__ == "__main__":
    main()

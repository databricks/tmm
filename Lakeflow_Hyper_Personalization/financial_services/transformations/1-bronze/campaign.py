import dlt

@dlt.table
@dlt.expect_or_drop("valid_outcome", "outcome != 'UNKNOWN'")
@dlt.expect_or_drop("valid_campaign", "campaign_id is not NULL")
def campaign():
    return (
        spark.readStream.table("finance_summit.ingestion.campaign")
    )
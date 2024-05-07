"""
1. Fill in the CONFIG values below
2. Execute on the new DBR version
3. Schedule weekly to fetch the latest user/workspace information
"""
# START: --- CONFIG ----

## Make sure to set "accounts.cloud.databricks.com", "accounts.azuredatabricks.com" or "accounts.gcp.databricks.com" as appropriate.
HOST = ""

# Current account_id, ie 7a99b43c-b46c-432b-b0a7-814217701909
ACCOUNT_ID = ""

# CLIENT_ID and CLIENT_SECRET come from the account-admin service principal, if you don't have one, follow the Step 1 of this doc:
# https://docs.databricks.com/en/dev-tools/auth/oauth-m2m.html#step-1-create-a-service-principal
# Once you have the service principal ready, generate a CLIENT_SECRET from the Step 3 in the doc mentioned above.
CLIENT_ID = ""

# Ideally, don't store the secret in a raw string form, use SECRETS
# https://docs.databricks.com/en/security/secrets/index.html
CLIENT_SECRET = ""

# Table paths for user/workspace tables, can be 2 element if still using HMS
USERS_TABLE_PATH = "jacek.default.users"
WORKSPACES_TABLE_PATH = "jacek.default.workspaces"

# END: --- CONFIG ---

import re

from databricks.sdk import AccountClient

from delta.tables import *
from pyspark.sql.functions import *
from pyspark.sql.types import *

USERS_TABLE_SCHEMA = StructType(
    [
        StructField("id", StringType(), True),
        StructField("user_name", StringType(), True),
        StructField("display_name", StringType(), True),
        StructField("active", BooleanType(), True),
        # TODO - extend as needed
    ]
)


WORKSPACES_TABLE_SCHEMA = StructType(
    [
        StructField("account_id", StringType(), True),
        StructField("aws_region", StringType(), True),
        StructField(
            "azure_workspace_info", StringType(), True
        ),  # Assuming StringType for simplicity, adjust as needed
        StructField("cloud", StringType(), True),
        StructField("cloud_resource_container", StringType(), True),
        StructField("creation_time", LongType(), True),
        StructField("credentials_id", StringType(), True),
        StructField("deployment_name", StringType(), True),
        StructField("location", StringType(), True),
        StructField("managed_services_customer_managed_key_id", StringType(), True),
        StructField("network_id", StringType(), True),
        StructField("pricing_tier", StringType(), True),  # Enum converted to String
        StructField("private_access_settings_id", StringType(), True),
        StructField("storage_configuration_id", StringType(), True),
        StructField("storage_customer_managed_key_id", StringType(), True),
        StructField("workspace_id", LongType(), True),
        StructField("workspace_name", StringType(), True),
        StructField("workspace_status", StringType(), True),  # Enum converted to String
        StructField("workspace_status_message", StringType(), True),
        # TODO - extend as needed
    ]
)


def save_as_table(table_path, schema, df, pk_columns=["id"]):
    assert (
        df.schema == schema
    ), f"""
      Schemas are not equal.
      Expected: {schema}
      Actual: {df.schema}"""

    deltaTable = (
        DeltaTable.createIfNotExists(spark)
        .tableName(table_path)
        .addColumns(schema)
        .execute()
    )

    merge_statement = " AND ".join([f"logs.{col}=newLogs.{col}" for col in pk_columns])

    (
        deltaTable.alias("logs")
        .merge(
            df.alias("newLogs"),
            f"{merge_statement}",
        )
        .whenNotMatchedInsertAll()
        .whenMatchedUpdateAll()
        .execute()
    )


def to_snake(s):
    return re.sub("([A-Z]\w+$)", "_\\1", s).lower()


def t_dict(d):
    if isinstance(d, list):
        return [t_dict(i) if isinstance(i, (dict, list)) else i for i in d]
    return {
        to_snake(a): t_dict(b) if isinstance(b, (dict, list)) else b
        for a, b in d.items()
    }


def main():
    a = AccountClient(
        host=HOST,
        account_id=ACCOUNT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )

    print("Fetching users from the Account API..")
    users = [t_dict(user.to_dict()) for user in a.users.list()]
    users_df = spark.createDataFrame(users, schema=USERS_TABLE_SCHEMA)
    save_as_table(USERS_TABLE_PATH, USERS_TABLE_SCHEMA, users_df, pk_columns=["id"])
    print(f"{USERS_TABLE_PATH} created ({len(users)} rows)")

    print("Fetching workspaces from the Account API..")
    workspaces = [workspace.as_dict() for workspace in a.workspaces.list()]
    workspaces_df = spark.createDataFrame(workspaces, schema=WORKSPACES_TABLE_SCHEMA)
    save_as_table(
        WORKSPACES_TABLE_PATH,
        WORKSPACES_TABLE_SCHEMA,
        workspaces_df,
        pk_columns=["workspace_id"],
    )
    print(f"{WORKSPACES_TABLE_PATH} created ({len(workspaces)} rows)")


main()

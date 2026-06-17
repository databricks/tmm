CREATE OR REPLACE STREAMING TABLE raw_space_events
(
  CONSTRAINT timestamp_not_null EXPECT (timestamp IS NOT NULL)
)
AS
  SELECT offset, timestamp, value::string as msg
   FROM STREAM read_kafka(
    bootstrapServers => 'kafka.gcn.nasa.gov:9092',
    subscribe => 'gcn.circulars',
    startingOffsets => 'earliest',

    -- params kafka.sasl.oauthbearer.client.id
    `kafka.sasl.mechanism` => 'OAUTHBEARER',
    `kafka.security.protocol` => 'SASL_SSL',
    `kafka.sasl.oauthbearer.token.endpoint.url` => 'https://auth.gcn.nasa.gov/oauth2/token', 
    `kafka.sasl.login.callback.handler.class` => 'kafkashaded.org.apache.kafka.common.security.oauthbearer.secured.OAuthBearerLoginCallbackHandler',


    -- Credentials are read from the Databricks secret scope `gcn_kafka`
    -- (deployed via scripts/deploy_secret_scope.sh). secret() redacts in logs/output.
    `kafka.sasl.jaas.config` =>
         'kafkashaded.org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginModule required clientId="'
         || secret('gcn_kafka', 'client_id')
         || '" clientSecret="'
         || secret('gcn_kafka', 'client_secret')
         || '" ;'
  );

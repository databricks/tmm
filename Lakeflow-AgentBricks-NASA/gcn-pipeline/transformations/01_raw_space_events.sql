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


    `kafka.sasl.jaas.config` =>  
         '
          kafkashaded.org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginModule required
          clientId="3tedd4qhr6t5rp67s6as7pi56s"
          clientSecret="1ph8inouq89b5lr53g0ppq3r3b9fouoic9lqdv57ebr4ruhb7qcn" ;          
          '
  );

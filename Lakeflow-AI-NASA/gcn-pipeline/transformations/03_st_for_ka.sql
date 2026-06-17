-- Silver (KA-format): reshape parsed circulars into the Agent Bricks
-- "Files in a Table" knowledge-source schema.
--   content                : full denormalized circular text (event_id + subject + body + submitter)
--   metadata STRUCT         : file_path / file_name / file_size / file_modification_time
-- Streaming table => satisfies the KA "streaming table OR CDF" requirement.
-- Data quality: drop rows with empty content (circulars missing subject/body
-- yield null content) so the KA never ingests empty "files".
CREATE OR REFRESH STREAMING TABLE st_for_ka
(
  CONSTRAINT content_not_empty
    EXPECT (content IS NOT NULL AND length(trim(content)) > 0) ON VIOLATION DROP ROW
)
AS SELECT
  CONCAT(event_id, ' ', subject, ' ', body, ' ', submitter) AS content,
  named_struct(
    'file_path',              CONCAT('https://gcn.nasa.gov/circulars/', circular_id),
    'file_name',              CONCAT(circular_id, '.txt'),
    'file_size',              CAST(LENGTH(CONCAT(event_id, ' ', subject, ' ', body, ' ', submitter)) AS BIGINT),
    'file_modification_time', created_on
  ) AS metadata
FROM STREAM(parsed_space_events);

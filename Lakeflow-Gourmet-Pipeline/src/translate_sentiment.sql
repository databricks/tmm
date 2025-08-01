
USE CATALOG demos1;
USE SCHEMA `gourmet-snacks`;

ALTER TABLE flagship_stores
ADD COLUMN desc_es STRING;

ALTER TABLE flagship_stores
ADD COLUMN sentiment STRING;

UPDATE flagship_stores
SET
  desc_es = ai_translate(description, 'es'),
  sentiment = ai_analyze_sentiment(description);
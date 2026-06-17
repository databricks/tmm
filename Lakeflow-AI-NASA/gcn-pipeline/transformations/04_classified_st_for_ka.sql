-- Silver+ (KA-format, classified): apply ai_classify to the st_for_ka content
-- column so the KA file-table source also carries a cosmic-event label. Keeps
-- content + metadata so it stays a valid "Files in a Table" knowledge source.
CREATE OR REFRESH STREAMING TABLE classified_st_for_ka
AS SELECT
    content,
    metadata,
    ai_classify(
      content,
      ARRAY(
        'gamma-ray burst',
        'fast X-ray transient',
        'gravitational wave',
        'neutrino',
        'supernova',
        'optical transient',
        'other'
      )
    ) AS event_class
  FROM STREAM(st_for_ka);

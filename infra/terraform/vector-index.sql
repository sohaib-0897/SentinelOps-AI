-- Optional acceleration after enough rows exist (BigQuery may use brute force for small tables).
-- Replace PROJECT_ID and DATASET via deployment tooling; identifiers are validated there.
CREATE VECTOR INDEX IF NOT EXISTS history_hash128_v1
ON `PROJECT_ID.DATASET.historical_incidents`(embedding)
OPTIONS(index_type = 'IVF', distance_type = 'COSINE');

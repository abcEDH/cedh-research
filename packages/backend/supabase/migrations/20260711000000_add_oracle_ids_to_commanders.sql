-- Add oracle_ids column to commanders table for Universes Beyond deduplication
ALTER TABLE commanders ADD COLUMN oracle_ids TEXT[];

-- Create index for oracle_id lookups
CREATE INDEX idx_commanders_oracle_ids ON commanders USING GIN (oracle_ids);

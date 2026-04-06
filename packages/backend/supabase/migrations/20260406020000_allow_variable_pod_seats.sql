-- Allow historical pods larger than four players during ingestion backfills.

ALTER TABLE game_participants
  DROP CONSTRAINT IF EXISTS game_participants_seat_position_check;

ALTER TABLE game_participants
  ADD CONSTRAINT game_participants_seat_position_check
  CHECK (seat_position >= 0);

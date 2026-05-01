-- Add difficulty column (1=easiest … 5=hardest) to control progressive
-- introduction of new vocabulary. Existing cards default to 3 (mid-level).
ALTER TABLE cards ADD COLUMN difficulty INTEGER NOT NULL DEFAULT 3;

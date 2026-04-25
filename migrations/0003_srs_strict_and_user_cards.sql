ALTER TABLE cards ADD COLUMN lexical_unit_id INTEGER;
ALTER TABLE cards ADD COLUMN direction TEXT NOT NULL DEFAULT 'ka_ru';
ALTER TABLE cards ADD COLUMN accepted_answers_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE cards ADD COLUMN letter TEXT;
ALTER TABLE cards ADD COLUMN example_ka TEXT;
ALTER TABLE cards ADD COLUMN example_ru TEXT;
ALTER TABLE cards ADD COLUMN source TEXT NOT NULL DEFAULT 'curated';
ALTER TABLE cards ADD COLUMN owner_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;

UPDATE cards
SET lexical_unit_id = id
WHERE lexical_unit_id IS NULL;

-- Remove curated alphabet cards (topic = 'alphabet').
-- user_cards and review_events rows are deleted automatically via ON DELETE CASCADE.
DELETE FROM cards WHERE topic = 'alphabet' AND owner_user_id IS NULL;

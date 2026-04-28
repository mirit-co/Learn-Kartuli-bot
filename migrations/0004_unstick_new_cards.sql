-- Old code (commit 83af23d) used '9999-12-31' as a sentinel for "new card,
-- not yet drawn into a session". The strict-SRS refactor (commit 97bf7d4)
-- replaced that with today+1, but never migrated existing rows, so those
-- cards stay invisible to the due queue forever. Pull them back to "due
-- tomorrow" so they enter the rotation normally.
UPDATE user_cards
SET next_review_date = DATE('now', '+1 day')
WHERE next_review_date = '9999-12-31';

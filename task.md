Goal: Create a Telegram bot that implements the Leitner System for spaced repetition of vocabulary. I want to learn georgian, my native language is russian. It should be everyday words with alphabet memorising. At the end of a course I could speak at the grocery, transport, market, could have a small talk with georgian people. Like A1 level.

Learning approach: Alphabet is NOT taught separately as bare letters. Each letter is learned together with a real word that starts with it (e.g. ა — ანანასი/ананас). This way I memorize the letter shape, its sound, AND a useful word at the same time.

Core Logic (Leitner System):
Card Structure: Each card has: id, front_side (word/phrase), back_side (translation), current_box (1-5), and next_review_date.

The Boxes:
Box 1: Review every day.
Box 2: Review every 2 days.
Box 3: Review every 7 days.
Box 4: Review every 14 days.
Box 5: Review every 30 days.

Movement Rules:
Correct Answer: Move the card to the next box (e.g., from 1 to 2). Update next_review_date based on the box interval.

Wrong Answer: Immediately move the card back to Box 1, regardless of its current position.

Daily Session:
When the user starts a session, the bot fetches all cards where next_review_date <= today.
The bot shows the front_side (Georgian) and asks the user to type the Russian translation.
If the answer is correct → card is promoted to the next box.
If the answer is wrong → the bot shows the correct translation and the card goes back to Box 1.
There is a "Не знаю" (skip) button — pressing it counts as a wrong answer and shows the correct translation.
It has to remind me every morning to learn georgian. I could set up exact time for notifications. 

Please think what skills you need to perform this task every day. For example, one skill that conduct everyday vocabulary for newbies, the second one for learning methology. I want to see them separetely in the project and upgrade selected skill.
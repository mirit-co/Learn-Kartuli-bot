PYTHONPATH=src

.PHONY: run test lint validate-deck

run:
	PYTHONPATH=$(PYTHONPATH) python3 -m kartuli_bot.main

test:
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s tests -p "test_*.py"

validate-deck:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/validate_deck.py

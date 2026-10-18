# GraphSentinel – convenience commands
# Usage: make <target>

.PHONY: up down seed run test

## Start FalkorDB in Docker
up:
	docker compose up -d
	@echo "✅ FalkorDB running on localhost:6379 | Browser: http://localhost:3000"

## Stop FalkorDB
down:
	docker compose down

## Seed the graph with synthetic fraud data
seed:
	python data/generate_data.py

## Launch the Streamlit app
run:
	streamlit run app.py

## Full setup from scratch
setup: up
	@sleep 3
	$(MAKE) seed
	$(MAKE) run

## Install Python deps
install:
	pip install -r requirements.txt

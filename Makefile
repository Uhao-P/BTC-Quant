.PHONY: init backfill run-api run-collector dev docker-up docker-down docker-logs

init:
	@bash scripts/init.sh

backfill:
	@./venv/bin/python scripts/backfill.py $(ARGS)

run-api:
	@./venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8700 --reload

run-collector:
	@./venv/bin/python scripts/collector_daemon.py

dev:
	@echo "Start API + Frontend..."
	@./venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8700 &
	@cd frontend && pnpm dev

docker-up:
	@docker compose up -d --build

docker-down:
	@docker compose down

docker-logs:
	@docker compose logs -f

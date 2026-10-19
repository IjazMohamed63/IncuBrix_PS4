.PHONY: up down test contract-test clean lint

up:
	docker compose up -d

down:
	docker compose down

test:
	pytest tests/

contract-test:
	pytest tests/contract

clean:
	docker compose down -v
	rm -rf __pycache__ .pytest_cache

.PHONY: test

test:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ --cov=newsfeed --cov-report=term-missing

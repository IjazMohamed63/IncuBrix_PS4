FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir fastapi uvicorn pydantic

COPY mock_platforms/ ./mock_platforms/

ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["uvicorn", "mock_platforms.main:app", "--host", "0.0.0.0", "--port", "8080"]

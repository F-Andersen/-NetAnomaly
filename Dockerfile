FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

COPY pyproject.toml ./
COPY src ./src
COPY tests ./tests
RUN pip install --no-deps -e .

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data /app/artifacts /app/reports \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "--factory", "netanomaly.api.main:app_factory", "--host", "0.0.0.0", "--port", "8000"]

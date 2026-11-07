FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-docker.txt

RUN useradd --create-home appuser

COPY --chown=appuser:appuser app.py .
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser templates/ ./templates/
COPY --chown=appuser:appuser static/ ./static/

RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=5)" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "app:app"]
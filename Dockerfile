FROM python:3.11-slim

# Install system deps for WeasyPrint (PDF generation) and Docker CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install -e .

RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8501
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

CMD ["sh", "-c", "uvicorn api.server:app --host 0.0.0.0 --port 8000 & streamlit run ui/app.py --server.address=0.0.0.0"]

FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libpango-1.0-0=1.50.12+ds-1 \
    libpangoft2-1.0-0=1.50.12+ds-1 \
    libcairo2=1.16.0-7 \
    curl=7.88.1-10+deb12u8 \
    docker.io=20.10.24+dfsg1-1+deb12u1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser && usermod -aG docker appuser && chown -R appuser /app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install -e .

RUN chown -R appuser /app
USER appuser

EXPOSE 8501
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

CMD ["sh", "-c", "uvicorn api.server:app --host 0.0.0.0 --port 8000 & streamlit run ui/app.py --server.address=0.0.0.0"]

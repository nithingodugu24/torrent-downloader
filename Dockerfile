FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend:/usr/lib/python3/dist-packages

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-libtorrent \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY .env.example ./.env.example

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000"]

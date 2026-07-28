FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY config ./config
COPY data ./data
COPY indicators ./indicators
COPY scripts ./scripts
COPY strategies ./strategies
COPY services ./services
COPY __init__.py ./

RUN mkdir -p /app/storage

ENV PYTHONPATH=/app

EXPOSE 8700

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8700"]

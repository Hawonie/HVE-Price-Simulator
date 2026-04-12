FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory for SQLite
RUN mkdir -p /data

ENV TRACKER_DATABASE_URL=sqlite+aiosqlite:////data/tracker.db
ENV TRACKER_LOG_LEVEL=INFO

EXPOSE 10000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]

FROM python:3.11-slim
WORKDIR /app
COPY common/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY aggregator-worker/app app
CMD ["python", "-m", "app.worker"]

FROM node:22-alpine AS frontend

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend /app/backend/app/static backend/app/static
COPY docs/ docs/
COPY cli/ cli/
COPY README.md ./

ENV TASKS_PLANNER_HOST=0.0.0.0 \
    TASKS_PLANNER_PORT=56649 \
    TASKS_PLANNER_DATA_DIR=/data

VOLUME ["/data"]
EXPOSE 56649

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:56649/api/health')"

CMD ["python", "backend/run.py"]

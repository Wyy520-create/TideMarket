FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV TM_UPLOAD_DIR=/data/uploads \
    TM_DATABASE_URL=postgresql+asyncpg://tide:tide@db:5432/tidemarket \
    TM_REDIS_URL=redis://redis:6379/0

VOLUME ["/data/uploads"]
EXPOSE 8000

# 同一镜像内启动 API 服务 + arq 定时任务 worker（超时关单）
CMD ["sh", "-c", "arq worker.WorkerSettings & exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]

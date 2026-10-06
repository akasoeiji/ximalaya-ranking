FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TZ=Asia/Shanghai

RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN chmod +x /app/entrypoint.sh && mkdir -p /app/output
VOLUME ["/app/output"]

# CMD: manual=跑一次退出 | schedule=按 SCHEDULE_INTERVAL_SECONDS 循环(默认86400s=每天)
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["manual"]

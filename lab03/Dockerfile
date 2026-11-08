FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    TZ=Europe/Chisinau

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends cron tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/lab03

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY currency_exchange_rate.py cronjob cronjob.test entrypoint.sh ./
RUN chmod 755 /app/lab03/entrypoint.sh \
    && chmod 644 /app/lab03/cronjob /app/lab03/cronjob.test

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD test -s /var/run/crond.pid && kill -0 "$(cat /var/run/crond.pid)" || exit 1

ENTRYPOINT ["/app/lab03/entrypoint.sh"]

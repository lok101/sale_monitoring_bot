FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends cron tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir . \
    && sed -i 's/\r$//' /app/entrypoint.sh /app/run_cron_report.sh \
    && chmod +x /app/entrypoint.sh /app/run_cron_report.sh

ENTRYPOINT ["/app/entrypoint.sh"]

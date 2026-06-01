#!/bin/sh
set -eu
. /app/cron_env.sh
cd /app
exec python -m sale_monitoring_bot "$@"

#!/bin/sh
/usr/bin/env poetry run alembic upgrade head
/usr/bin/env poetry run uvicorn --proxy-headers \
       --forwarded-allow-ips "*" \
       --host "0.0.0.0" \
       --port 8080 \
       ladsetal.site:app

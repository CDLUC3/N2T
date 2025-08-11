#!/bin/bash
set -e

echo "Starting Unit in background..."
unitd --no-daemon --control unix:/var/run/control.unit.sock &
UNIT_PID=$!

echo "Waiting for NGIX Unit to be read ..."
until curl --unix-socket /var/run/control.unit.sock http://localhost/status 2>/dev/null; do
    sleep 0.5
done

sleep 0.2  # small extra buffer

echo "Loading unit configuration..."
curl -X PUT \
     --data-binary @/docker-entrypoint.d/config.json \
     --unix-socket /var/run/control.unit.sock \
     http://localhost/config

echo "NGINX Unit started. Keeping container running..."
wait $UNIT_PID
#!/usr/bin/env bash
set -e
URL="http://127.0.0.1:8000/"
if curl -fsS -m 3 "$URL" >/dev/null 2>&1; then
  exit 0
fi
exit 1

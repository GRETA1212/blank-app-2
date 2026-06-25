#!/bin/sh
set -eu

for file in /migrations/*.sql; do
  echo "Applying ${file}"
  psql \
    -h postgres \
    -U "${POSTGRES_USER:-studio}" \
    -d "${POSTGRES_DB:-studio}" \
    -v ON_ERROR_STOP=1 \
    -f "${file}"
done

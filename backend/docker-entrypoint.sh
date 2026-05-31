#!/bin/sh
set -e

# Apply database migrations before starting the application server.
echo "Running database migrations..."
alembic upgrade head

echo "Starting: $*"
exec "$@"

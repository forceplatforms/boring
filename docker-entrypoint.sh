#!/bin/bash
set -e

echo "🔄 Starting ComplianceGuard API..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
until pg_isready -h postgres -p 5432 -U complianceguard; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done
echo "✅ PostgreSQL is ready!"

# Run database migrations
echo "🔄 Running database migrations..."
alembic upgrade head
echo "✅ Migrations complete!"

# Start the application
echo "🚀 Starting Uvicorn..."
exec "$@"

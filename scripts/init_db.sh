#!/bin/bash
# Database initialization script for Docker
# This script waits for PostgreSQL to be ready and then runs Alembic migrations

set -e

echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h postgres -U postgres; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is up - running migrations..."
alembic upgrade head

echo "Database migrations completed successfully!"


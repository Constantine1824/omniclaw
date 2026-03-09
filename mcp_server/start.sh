#!/bin/bash
# Startup script for Cloud Run
# Cloud Run sets PORT environment variable automatically

set -e

# Default port if PORT is not set
PORT=${PORT:-8080}

# Log startup information
echo "Starting OmniClaw MCP Server..."
echo "PORT=${PORT}"
echo "ENVIRONMENT=${ENVIRONMENT:-not set}"

# Start uvicorn with proper signal handling
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"

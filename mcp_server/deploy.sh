#!/bin/bash
# Deployment script for Google Cloud Run

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
# Use GCP_PROJECT_ID env var, or get from gcloud config, or prompt user
if [ -z "$GCP_PROJECT_ID" ]; then
  PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
  if [ -z "$PROJECT_ID" ]; then
    echo "Error: No project ID found. Set GCP_PROJECT_ID or run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
  fi
else
  PROJECT_ID="$GCP_PROJECT_ID"
fi

REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-omniclaw-mcp-server}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo -e "${GREEN}Using project: ${PROJECT_ID}${NC}"

# Configure Docker to use gcloud as credential helper
echo -e "${GREEN}Configuring Docker authentication...${NC}"
gcloud auth configure-docker --quiet

echo -e "${GREEN}Building Docker image...${NC}"
docker build -t ${IMAGE_NAME}:latest .

echo -e "${GREEN}Pushing image to Google Container Registry...${NC}"
docker push ${IMAGE_NAME}:latest

# Read environment variables from .env if available
if [ -f .env ]; then
  CIRCLE_API_KEY=$(grep "^CIRCLE_API_KEY=" .env | cut -d '=' -f2- | tr -d '"' || echo "")
  ENTITY_SECRET=$(grep "^ENTITY_SECRET=" .env | cut -d '=' -f2- | tr -d '"' || echo "")
  MCP_AUTH_ENABLED=$(grep "^MCP_AUTH_ENABLED=" .env | cut -d '=' -f2 | tr -d '"' || echo "true")
  MCP_AUTH_TOKEN=$(grep "^MCP_AUTH_TOKEN=" .env | cut -d '=' -f2 | tr -d '"' || echo "")
else
  CIRCLE_API_KEY="${CIRCLE_API_KEY:-}"
  ENTITY_SECRET="${ENTITY_SECRET:-}"
  MCP_AUTH_ENABLED="${MCP_AUTH_ENABLED:-true}"
  MCP_AUTH_TOKEN="${MCP_AUTH_TOKEN:-}"
fi

# Build env vars string
ENV_VARS="ENVIRONMENT=prod"
if [ -n "$CIRCLE_API_KEY" ]; then
  ENV_VARS="${ENV_VARS},CIRCLE_API_KEY=${CIRCLE_API_KEY}"
fi
if [ -n "$ENTITY_SECRET" ]; then
  ENV_VARS="${ENV_VARS},ENTITY_SECRET=${ENTITY_SECRET}"
fi
if [ -n "$MCP_AUTH_ENABLED" ]; then
  ENV_VARS="${ENV_VARS},MCP_AUTH_ENABLED=${MCP_AUTH_ENABLED}"
fi
if [ -n "$MCP_AUTH_TOKEN" ]; then
  ENV_VARS="${ENV_VARS},MCP_AUTH_TOKEN=${MCP_AUTH_TOKEN}"
fi

echo -e "${GREEN}Deploying to Cloud Run...${NC}"
echo -e "${YELLOW}Environment variables: ${ENV_VARS}${NC}"
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME}:latest \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 300 \
  --set-env-vars "${ENV_VARS}"

echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${YELLOW}Service URL:${NC}"
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'

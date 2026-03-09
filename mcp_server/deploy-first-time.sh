#!/bin/bash
# First-time deployment script with all environment variables

set -e

PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-omniclaw-mcp-server}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "Project ID: ${PROJECT_ID}"
echo "Building and deploying ${SERVICE_NAME}..."

# Build image
docker build -t ${IMAGE_NAME}:latest .

# Push image
docker push ${IMAGE_NAME}:latest

# Deploy with all environment variables from .env
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
  --set-env-vars \
    ENVIRONMENT=prod,\
    CIRCLE_API_KEY=TEST_API_KEY:90b965fbffbeaa23edf585dbd960bbf0:f3613cf4b1e9f06e839d4ae7da27091a,\
    ENTITY_SECRET=d05188532e6d3b4d2f9c8fc97b5138e727d4053d5ef02cb4486da52af9a432f2,\
    MCP_AUTH_ENABLED=true,\
    MCP_AUTH_TOKEN=9507b8047086f29f78dcdf3b188f52fedb2dfd831053c723901d328e00537277

echo "Deployment complete!"
echo "Service URL:"
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'

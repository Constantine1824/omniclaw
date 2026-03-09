# Google Cloud Run Deployment Guide

This guide walks you through deploying the OmniClaw MCP Server to Google Cloud Run.

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed and configured
3. **Docker** installed (for local builds)
4. **Project ID** in Google Cloud Platform

## Setup

### 1. Install Google Cloud SDK

```bash
# Install gcloud CLI (if not already installed)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Authenticate
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

### 2. Enable Required APIs

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com
```

### 3. Configure Environment Variables

Set secrets in Google Cloud Secret Manager or as Cloud Run environment variables:

```bash
# Set secrets in Secret Manager (recommended)
gcloud secrets create circle-api-key --data-file=- <<< "your_circle_api_key"
gcloud secrets create entity-secret --data-file=- <<< "your_entity_secret"
gcloud secrets create mcp-auth-token --data-file=- <<< "your_auth_token"
gcloud secrets create mcp-jwt-secret --data-file=- <<< "your_jwt_secret"
gcloud secrets create omniclaw-webhook-secret --data-file=- <<< "your_webhook_secret"
```

## ⚠️ Important: Set Environment Variables First

**Before deploying**, ensure you set the required environment variables. The application will fail to start in production mode if `CIRCLE_API_KEY` or `ENTITY_SECRET` are missing.

For initial testing, you can set `ENVIRONMENT=dev` to skip production validation.

## Deployment Methods

### Method 1: Using Deployment Script (Recommended)

```bash
# Make script executable
chmod +x deploy.sh

# Set environment variables
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
export SERVICE_NAME="omniclaw-mcp-server"

# Deploy
./deploy.sh
```

### Method 2: Using Cloud Build (Automated CI/CD)

```bash
# Submit build to Cloud Build
gcloud builds submit --config cloudbuild.yaml \
  --substitutions _SERVICE_NAME=omniclaw-mcp-server,_REGION=us-central1
```

### Method 3: Manual Deployment

```bash
# Build and push image
docker build -t gcr.io/YOUR_PROJECT_ID/omniclaw-mcp-server .
docker push gcr.io/YOUR_PROJECT_ID/omniclaw-mcp-server

# Deploy to Cloud Run with required environment variables
gcloud run deploy omniclaw-mcp-server \
  --image gcr.io/YOUR_PROJECT_ID/omniclaw-mcp-server \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --set-env-vars ENVIRONMENT=prod,CIRCLE_API_KEY=your_key,ENTITY_SECRET=your_secret
```

**Note:** Replace `your_key` and `your_secret` with actual values, or use Secret Manager (recommended).

## Configure Secrets

After deployment, attach secrets to your Cloud Run service:

```bash
gcloud run services update omniclaw-mcp-server \
  --region us-central1 \
  --update-secrets=CIRCLE_API_KEY=circle-api-key:latest,ENTITY_SECRET=entity-secret:latest,MCP_AUTH_TOKEN=mcp-auth-token:latest
```

Or set environment variables directly:

```bash
gcloud run services update omniclaw-mcp-server \
  --region us-central1 \
  --set-env-vars \
    ENVIRONMENT=prod,\
    CIRCLE_API_KEY=your_key,\
    ENTITY_SECRET=your_secret,\
    MCP_AUTH_ENABLED=true,\
    MCP_AUTH_TOKEN=your_token,\
    OMNICLAW_DAILY_BUDGET=1000.0,\
    OMNICLAW_HOURLY_BUDGET=200.0,\
    OMNICLAW_TX_LIMIT=500.0
```

**Note:** The `deploy.sh` script automatically reads `MCP_AUTH_ENABLED` and `MCP_AUTH_TOKEN` from your `.env` file if it exists.

## Verify Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe omniclaw-mcp-server \
  --region us-central1 \
  --format 'value(status.url)')

# Test health endpoint
curl ${SERVICE_URL}/health

# Test MCP endpoint (with auth)
curl -X POST ${SERVICE_URL}/mcp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

## Configuration Options

### Resource Limits

Adjust in `cloudbuild.yaml` or deployment command:

- **Memory**: `--memory 512Mi` (512Mi, 1Gi, 2Gi, 4Gi, 8Gi)
- **CPU**: `--cpu 1` (1, 2, 4, 6, 8)
- **Timeout**: `--timeout 300` (seconds, max 3600)
- **Min Instances**: `--min-instances 0` (0 for scale-to-zero, 1+ for always-on)
- **Max Instances**: `--max-instances 10` (auto-scaling limit)

### Environment Variables

Required for production:
- `ENVIRONMENT=prod`
- `CIRCLE_API_KEY`
- `ENTITY_SECRET`
- `MCP_AUTH_ENABLED=true` (enables authentication)
- `MCP_AUTH_TOKEN` or `MCP_JWT_SECRET` (required if `MCP_AUTH_ENABLED=true`)
- `OMNICLAW_WEBHOOK_SECRET` (if using webhooks)
- `OMNICLAW_MERCHANT_ID` (if using webhooks)

Optional guard policies:
- `OMNICLAW_DAILY_BUDGET=1000.0`
- `OMNICLAW_HOURLY_BUDGET=200.0`
- `OMNICLAW_TX_LIMIT=500.0`
- `OMNICLAW_RATE_LIMIT_PER_MIN=5`
- `OMNICLAW_WHITELISTED_RECIPIENTS=addr1,addr2`

## Monitoring

### View Logs

```bash
gcloud run services logs read omniclaw-mcp-server \
  --region us-central1 \
  --limit 50
```

### View Metrics

```bash
# Open Cloud Console
gcloud run services describe omniclaw-mcp-server \
  --region us-central1
```

## Troubleshooting

### Container failed to start and listen on PORT

**Error:** "The user-provided container failed to start and listen on the port defined provided by the PORT=8080 environment variable"

**Solutions:**
1. **Check application logs:**
   ```bash
   gcloud run services logs read omniclaw-mcp-server --region us-central1 --limit 100
   ```

2. **Verify required environment variables are set:**
   - In production (`ENVIRONMENT=prod`), the app requires:
     - `CIRCLE_API_KEY`
     - `ENTITY_SECRET`
   - If these are missing, the app will fail to start during validation

3. **Set environment variables before deployment:**
   ```bash
   gcloud run services update omniclaw-mcp-server \
     --region us-central1 \
     --set-env-vars ENVIRONMENT=prod,CIRCLE_API_KEY=your_key,ENTITY_SECRET=your_secret
   ```

4. **For initial testing, use dev mode:**
   ```bash
   gcloud run services update omniclaw-mcp-server \
     --region us-central1 \
     --set-env-vars ENVIRONMENT=dev
   ```

5. **Check that PORT is being read correctly:**
   - The startup script (`start.py`) automatically reads the PORT environment variable
   - Cloud Run sets PORT automatically (usually 8080)
   - No manual PORT configuration needed

### Service won't start

1. Check logs: `gcloud run services logs read omniclaw-mcp-server --region us-central1`
2. Verify environment variables are set correctly
3. Check that secrets are accessible
4. Ensure PORT environment variable is available (Cloud Run sets this automatically)
5. **Common issue:** Missing `CIRCLE_API_KEY` or `ENTITY_SECRET` in production mode causes startup failure

### Authentication errors

1. Verify `MCP_AUTH_TOKEN` or `MCP_JWT_SECRET` is set
2. Check that `MCP_AUTH_ENABLED=true` (default)
3. Ensure Authorization header is included in requests

### Payment API errors

1. Verify `CIRCLE_API_KEY` and `ENTITY_SECRET` are correct
2. Check Circle API status
3. Review payment guard policies

## Cost Optimization

- Use **scale-to-zero** (`--min-instances 0`) for development
- Set **min-instances 1** only if you need always-on
- Adjust **memory** based on actual usage (start with 512Mi)
- Use **CPU throttling** for non-CPU intensive workloads
- Monitor usage in Cloud Console

## Security Best Practices

1. **Use Secret Manager** for sensitive values (API keys, tokens)
2. **Enable authentication** (`MCP_AUTH_ENABLED=true`)
3. **Use HTTPS only** (Cloud Run provides this automatically)
4. **Set guard policies** to limit payment amounts
5. **Monitor access logs** regularly
6. **Rotate secrets** periodically

## Next Steps

- Set up **Cloud Build triggers** for automatic deployments
- Configure **custom domain** mapping
- Set up **alerting** for errors and high latency
- Enable **Cloud CDN** for better performance
- Configure **VPC connector** if accessing private resources

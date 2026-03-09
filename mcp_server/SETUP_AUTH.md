# Setting Up Authentication Bearer Token

## What is the Bearer Token?

The bearer token is a **custom API key** you create to secure your FastMCP server. It's not provided by any external service - **you generate it yourself**.

## Option 1: Generate a Secure Token (Recommended)

### Using Python

```bash
python3 << 'EOF'
import secrets
token = secrets.token_urlsafe(32)
print(f"MCP_AUTH_TOKEN={token}")
EOF
```

### Using OpenSSL

```bash
openssl rand -hex 32
```

### Using /dev/urandom

```bash
head -c 32 /dev/urandom | base64 | tr -d '\n'
```

## Option 2: Use a Simple Token (For Testing Only)

For development/testing, you can use any string:

```bash
# Example (NOT secure for production!)
MCP_AUTH_TOKEN=my_test_token_12345
```

## Configuration Steps

### Step 1: Create/Edit `.env` File

Create a `.env` file in the project root (if it doesn't exist):

```bash
cd /home/arslan/Documents/hackathon/omni_agent_pay/mcp_server
touch .env
```

### Step 2: Add Token to `.env`

Add your generated token to `.env`:

```bash
# FastMCP Authentication
MCP_AUTH_ENABLED=true
MCP_AUTH_TOKEN=your_generated_token_here
MCP_REQUIRE_AUTH=true
```

**Example `.env` file:**

```bash
# Payment Configuration
CIRCLE_API_KEY=your_circle_api_key
ENTITY_SECRET=your_entity_secret
ENVIRONMENT=dev

# FastMCP Authentication
MCP_AUTH_ENABLED=true
MCP_AUTH_TOKEN=45f6c5e6ae8b9c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
MCP_REQUIRE_AUTH=true

# Guard Policies
OMNICLAW_DAILY_BUDGET=1000.0
OMNICLAW_HOURLY_BUDGET=200.0
OMNICLAW_TX_LIMIT=500.0
OMNICLAW_RATE_LIMIT_PER_MIN=5
```

### Step 3: Restart Server

After updating `.env`, restart your server:

```bash
# Stop the server (Ctrl+C)
# Then restart
uvicorn app.main:app --reload
```

### Step 4: Use Token in Requests

Use the token in your curl commands:

```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer your_generated_token_here" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

## Quick Setup Script

Run this to generate and add token to `.env`:

```bash
#!/bin/bash
# Generate token
TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Add to .env (or create if doesn't exist)
if ! grep -q "MCP_AUTH_TOKEN" .env 2>/dev/null; then
    echo "" >> .env
    echo "# FastMCP Authentication" >> .env
    echo "MCP_AUTH_ENABLED=true" >> .env
    echo "MCP_AUTH_TOKEN=$TOKEN" >> .env
    echo "MCP_REQUIRE_AUTH=true" >> .env
    echo "✅ Token added to .env: $TOKEN"
else
    echo "⚠️  MCP_AUTH_TOKEN already exists in .env"
    echo "Current token: $(grep MCP_AUTH_TOKEN .env | cut -d '=' -f2)"
fi
```

Save as `setup_token.sh`, make executable (`chmod +x setup_token.sh`), and run it.

## Option 3: Disable Authentication (Development Only)

For local development/testing, you can temporarily disable auth:

**In `.env`:**
```bash
MCP_AUTH_ENABLED=false
MCP_REQUIRE_AUTH=false
```

Then restart server and use requests **without** Authorization header:

```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

⚠️ **Warning**: Never disable auth in production!

## Verify Token is Set

Check if token is configured:

```bash
python3 << 'EOF'
from app.core.config import settings
if settings.MCP_AUTH_TOKEN:
    token = settings.MCP_AUTH_TOKEN.get_secret_value()
    print(f"✅ Token configured: {token[:20]}... (length: {len(token)})")
else:
    print("❌ Token NOT configured!")
EOF
```

## Using Environment Variable Directly

You can also set it as an environment variable:

```bash
export MCP_AUTH_TOKEN="your_token_here"
uvicorn app.main:app --reload
```

## Multiple Clients / Different Tokens

If you need different tokens for different clients, you can:

1. **Use JWT tokens** - Set `MCP_JWT_SECRET` and issue JWTs
2. **Rotate tokens** - Change `MCP_AUTH_TOKEN` in `.env` and restart
3. **Use OAuth** - Configure OAuth provider (see FastMCP docs)

## Security Best Practices

1. **Use long, random tokens** (32+ characters)
2. **Never commit `.env` to git** (add to `.gitignore`)
3. **Rotate tokens regularly** in production
4. **Use different tokens** for dev/staging/prod
5. **Store tokens securely** (use secrets manager in production)

## Troubleshooting

### Token Not Working?

1. Check `.env` file exists and has `MCP_AUTH_TOKEN=...`
2. Verify no extra spaces: `MCP_AUTH_TOKEN=token` (not `MCP_AUTH_TOKEN= token`)
3. Restart server after changing `.env`
4. Check server logs for authentication errors

### Get Current Token

```bash
# From .env file
grep MCP_AUTH_TOKEN .env | cut -d '=' -f2

# Or from Python
python3 -c "from app.core.config import settings; print(settings.MCP_AUTH_TOKEN.get_secret_value() if settings.MCP_AUTH_TOKEN else 'Not set')"
```

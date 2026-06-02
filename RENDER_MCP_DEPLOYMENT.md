# Deploying MCP Server to Render

This guide explains how to deploy the MCP (Model Context Protocol) server as a **separate service** on Render, alongside your main backend API.

## Architecture

```
┌─────────────────────────────────────────────┐
│           Render Dashboard                  │
├──────────────────┬──────────────────────────┤
│                  │                          │
│  Backend API     │    MCP Server            │
│  (port 8080)     │    (port 8080)           │
│  src.api.server  │    src.mcp.mcp_server    │
│                  │                          │
│  parking-chatbot │  parking-mcp-server      │
└──────────────────┴──────────────────────────┘
```

## Prerequisites

- GitHub repo with your code
- Render account connected to GitHub
- Existing backend service running (`parking-chatbot`)

## Step 1: Verify `render.yaml`

The `render.yaml` file already includes both services:

```yaml
services:
  - type: web
    name: parking-chatbot           # Backend API
    startCommand: uvicorn src.api.server:app ...
    
  - type: web
    name: parking-mcp-server        # MCP Server (NEW)
    startCommand: uvicorn src.mcp.mcp_server:mcp_app ...
```

## Step 2: Set Environment Variables in Render

### For `parking-mcp-server` service:

1. Open Render Dashboard → Your Project
2. Click on **`parking-mcp-server`** service (or create it if not auto-detected)
3. Go to **Environment** tab
4. Add these variables:

| Variable | Value | Notes |
|----------|-------|-------|
| `MCP_API_KEY` | `mcp-parksmart-secret-key-2026` | Change to a strong secret in production |
| `PYTHON_VERSION` | `3.13.0` | Already set in render.yaml |

### For `parking-chatbot` (Backend) service:

Update to use the MCP server URL:

| Variable | Value | Example |
|----------|-------|---------|
| `MCP_SERVER_URL` | Render MCP service URL | `https://parking-mcp-server-xxx.onrender.com` |
| `MCP_API_KEY` | Same as MCP service | `mcp-parksmart-secret-key-2026` |

Find the MCP service URL in Render:
- Go to **`parking-mcp-server`** → **Settings**
- Copy the **Render URL** (looks like `https://parking-mcp-server-xxx.onrender.com`)

## Step 3: Deploy

### Option A: Auto-deploy from GitHub (Recommended)

1. Push your changes (including updated `render.yaml` and `.env`):
```bash
git add render.yaml .env
git commit -m "Add MCP server to Render deployment"
git push origin main
```

2. Render auto-detects services in `render.yaml` and deploys them

3. Go to Render Dashboard → Your Project
   - You should see both services listed
   - Each gets its own URL and deployment logs

### Option B: Manual deploy

1. In Render Dashboard, click **+ New Service**
2. Select **Web Service**
3. Connect your repository
4. Configure:
   - **Name:** `parking-mcp-server`
   - **Environment:** Python 3.13
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn src.mcp.mcp_server:mcp_app --host 0.0.0.0 --port $PORT --workers 1`
   - **Health Check Path:** `/mcp/health`

5. Add environment variables (see Step 2)
6. Deploy

## Step 4: Verify Deployment

### Check MCP Server Health

```bash
curl https://parking-mcp-server-xxx.onrender.com/mcp/health
```

Expected response:
```json
{"status": "healthy"}
```

### Check MCP Tools Available

```bash
curl -X POST https://parking-mcp-server-xxx.onrender.com/mcp/tools/list \
  -H "X-MCP-API-KEY: mcp-parksmart-secret-key-2026" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Expected: List of available tools (e.g., `write_reservation_to_file`)

### Check Backend can reach MCP

Test from your backend:
```bash
# SSH to backend or use logs
curl https://parking-mcp-server-xxx.onrender.com/mcp/health \
  -H "X-MCP-API-KEY: mcp-parksmart-secret-key-2026"
```

## Step 5: Update Backend Configuration

Once MCP server URL is live on Render, update your backend `.env`:

```env
MCP_SERVER_URL=https://parking-mcp-server-xxx.onrender.com
MCP_API_KEY=mcp-parksmart-secret-key-2026
```

Then restart the backend service in Render.

## Troubleshooting

### MCP Server won't start

Check logs in Render:
- Service → **Logs**
- Look for import errors or missing dependencies

**Solution:** Ensure `src/mcp/mcp_server.py` and dependencies are in `requirements.txt`

### Backend can't reach MCP server

- Verify `MCP_SERVER_URL` is set correctly in backend env vars
- Check MCP server is running (visit health endpoint)
- Verify `MCP_API_KEY` matches between services

### "403 Forbidden" from MCP server

- Check `X-MCP-API-KEY` header matches `MCP_API_KEY` env var
- Example (correct):
  ```bash
  curl https://parking-mcp-server-xxx.onrender.com/mcp/tools/list \
    -H "X-MCP-API-KEY: mcp-parksmart-secret-key-2026"
  ```

## Local Testing

To test locally before deploying to Render:

### Terminal 1: Start Backend API
```bash
python -m uvicorn src.api.server:app --reload --port 8000
```

### Terminal 2: Start MCP Server
```bash
python -m uvicorn src.mcp.mcp_server:mcp_app --reload --port 8001
```

### Terminal 3: Test MCP
```bash
python scripts/test_mcp.py
# or use curl to call /mcp/tools/list
```

## Service Scaling

If MCP server gets slow, you can:
- Upgrade the Render instance tier (Settings → Instance Type)
- Enable auto-scaling (if using Render Pro)
- Add a background worker for file writes (advanced)

---

**Questions?** Check `src/mcp/mcp_server.py` and `src/mcp/mcp_client.py` for implementation details.

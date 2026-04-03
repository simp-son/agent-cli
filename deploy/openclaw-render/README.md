# Deploying Nunchi OpenClaw Agent to Render

This guide helps you deploy the Nunchi trading agent as an OpenClaw agent on Render.

## Prerequisites

1. A Render account
2. Hyperliquid wallet private key
3. AI API key (Anthropic, OpenAI, etc.)
4. Optional: Telegram bot token for messaging

## Deployment Steps

### 1. Connect Repository to Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "Blueprint"
3. Connect your GitHub repository (`Nunchi-trade/agent-cli`)
4. Render will detect the `render.yaml` file

### 2. Configure Environment Variables

In the Render dashboard, set these environment variables as secrets:

**Required:**
- `HL_PRIVATE_KEY`: Your Hyperliquid wallet private key
- `AI_API_KEY`: Your AI provider API key or OAuth token
  - For Anthropic/Claude: API key (sk-ant-...) or OAuth token (sk-ant-oauth-...)
  - For OpenAI: API key
  - For Google/Gemini: API key
  - For OpenRouter: API key

**Optional:**
- `TELEGRAM_BOT_TOKEN`: For Telegram bot integration
- `HL_TESTNET`: Set to `false` for mainnet (default: `true` for testnet)
- `AI_PROVIDER`: `anthropic`, `openai`, `gemini`, etc. (default: `anthropic`)
- `RUN_MODE`: Trading mode - `apex`, `pulse`, `radar`, etc. (default: `apex`)
- `INSTRUMENT`: Trading instrument (default: `ETH-PERP`)

### 3. Configure Persistent Disk

The `render.yaml` includes a 10GB persistent disk mounted at `/data` for storing OpenClaw state and workspace data.

### 4. Deploy

Click "Create Blueprint" to deploy. The service will:
1. Build the Docker image
2. Run the bootstrap script to configure OpenClaw
3. Start the OpenClaw gateway
4. Serve the agent at the provided URL

## Troubleshooting

### Bot Not Responding

If the bot doesn't reply to messages:

1. **Check Health Endpoint**: Visit `https://your-service.onrender.com/health`
   - Should return JSON with `status: "ok"`
   - `gateway_alive: true`
   - `mcp_alive: true` (MCP server should be running)

2. **Check Logs**: In Render dashboard, view service logs
   - Look for `[bootstrap] Configuration complete`
   - Look for `[mcp] Starting MCP server...`
   - Look for `[gateway] Starting OpenClaw gateway...`
   - Look for successful MCP server connection

3. **Verify Environment Variables**:
   - `AI_API_KEY` must be set and valid
   - `HL_PRIVATE_KEY` must be set
   - Check AI provider compatibility

4. **Test MCP Server Directly**:
   ```bash
   # SSH into your Render service or check logs for MCP server output
   # Look for lines like "[mcp] Listening on port 18790" or similar
   ```

5. **Test Trading Tools**:
   ```bash
   curl https://your-service.onrender.com/api/status
   curl https://your-service.onrender.com/api/strategies
   ```

### Common Issues

- **MCP Server Not Starting**: Check if Python dependencies are installed correctly
- **OpenClaw Configuration**: The bootstrap script generates `openclaw.json` with MCP server config
- **Port Conflicts**: Ensure ports 18789 (gateway) and 18790 (MCP) are available
- **Memory Issues**: OpenClaw agents need sufficient memory (use at least 1GB RAM)

### Manual Testing

You can test the agent directly:

```bash
# Check status
curl https://your-service.onrender.com/status

# Check API status
curl https://your-service.onrender.com/api/status

# Check strategies
curl https://your-service.onrender.com/api/strategies
```

## Architecture

The deployment runs:
- **Express server** (port 10000) - Health checks and API endpoints
- **OpenClaw gateway** (internal port 18789) - Agent runtime
- **Nunchi MCP server** - Trading tools and strategies
- **Persistent storage** (/data) - Configuration and workspace

## Security Notes

- Never commit private keys to the repository
- Use Render's secret management for sensitive environment variables
- The agent has access to trading functions - monitor activity closely
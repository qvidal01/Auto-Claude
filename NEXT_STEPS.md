# Auto-Claude: AI Server Integration — Next Steps

**Date:** 2026-03-12
**AI Server:** 192.168.0.234 (ubuntuai)
**Status:** Backend `.env` configured, server unreachable from current network

---

## Current Configuration (already in `.env`)

| Service | Setting | Value |
|---------|---------|-------|
| Graphiti Memory | `GRAPHITI_ENABLED` | `true` |
| Graphiti LLM | `GRAPHITI_LLM_PROVIDER` | `ollama` |
| Graphiti Embedder | `GRAPHITI_EMBEDDER_PROVIDER` | `ollama` |
| Ollama Base URL | `OLLAMA_BASE_URL` | `http://192.168.0.234:11434` |
| Memory LLM Model | `OLLAMA_LLM_MODEL` | `llama3.2:3b` |
| Embedding Model | `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text:latest` |
| Coder Model | `OLLAMA_CODER_MODEL` | `qwen2.5-coder:32b-instruct` |
| Planner Model | `OLLAMA_PLANNER_MODEL` | `llama3.3:70b` |
| Reviewer Model | `OLLAMA_REVIEWER_MODEL` | `qwen2.5-coder:32b-instruct` |

## Step 1: Expose Ollama via Cloudflare Tunnel (Remote Access)

SSH into the AI server (from LAN or mesh) and create a Cloudflare tunnel so Ollama is reachable from any network:

```bash
ssh dunkin@192.168.0.234

# Add Ollama to an existing Cloudflare tunnel config, or create a new one:
# In /etc/cloudflare/config.yml, add:
#   - hostname: ollama.aiqso.io
#     service: http://localhost:11434

# Then reload the tunnel:
cloudflared tunnel run <tunnel-name>
```

After the tunnel is up, update `.env`:
```
OLLAMA_BASE_URL=https://ollama.aiqso.io
```

## Step 2: Verify Ollama Models Are Pulled

Ensure the required models are available on the AI server:

```bash
ssh dunkin@192.168.0.234
ollama list
```

Required models:
- `llama3.2:3b` — Graphiti memory LLM
- `nomic-embed-text:latest` — Graphiti embeddings (768 dim)
- `qwen2.5-coder:32b-instruct` — Code generation & review
- `llama3.3:70b` — Planning agent

Pull any missing:
```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text:latest
ollama pull qwen2.5-coder:32b-instruct
ollama pull llama3.3:70b
```

## Step 3: Verify Graphiti / LadybugDB Memory

Auto-Claude uses LadybugDB (embedded graph DB) for its memory system — no Neo4j/Docker required. Once Ollama is reachable:

```bash
cd ~/projects/auto-claude
source apps/backend/.venv/bin/activate
python -c "
from apps.backend.integrations.graphiti.memory_client import MemoryClient
client = MemoryClient()
print('Graphiti memory connected:', client is not None)
"
```

Memory data stored locally at `~/.auto-claude/memories/` by default.

## Step 4: Test the Full Stack

```bash
# 1. Verify Ollama connectivity
curl http://192.168.0.234:11434/api/tags  # or https://ollama.aiqso.io/api/tags

# 2. Launch Auto-Claude Electron app
cd ~/projects/auto-claude && npm run dev

# 3. In the app:
#    - Go to Settings > Memory and verify Graphiti shows "Connected"
#    - Open a terminal agent and confirm it can generate code
#    - Create a test task to verify the planner/coder/reviewer pipeline
```

## Step 5: Optional — Connect Additional AI Server Services

Check what else is running on the AI server that Auto-Claude could use:

```bash
ssh dunkin@192.168.0.234 "docker ps --format 'table {{.Names}}\t{{.Ports}}'"
```

Potential integrations:
| Service | Use in Auto-Claude | Config |
|---------|-------------------|--------|
| **Grafana** (grafana.aiqso.io) | Monitor Ollama/agent performance | Dashboard only |
| **n8n** (192.168.0.232) | Trigger workflows on task completion | Webhook in `.env` |
| **AI Gateway** (ai-gateway.aiqso.io) | Route API calls, add caching/logging | Set as `ANTHROPIC_BASE_URL` |

## Step 6: Fork Maintenance

Keep the fork synced with upstream:

```bash
cd ~/projects/auto-claude
git fetch origin           # upstream (AndyMik90)
git merge origin/main      # merge upstream changes
git push fork main         # push to your fork
```

---

## Quick Connectivity Test Script

Save and run when on LAN or after tunnel setup:

```bash
#!/bin/bash
echo "Testing AI Server connectivity..."
curl -sf http://192.168.0.234:11434/api/tags > /dev/null && echo "✓ Ollama reachable (LAN)" || echo "✗ Ollama not reachable (LAN)"
curl -sf https://ollama.aiqso.io/api/tags > /dev/null 2>&1 && echo "✓ Ollama reachable (tunnel)" || echo "✗ Ollama not reachable (tunnel)"
echo ""
echo "Required models:"
curl -sf http://192.168.0.234:11434/api/tags 2>/dev/null | python3 -c "
import sys,json
try:
    data=json.load(sys.stdin)
    models=[m['name'] for m in data.get('models',[])]
    for need in ['llama3.2:3b','nomic-embed-text:latest','qwen2.5-coder:32b-instruct','llama3.3:70b']:
        status='✓' if any(need in m for m in models) else '✗ MISSING'
        print(f'  {status} {need}')
except: print('  Could not check models')
"
```

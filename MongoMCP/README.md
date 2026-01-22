# Dynamic MongoDB MCP Server (MongoMCP)

A configurable **Model Context Protocol (MCP)** server that dynamically loads tool definitions from MongoDB (no code changes required to add/modify tools). This repo also includes an example **MCP “bridge”** you can register in **Claude Desktop** to call your MCP server from Claude.

> This README intentionally **does not use AWS** (no Secrets Manager / ECR / EKS).  
> Container build/push uses **Podman** and **quay.io**.

---

## What you’ll build

1. **MongoDB-backed tool registry** (`mcp_config.mcp_tools.json`) that defines tools like vector search, text search, aggregation queries, etc.
2. An **MCP server** (FastAPI/uvicorn) that:
   - loads an active tool config from MongoDB
   - exposes endpoints (e.g. `/tools_config`, `/vectorize`, etc.)
   - validates requests with a **JWT** signed by an agent private key (PVK) stored in MongoDB
3. Optional: an **MCP client bridge** for Claude Desktop that calls the server.

---

## Prerequisites

### All platforms
- Git
- **MongoDB Atlas** (or MongoDB compatible deployment) with:
  - a database for MCP config (e.g. `mcp_config`)
  - your target dataset(s) (e.g. `sample_airbnb.listingsAndReviews`)
- OpenSSL (for generating your demo PVK)
- A container runtime: **Podman** (recommended)

### Python
- Python **3.12** (recommended)
- `pyenv` (recommended) to manage Python versions

---

## Install prerequisites

### macOS (Apple Silicon or Intel)

#### 1) Install Homebrew (if needed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2) Install pyenv + build deps
```bash
brew update
brew install pyenv openssl readline sqlite3 xz zlib tcl-tk
```

#### 3) Install Podman
```bash
brew install --cask podman-desktop
# or CLI-only:
brew install podman
```

Initialize Podman VM (required on macOS):
```bash
podman machine init
podman machine start
```

---

### Ubuntu Linux

#### 1) Install build deps + utilities
```bash
sudo apt-get update
sudo apt-get install -y \
  git curl build-essential \
  libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev \
  libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
  openssl
```

#### 2) Install pyenv
```bash
curl https://pyenv.run | bash
```

Add pyenv init to your shell (bash example):
```bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc
```

#### 3) Install Podman
```bash
sudo apt-get install -y podman
```

---

## Install Python 3.12 with pyenv

> If you already have Python 3.12 installed system-wide, you can skip pyenv and use `python3.12`.

```bash
pyenv install 3.12.8
pyenv local 3.12.8
python -V
```

---

## Repo layout

- `mongo_mcp.py` (or equivalent): MCP server implementation
- `mcp_config/`
  - `mcp_tools`: tool configuration docs (JSON)
  - `agent_identities`: agent auth records (JSON)
  - `llm_history`: optional conversation history store
- `mcpclient/` or `mcpclient/mcp_bridge_airbnb.py`: example MCP bridge for Claude Desktop

---

## 1) MongoDB setup (dynamic configuration)

The server loads tool definitions from MongoDB. Create these **three collections** (example names shown):

1. `mcp_config.mcp_tools` — tool config documents
2. `mcp_config.agent_identities` — agent auth records (PVK + agent_key)
3. `mcp_config.llm_history` — optional persisted conversation history

This matches the “Dynamic Configuration Setup” described in the original README. fileciteturn13file8L31-L41

### 1.1 Load tool configuration docs

Import `mcp_config/mcp_tools.json` into `mcp_config.mcp_tools` (Atlas UI or `mongoimport`).

Example with `mongoimport`:
```bash
mongoimport \
  --uri "mongodb+srv://<user>:<pass>@<cluster-host>/" \
  --db mcp_config \
  --collection mcp_tools \
  --file mcp_config/mcp_tools.json \
  --jsonArray
```

> Make sure the tool config you want is marked **active: true** in the JSON.

### 1.2 Create an agent identity (PVK + agent_key)

Generate a demo secret:
```bash
openssl rand -base64 32
```

The original README calls this PVK out explicitly for `agent_identities`. fileciteturn13file8L39-L44

Insert an agent record into `mcp_config.agent_identities`:
```json
{
  "pvk": "YOUR_GENERATED_SECRET",
  "agent_name": "console_chatbot",
  "agent_key": "console-chatbot",
  "scope": ["vectorize", "tools:read", "llm:invoke"]
}
```

Important notes:
- `agent_key` is what the client puts into the JWT header as `api_key`
- `pvk` is the shared secret used to sign/verify HS256 JWTs
- `agent_name` is checked against the token payload by the server (keep them consistent)

---

## 2) Run the MCP server locally (Python)

### 2.1 Create and activate a virtualenv
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

(These steps were in the original README; we’re keeping the workflow but updating the dependencies and removing AWS.) fileciteturn13file0L1-L14

### 2.2 Configure runtime environment

Set your MongoDB connection details and config selectors however your server expects them.

**Common pattern (example):**
```bash
export MONGODB_URI="mongodb+srv://<user>:<pass>@<cluster-host>/?retryWrites=true&w=majority"
export MCP_CONFIG_DB="mcp_config"
export MCP_TOOLS_COLLECTION="mcp_tools"
export MCP_AGENT_COLLECTION="agent_identities"
export MCP_HISTORY_COLLECTION="llm_history"
```

> If your code uses different variable names, update these accordingly (or document the actual names in `settings.py` / your server module).

### 2.3 Start the server
The original README uses FastAPI’s runner: fileciteturn13file0L38-L44

```bash
fastapi run mongo_mcp.py
```

By default the server listens on port `8000`. Confirm it’s alive:
```bash
curl -s http://127.0.0.1:8000/health || true
curl -s http://127.0.0.1:8000/tools_config
```

---

## 3) Auth: generate a JWT for API calls

Your server expects:
- JWT header contains: `api_key` = the `agent_key` from MongoDB
- JWT payload contains: at minimum `agent_name` (and optionally `scope`, `exp`, etc.)
- JWT is signed with HS256 using `pvk`

Example generator (`gen_token.py`):

```python
import time
import jwt

PVK = "YOUR_PVK_FROM_MONGODB"
AGENT_KEY = "console-chatbot"
AGENT_NAME = "console_chatbot"

payload = {
    "agent_key": AGENT_KEY,
    "agent_name": AGENT_NAME,
    "scope": ["vectorize", "tools:read", "llm:invoke"],
    "iat": int(time.time()),
    "exp": int(time.time()) + 3600,
}

headers = {"alg": "HS256", "typ": "JWT", "api_key": AGENT_KEY}

print(jwt.encode(payload, PVK, algorithm="HS256", headers=headers))
```

Use it:
```bash
export AUTH_TOKEN="$(python gen_token.py)"
curl -s -i http://127.0.0.1:8000/tools_config \
  -H "Authorization: Bearer $AUTH_TOKEN"
```

---

## 4) Containerize with Podman (build + run)

The original README included Docker build/run instructions. fileciteturn13file0L45-L51  
We’ll do the same with **Podman**.

### 4.1 Build the image
```bash
podman build -t mongodb-vector-mcp:latest .
```

### 4.2 Run the container locally
```bash
podman run --rm -p 8000:8000 \
  -e MONGODB_URI="$MONGODB_URI" \
  -e MCP_CONFIG_DB="mcp_config" \
  -e MCP_TOOLS_COLLECTION="mcp_tools" \
  -e MCP_AGENT_COLLECTION="agent_identities" \
  -e MCP_HISTORY_COLLECTION="llm_history" \
  mongodb-vector-mcp:latest
```

---

## 5) Push to quay.io

### 5.1 Login
```bash
podman login quay.io
```

### 5.2 Tag
```bash
export QUAY_REPO="quay.io/<your-username>/mongodb-vector-mcp"
podman tag mongodb-vector-mcp:latest "${QUAY_REPO}:latest"
```

### 5.3 Push
```bash
podman push "${QUAY_REPO}:latest"
```

---

## 6) Use with Claude Desktop (MCP client bridge)

Claude Desktop doesn’t connect directly to an arbitrary HTTP MCP server; instead, you register an **MCP server process** (your “bridge”) that Claude can start locally. That bridge can then call your HTTP server.

### 6.1 Example bridge script

Your bridge only needs:
- `UPSTREAM_BASE_URL` (where your MCP server is running)
- `AUTH_TOKEN` (JWT)

Example skeleton:
```python
import os
import httpx
from mcp.server.fastmcp import FastMCP

UPSTREAM = os.environ.get("UPSTREAM_BASE_URL", "http://127.0.0.1:8000")
TOKEN = os.environ.get("AUTH_TOKEN")

mcp = FastMCP("mongodb-vector-mcp-bridge")

def _headers():
    if not TOKEN:
        raise RuntimeError("AUTH_TOKEN env var is required (JWT)")
    return {"Authorization": f"Bearer {TOKEN}"}

@mcp.tool()
def airbnb_search(payload: dict) -> dict:
    url = f"{UPSTREAM}/vectorize"
    r = httpx.post(url, json=payload, headers=_headers(), timeout=60)
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    mcp.run()
```

> This script runs on your laptop (macOS/Ubuntu). It does **not** have to live inside the server container.  
> Treat it like an MCP “adapter” process for Claude Desktop.

### 6.2 Register the bridge in Claude Desktop

Edit Claude Desktop config:

- macOS: `~/Library/Application Support/Claude/config.json`
- Ubuntu: `~/.config/Claude/config.json` (path may vary by install)

Add an entry under `mcpServers`:

```json
{
  "mcpServers": {
    "mongodb-vector-mcp-airbnb": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["/path/to/mcp_bridge_airbnb.py"],
      "env": {
        "UPSTREAM_BASE_URL": "http://127.0.0.1:8000",
        "AUTH_TOKEN": "YOUR_JWT_HERE"
      }
    }
  }
}
```

Restart Claude Desktop.

### 6.3 Verify tool availability
In a new chat, ask Claude something like:

> “List the available tools.”

You should see your bridge tool(s) (e.g. `airbnb_search`) become available.

---

## Notes / troubleshooting

- **401 Invalid authentication credentials**
  - Confirm your token is signed with the **same PVK** stored in MongoDB for that `agent_key`
  - Confirm the JWT **header** contains `api_key` with the correct value
  - Confirm the JWT **payload** has `agent_name` that matches the MongoDB record
- **macOS Podman networking**
  - Podman on macOS runs in a VM. Use `podman machine start` and ensure port forwarding is working.
- **Rotate tokens**
  - Use short-lived JWTs (e.g. 1 hour) and re-export `AUTH_TOKEN` when needed.

---

## What changed vs the original README

- Removed AWS-specific setup (`AWS_REGION`, `MONGO_CREDS`, ECR, EKS/Terraform). fileciteturn13file0L16-L23
- Switched container workflow from **Docker** to **Podman** and registry from **ECR** to **quay.io**. fileciteturn13file0L45-L73
- Added a practical **Claude Desktop MCP bridge** flow (how Claude actually discovers tools).

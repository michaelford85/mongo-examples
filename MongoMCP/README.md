# MongoMCP – MongoDB-backed MCP Server (GHCR)

This document explains how to build, publish, and run **MongoMCP** as a container image hosted on **GitHub Container Registry (GHCR)**, using **Podman** (recommended) or Docker-compatible tooling.

The goal is that **someone new** can follow this end‑to‑end and:

- Build the container
- Push it to GHCR
- Run the MCP server locally
- Connect to it from an MCP client (e.g. Claude Desktop)

---

## What is MongoMCP?

MongoMCP is a **Model Context Protocol (MCP) server** backed by MongoDB. It:

- Exposes MCP tools over stdio and HTTP
- Uses MongoDB for:
  - Tool configuration
  - Agent identities
  - Authorization (JWT bearer tokens)
  - Conversation history
- Acts as a backend for agentic workflows (Claude, IDEs, custom clients)

Typical architecture:

```
Claude Desktop / MCP Client
        │
        │  (stdio MCP)
        ▼
MongoMCP (container)
        │
        │  MongoDB Atlas
        ▼
MongoDB collections
```

---

## Prerequisites

### Common (macOS + Ubuntu)

- Git
- A GitHub account
- Access to a MongoDB cluster (Atlas or self‑hosted)

---

### macOS prerequisites

```bash
# Install Homebrew (if needed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Podman
brew install podman

# Initialize Podman VM
podman machine init
podman machine start
```

Verify:

```bash
podman info
```

---

### Ubuntu Linux prerequisites

```bash
sudo apt update
sudo apt install -y podman uidmap

# Enable user namespaces
sudo sysctl -w kernel.unprivileged_userns_clone=1
```

Verify:

```bash
podman info
```

---

## Repository Layout (relevant parts)

```
MongoMCP/
├── MongoMCP/
│   ├── mongo_mcp.py
│   ├── MongoMCPMiddleware.py
│   └── ...
├── Containerfile
├── requirements.txt
└── README.md
```

---

## Containerfile (OCI compatible)

MongoMCP uses a **Containerfile** (works with Podman and Docker):

```Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY MongoMCP ./MongoMCP

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "MongoMCP.mongo_mcp"]
```

---

## Build the image locally

From the `MongoMCP/` directory:

```bash
podman build -t mongo-mcp:local .
```

Test locally:

```bash
podman run --rm -it \
  -e MONGO_URI="mongodb+srv://..." \
  -e MCP_MODE=stdio \
  mongo-mcp:local
```

---

## Publish to GitHub Container Registry (GHCR)

### 1. Authenticate to GHCR

Create a GitHub Personal Access Token with:

- `write:packages`
- `read:packages`

Login:

```bash
echo $GITHUB_TOKEN | podman login ghcr.io \
  -u YOUR_GITHUB_USERNAME \
  --password-stdin
```

---

### 2. Tag the image

```bash
podman tag mongo-mcp:local ghcr.io/YOUR_GITHUB_USERNAME/mongo-mcp:latest
```

---

### 3. Push the image

```bash
podman push ghcr.io/YOUR_GITHUB_USERNAME/mongo-mcp:latest
```

After pushing, the package appears under:

```
GitHub → Profile → Packages → mongo-mcp
```

---

## Running MongoMCP from GHCR

```bash
podman run --rm -it \
  -e MONGO_URI="mongodb+srv://..." \
  -e MCP_MODE=stdio \
  ghcr.io/YOUR_GITHUB_USERNAME/mongo-mcp:latest
```

### Common environment variables

| Variable    | Description               |
| ----------- | ------------------------- |
| `MONGO_URI` | MongoDB connection string |
| `MCP_MODE`  | `stdio` or `http`         |
| `LOG_LEVEL` | `info`, `debug`           |

---

## MongoDB Setup (required)

MongoMCP expects a database called:

```
mcp_config
```

Required collections:

- `agent_identities`
- `mcp_tools`
- `tool_prompts`

### Example agent identity document

```json
{
  "agent_key": "console-chatbot",
  "agent_name": "console_chatbot",
  "pvk": "demo-secret-console-chatbot",
  "scope": ["vectorize", "tools:read", "llm:invoke"]
}
```

---

## Generating a JWT for local testing

MongoMCP uses **HS256 JWTs**. Example token generator:

```python
import jwt, time

payload = {
  "agent_key": "console-chatbot",
  "agent_name": "console_chatbot",
  "scope": ["vectorize", "tools:read", "llm:invoke"],
  "iat": int(time.time()),
  "exp": int(time.time()) + 3600
}

headers = {
  "alg": "HS256",
  "typ": "JWT",
  "api_key": "console-chatbot"
}

print(jwt.encode(payload, "demo-secret-console-chatbot", algorithm="HS256", headers=headers))
```

---

## Using MongoMCP with Claude Desktop

MongoMCP runs as a **backend server**. Claude Desktop connects via a **local MCP bridge** script.

Typical flow:

```
Claude Desktop
   ↓ stdio
MCP bridge (Python)
   ↓ HTTP + JWT
MongoMCP container
```

Your Claude `config.json` references the **bridge**, not the container directly.

---

## Troubleshooting

### Container starts but tools return 401

- JWT does not match MongoDB `pvk`
- `api_key` header mismatch
- Token expired

### MCP tools not visible in Claude

- Bridge script not running
- Tool name mismatch
- MCP server stdout blocked

### Mongo connection issues

- IP allowlist in Atlas
- Invalid URI

---

## Summary

✔ Uses GitHub Container Registry (no paid registry) ✔ Podman‑native (Docker compatible) ✔ Clean MCP backend ✔ Claude Desktop compatible ✔ MongoDB‑backed authorization and history

This setup is intentionally **production‑shaped** while remaining demo‑friendly.


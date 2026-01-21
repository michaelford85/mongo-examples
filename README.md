# MongoDB Examples with AI, Vector Search, and MCP

This repository contains **multiple complementary projects** demonstrating how to integrate **MongoDB Atlas**, **vector search**, **AWS Bedrock**, and the **Model Context Protocol (MCP)**—including **local MCP clients**, **containerized MCP servers**, and **Claude Desktop integration**.

The goal of this repo has evolved beyond simple demos: it now shows **end‑to‑end agentic workflows**, where *clients (Claude Desktop, Python MCP clients)* can interact with *one or more MCP servers* that expose MongoDB‑backed tools.

---

## Repository Structure

### `jsonembed/`
**Document Embedding and Vectorization**

A Python application that processes MongoDB documents, generates AI embeddings using **AWS Bedrock**, and stores vector representations for semantic search.

- Document chunking and text extraction
- AWS Bedrock Titan embeddings
- Batch processing of MongoDB collections
- MongoDB Atlas Vector Search storage

---

### `MongoMCP/`
**MongoDB MCP Server (Core Runtime)**

A FastAPI‑based **MCP server** that exposes MongoDB functionality as MCP tools. This server is the backbone for both local development and containerized deployments.

Key capabilities:
- Vector similarity search using `$vectorSearch`
- Atlas Search and aggregation queries
- Tool discovery via `/tools_config`
- JWT‑based agent authentication backed by MongoDB
- Designed to run **locally**, **in containers**, or **behind an MCP bridge**

This server is what ultimately powers tools like **AirbnbSearch**.

---

### `mcpclient/`
**MCP Clients & Bridges (Claude / Local)**

This directory now serves **two distinct roles**:

1. **Standalone MCP clients** (Python) for testing and development
2. **MCP bridge servers** used by **Claude Desktop** to access already‑running MCP services

Key components:
- `mcp_bridge_airbnb.py` – exposes a local MCP tool that *proxies* requests to a running MongoMCP server
- `gen_token.py` – generates JWTs for agent authentication
- Example clients for invoking MCP tools directly

This separation allows Claude Desktop to interact with MCP servers **without embedding secrets or MongoDB credentials inside Claude**.

---

## Updated Architecture (Important)

The architecture now looks like this:

```
Claude Desktop
   │
   │ (stdio MCP)
   ▼
MCP Bridge (Python, local)
   │
   │ (HTTP + JWT)
   ▼
MongoMCP Server (FastAPI)
   │
   ▼
MongoDB Atlas (vector search, config, auth)
```

Key idea:
- **Claude never talks directly to MongoDB**
- Claude talks to a **local MCP bridge**
- The bridge forwards requests to **one or more MCP servers**

This enables:
- Multiple MCP servers per agent
- Local or remote MCP servers
- Secure token‑based auth

---

## Prerequisites

- **Python 3.10–3.12** (Python 3.13 is *not* recommended for some dependencies)
- MongoDB Atlas cluster (sample Airbnb dataset)
- AWS account with Bedrock access
- Docker or Podman (for containerized MCP server)
- Claude Desktop (paid plan required for MCP tools)

---

## Running the MongoMCP Server (Containerized)

The MongoMCP server is typically run as a container:

```bash
podman run --rm -p 8000:8000 \
  -e MCP_TOOL_NAME=AirbnbSearch \
  -e MONGO_CREDS=mford_study_cluster_creds \
  -e AWS_REGION=us-east-2 \
  -e AWS_PROFILE="Solution-Architects.User-979559056307" \
  -e AWS_SDK_LOAD_CONFIG=1 \
  -v $HOME/.aws:/root/.aws \
  979559056307.dkr.ecr.us-east-2.amazonaws.com/mongodb-vector-mcp:latest
```

Once running, verify:

- OpenAPI: http://localhost:8000/docs
- Tool config: `GET /tools_config`

---

## Authentication Model (Critical)

MongoMCP uses **JWT Bearer authentication**, validated against MongoDB:

### MongoDB Collection
`mcp_config.agent_identities`

Example document:
```json
{
  "agent_name": "console_chatbot",
  "agent_key": "console_chatbot",
  "pvk": "demo-secret-console-chatbot",
  "scope": ["vectorize", "tools:read", "llm:invoke"]
}
```

### Token Generation

Generate a token locally:

```bash
python gen_token.py
```

Token requirements:
- Header `api_key` must match `agent_key`
- Payload must include `agent_name`
- Signed using the MongoDB‑stored `pvk`

---

## MCP Bridge for Claude Desktop

Claude Desktop **does not connect to HTTP MCP servers directly**.

Instead, it runs **local stdio MCP servers**, defined in:

```
~/Library/Application Support/Claude/config.json
```

### Example Claude MCP Configuration

```json
{
  "mcpServers": {
    "mongodb-vector-mcp-airbnb": {
      "command": "/Users/michael.ford/venvs/chapman-mcp-demo/bin/python",
      "args": [
        "/Users/michael.ford/git-workspace/mongo-examples/mcpclient/mcp_bridge_airbnb.py"
      ],
      "env": {
        "UPSTREAM_BASE_URL": "http://127.0.0.1:8000",
        "AUTH_TOKEN": "<JWT_TOKEN>"
      }
    }
  }
}
```

The bridge:
- Registers tools with Claude via MCP
- Forwards calls to the running MongoMCP server
- Injects the required JWT automatically

---

## Using Tools in Claude

Once configured:

1. Restart Claude Desktop
2. Start a new chat
3. Ask Claude to use the tool explicitly:

> "Use the AirbnbSearch tool to vectorize: pet‑friendly apartments in Logan Square under $250/night"

Claude will:
- Discover the tool
- Call the MCP bridge
- Forward to MongoMCP
- Return real results

---

## Can One Query Use Multiple Tools?

Yes — **this is the core of agentic MCP**.

Claude can:
- Call multiple tools sequentially
- Chain MCP servers
- Use results from one tool as input to another

This repo is designed to demonstrate that pattern.

---

## License

See [LICENSE](./LICENSE) for details.


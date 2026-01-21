# Dynamic MongoDB MCP Server

A highly configurable Model Context Protocol (MCP) server that dynamically exposes MongoDB Atlas data (including Vector Search) to MCP-compatible AI agents. The server supports dynamic MCP tool generation for various MongoDB collections and use cases.

---

## ⚠️ Important Compatibility Notes (Added)

### Python Version Support

| Python Version | Status |
|---------------|--------|
| **3.11.x** | ✅ Supported (recommended) |
| **3.12.x** | ✅ Supported |
| **3.13.x** | ❌ Not supported (OpenSSL / hashlib / awscrt incompatibilities with boto3) |

> **Do not use Python 3.13**. If you are using `pyenv`, explicitly install and select Python 3.11 or 3.12.

---

## Features

- **Dynamic Configuration**: MCP server configuration is dynamic and stored in MongoDB, allowing for flexible tool definitions without code changes
- **Automatic Tool Generation**: Tool information and metadata are generated based on JSON configuration documents stored in MongoDB
- **Vector Search**: Perform semantic similarity search using MongoDB's `$vectorSearch` aggregation pipeline with AI embeddings
- **Text Search**: Full-text search using MongoDB's `$search` aggregation pipeline with keyword matching
- **Unique Values Discovery**: Get unique values for any field to discover available filter options
- **Custom Aggregation Queries**: Execute complex MongoDB aggregation pipelines for advanced data analysis
- **Collection Info**: Get comprehensive metadata about the MongoDB collection, indexes, and search capabilities
- **Prompts**: Store and edit MCP prompts which are dynamically callable from endpoints on the MCP service
- **Multi-Configuration Support**: Support for multiple MCP servers with multiple clusters and collections

---

## Prerequisites

- **Python 3.11 or 3.12** (see compatibility note above)
- MongoDB Atlas cluster with MCP configuration collection
- MongoDB Atlas cluster with target data collection(s)
- AWS account with:
  - AWS CLI v2
  - AWS SSO or IAM credentials
  - Access to **AWS Secrets Manager**
- MCP client (Claude Desktop, Cline, etc.)
- Docker **or** Podman (for containerized runs)

---

## How Configuration Works (Added Context)

This MCP server **does not hardcode MongoDB connection strings**.

Instead, configuration is resolved dynamically from:

1. **MongoDB Atlas collections** (tool definitions)
2. **AWS Secrets Manager** (MongoDB credentials)

### MongoDB Configuration Collections

| Collection | Purpose |
|----------|--------|
| `mcp_config.mcp_tools` | Defines available MCP tools, collections, indexes, and capabilities |
| `mcp_config.agent_identities` | Defines which agents are allowed to use which tools |

These documents must be imported before the server can start successfully.

---

## Required Environment Variables (Added)

### Core Runtime Variables

| Variable | Required | Description |
|--------|---------|-------------|
| `MCP_TOOL_NAME` | ✅ | Name of the MCP tool to load (must match `name` field in `mcp_tools`) |
| `AWS_REGION` | ✅ | AWS region containing the Secrets Manager secret |
| `MONGO_CREDS` | ✅ | Name of AWS Secrets Manager secret containing MongoDB URI |

### AWS Credential Variables (Local / Container)

| Variable | When Needed |
|--------|------------|
| `AWS_PROFILE` | Using AWS SSO |
| `AWS_SDK_LOAD_CONFIG=1` | Required for boto3 + SSO |

---

## AWS Secrets Manager Requirements (Added)

The secret referenced by `MONGO_CREDS` **must contain a MongoDB connection string**.

Example secret value:

```json
{
  "uri": "mongodb+srv://<user>:<password>@cluster.mongodb.net"
}
```

Accepted key names:
- `uri`
- `mongodb_uri`
- `connection_string`

---

## Dynamic Configuration Setup

### Import MCP Tool Definitions

```bash
mongoimport \
  --uri "mongodb+srv://<user>@<cluster>.mongodb.net" \
  --db mcp_config \
  --collection mcp_tools \
  --file mcp_config.mcp_tools.json \
  --jsonArray
```

### Import Agent Identities

```bash
mongoimport \
  --uri "mongodb+srv://<user>@<cluster>.mongodb.net" \
  --db mcp_config \
  --collection agent_identities \
  --file mcp_config.agent_identities.json \
  --jsonArray
```

---

## Python Virtual Environment Setup

```bash
python3.12 -m venv venv
source venv/bin/activate
```

---

## Installation

```bash
pip install -r requirements.txt
```

---

## FastAPI Deployment

```bash
export MCP_TOOL_NAME=AirbnbSearch
export AWS_REGION=us-east-2
export MONGO_CREDS=mford_study_cluster_creds
export AWS_PROFILE=Solution-Architects.User-979559056307
export AWS_SDK_LOAD_CONFIG=1

fastapi run mongo_mcp.py
```

Swagger UI:
```
http://localhost:8000/docs
```

---

## Running in a Container (Added)

```bash
podman run --rm \
  -p 8000:8000 \
  -e MCP_TOOL_NAME=AirbnbSearch \
  -e AWS_REGION=us-east-2 \
  -e MONGO_CREDS=mford_study_cluster_creds \
  -e AWS_PROFILE=Solution-Architects.User-979559056307 \
  -e AWS_SDK_LOAD_CONFIG=1 \
  -v $HOME/.aws:/root/.aws:ro \
  <account>.dkr.ecr.<region>.amazonaws.com/mongodb-vector-mcp:latest
```

---

## Common Errors & Fixes (Added)

### ❌ `tool None`
Cause: `MCP_TOOL_NAME` missing or does not match a document in `mcp_tools`.

### ❌ `Invalid type for parameter SecretId`
Cause: `MONGO_CREDS` not set or incorrect.

### ❌ `Token has expired and refresh failed`
Cause: AWS SSO token expired. Run:

```bash
aws sso login --profile <profile>
```

### ❌ hashlib / blake2 errors
Cause: Python 3.13. Downgrade to Python 3.11 or 3.12.

---

## Architecture Overview (Added)

```
MCP Client
   ↓
FastAPI MCP Server
   ↓
MongoDB Atlas (config + data)
   ↓
Vector Search / Aggregation
```

---

## How to Run the MCP Service (Original)

1. Setup MongoDB with MCP configurations (see [Dynamic Configuration Setup](#dynamic-configuration-setup) above)
2. Setup your python environment (see [Python Virtual Environment Setup](#python-virtual-environment-setup))
3. Install requirements (see [Installation](#installation))
4. Run fastapi (see [FastAPI Deployment](#fastapi-deployment))
5. Run the MCP client (see `../mcpclient/mcp_client`)


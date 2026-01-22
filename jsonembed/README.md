# MongoDB Vector Search with VoyageAI (Airbnb Example)

This repository demonstrates how to build a **MongoDB Atlas Vector Search** pipeline using the Airbnb sample dataset, powered by **VoyageAI embeddings**.

This refactor removes **AWS / Bedrock entirely** and focuses on:

- MongoDB Atlas Vector Search
- VoyageAI embedding models
- Clean, local-first Python workflows
- Compatibility with MCP-based tools (Claude Desktop, FastMCP)

---

## Repository Overview

- **`embedairbnb.py`** – Generates vector embeddings using VoyageAI and stores them in MongoDB
- **`settings.py`** – Centralized configuration (MongoDB + VoyageAI)
- **`mcpclient/`** – MCP bridge examples for Claude Desktop integration

> For advanced multi-tool reasoning and agent-driven workflows, see the MCP examples in `mcpclient/`.

---

## 1. Python Environment Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 2. Configuration (`settings.py`)

Update `settings.py` with **MongoDB Atlas** and **VoyageAI** credentials:

```python
# settings.py

MONGODB_URI = "mongodb+srv://<username>:<password>@<cluster-url>/sample_airbnb"
MONGODB_DB = "sample_airbnb"
MONGODB_COLLECTION = "listingsAndReviews"

VOYAGE_API_KEY = "<your-voyage-api-key>"
VOYAGE_MODEL = "voyage-2"  # or voyage-large-2
```

---

## 3. Create the Vector Index

Create a **MongoDB Atlas Vector Search index** on the target collection.

### Example Index Definition

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1024,
      "similarity": "cosine"
    },
    { "type": "filter", "path": "address.country_code" },
    { "type": "filter", "path": "address.market" },
    { "type": "filter", "path": "beds" },
    { "type": "filter", "path": "bedrooms" },
    { "type": "filter", "path": "address.suburb" }
  ]
}
```

> Ensure the `numDimensions` matches the VoyageAI model you choose.

---

## 4. Generate Embeddings

Run the embedding script:

```bash
source venv/bin/activate
python embedairbnb.py
```

### What `embedairbnb.py` Does

1. Reads Airbnb documents from MongoDB
2. Extracts semantically useful fields (name, summary, description, property type, room type, address)
3. Combines fields into a single text payload per listing
4. Calls **VoyageAI** to generate embeddings
5. Stores embeddings back into MongoDB

### Document Limit

By default, the script processes a limited batch of documents.

You can adjust this in `main()`:

```python
vectorizer.process_documents(limit=1000)
```

---

## 5. MCP + Claude Desktop Integration (Optional)

This project supports **MCP (Model Context Protocol)** so Claude Desktop can invoke your vector search pipeline as a tool.

### MCP Bridge Example

```python
@mcp.tool()
def airbnb_search(payload: dict) -> dict:
    url = f"{UPSTREAM}/vectorize"
    r = httpx.post(url, json=payload, headers=_headers())
    r.raise_for_status()
    return r.json()
```

### Claude `config.json`

```json
{
  "mcpServers": {
    "mongodb-vector-mcp-airbnb": {
      "command": "/path/to/python",
      "args": ["/path/to/mcp_bridge_airbnb.py"],
      "env": {
        "UPSTREAM_BASE_URL": "http://127.0.0.1:8000",
        "AUTH_TOKEN": "<JWT>"
      }
    }
  }
}
```

Once connected, Claude can call:

```
Use the AirbnbSearch tool to vectorize:
"pet-friendly apartments in Logan Square under $250/night"
```

---

## 6. Why VoyageAI?

- High-quality embeddings optimized for retrieval
- Predictable dimensionality
- Simple API (no cloud IAM or credential sprawl)
- Ideal for MongoDB Atlas Vector Search

---

## 7. Next Steps

- Add metadata-aware hybrid search (vector + filters)
- Store embeddings in a separate collection
- Add re-ranking or score thresholds
- Introduce multi-tool MCP chains (vectorize → search → summarize)

---

## Summary

This refactor modernizes the original RAG example by:

- ❌ Removing AWS / Bedrock
- ✅ Using VoyageAI for embeddings
- ✅ Aligning with MCP + Claude Desktop
- ✅ Keeping MongoDB Atlas at the center

You now have a clean, composable vector search foundation that works equally well for scripts, APIs, and agent-based workflows.
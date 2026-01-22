# MongoDB Vector Search with VoyageAI and RAG (Airbnb Example)

This repository demonstrates how to build a **MongoDB Atlas Vector Search** pipeline using the Airbnb sample dataset, powered by **VoyageAI embeddings**.

Focus is placed on the following technologies:

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
## 1. Install pyenv

### macOS
```
brew update
brew install pyenv
```
- Add pyenv to your shell:

zsh (default on MacOS):
```
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
```

- Reload your shell:
```
source ~/.zshrc
```
### Ubuntu Linux

- Install dependencies:
```
sudo apt update
sudo apt install -y \
  build-essential \
  curl \
  git \
  libssl-dev \
  zlib1g-dev \
  libbz2-dev \
  libreadline-dev \
  libsqlite3-dev \
  libffi-dev \
  liblzma-dev \
  tk-dev \
  xz-utils \
  ca-certificates
```
- Install pyenv:
```
curl https://pyenv.run | bash
```

- Add pyenv to your shell (bash):
```
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
```

- Reload:
```
source ~/.bashrc
```

## 2. Install Python 3.12

- Why Python 3.12?
  - Required for modern MCP tooling
  - Better async performance
  - Improved typing and error messages
  - Matches Claude Desktop MCP client expectations

- Once pyenv is installed:
```
pyenv install 3.12.0
```

- Set it locally for the repository:
```
cd mongo-examples
pyenv local 3.12.0
```

- Verify:
```
python --version
# Python 3.12.0
```

## 3. Setup a Python Environment

```bash
python3 -m venv .venv #or specify a path to the desired venv directory
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

- Confirm Environment (Optional but Recommended)
```
python -c "import sys; print(sys.version)"
```

---

## 4. Configuration (`settings.py`)

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

## 5. Create the Vector Index

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

## 6. Generate Embeddings

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

## 7. MCP + Claude Desktop Integration (Optional)

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

## 8. Why VoyageAI?

- High-quality embeddings optimized for retrieval
- Predictable dimensionality
- Simple API (no cloud IAM or credential sprawl)
- Ideal for MongoDB Atlas Vector Search

---

## 9. Next Steps

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
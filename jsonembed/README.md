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
## 0. Prerequisites

- A MongoDB Atlas cluster with:
  - A database user with appropriate rights
  - an [IP Access list](https://www.mongodb.com/docs/atlas/security/ip-access-list/) that allows a connection from your local machine
  - The [Sample AirBnB Listings Dataset](https://www.mongodb.com/docs/atlas/sample-data/sample-airbnb/) loaded

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

## 2. Install Python 3.12.7

- Why Python 3.12.7?
  - Required for modern MCP tooling
  - Better async performance
  - Improved typing and error messages
  - Matches Claude Desktop MCP client expectations

- Once pyenv is installed:
```
pyenv install 3.12.7
```

- Set it locally for the repository:
```
cd mongo-examples
pyenv local 3.12.7
```

- Verify:
```
python --version
# Python 3.12.7
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

# mongo settings
MONGODB_URI = "mongodb+srv://<username>:<password>@<cluster-url>/sample_airbnb"
MONGODB_DB = "sample_airbnb"
MONGODB_COLLECTION = "listingsAndReviews"
VECTOR_INDEX_NAME = "listing_vector_index"
BATCH_SIZE = 100
LIMIT = 10000

# VoyageAI settings
VOYAGE_API_KEY = "<your-voyage-api-key>"
VOYAGE_MODEL = "voyage-4"  # or voyage-4-large
NUM_DIMENSIONS = 1024

# OpenAI settings
OPENAI_API_KEY = "<your-openai-api-key>"
OPENAI_MODEL = "gpt-4o-mini"  # optional override
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

## 5. Run the Search and Query System

Use the `searchairbnb.py` script to perform vector searches and interact with the LLM using your embedded Airbnb dataset:

```
# Activate your virtual environment
source .venv/bin/activate

# Run the search script
python searchairbnb.py
```

### What the Script Does
The `searchairbnb.py` script provides a Retrieval-Augmented Generation (RAG) system that:
1) **Vector Search**: Converts your questions into embeddings and finds similar Airbnb listings
2) **Metadata Filtering**: Applies filters based on your query (country, market, beds, bedrooms, listing ID)
3) **LLM Integration**: Uses OpenAI's `gpt-4o-mini` model (or another model specified by `settings.OPENAI_MODEL`) to generate natural language responses
4) **Conversation History**: Maintains context across multiple questions in a session

### Query Examples

**Basic Questions**
```
Question: What are some beachfront properties?
Question: Show me listings with great reviews
Question: Find properties good for families
```
**Filtered Searches**
```
Question: country=US,show me properties in New York
Question: market=Paris,beds=2,find apartments for couples
Question: bedrooms=3,country=AU,what's available in Sydney?
Question: id=12345678,show me details for this specific listing
```
**Direct Claude Queries**
```
Question: ask what makes a good Airbnb host?
Question: ask explain the difference between entire home and private room
```
### Filter Options
The system automatically detects and applies these filters from your questions:
- `country=XX` - Filter by country code (e.g., US, FR, AU)
- `market=CityName` - Filter by market/city
- `beds=N` - Filter by number of beds
- `bedrooms=N` - Filter by number of bedrooms
- `id=XXXXXXXX` - Get specific listing by ID (skips vector search)

### Sample Session
```
Enter questions (Press Ctrl+C to stop):
Commands:
  ask <question> - Direct Claude query without vector search
  <question> - Full query with vector search and Claude (classic RAG)
  clear - Clear conversation history

Question: country=US,beds=2,show me properties in beach locations
Answer: Based on the search results, here are some great 2-bed beachfront properties in the US...

Question: What about the pricing for these properties?
Answer: Looking at the properties from your previous search, the pricing varies...

Question: ask what should I look for when booking an Airbnb?
Answer: When booking an Airbnb, here are the key factors to consider...

Question: clear
Answer: history cleared...
```

### Performance Features
- Timing Information: The script displays processing times for each operation
- Smart Filtering: Automatically optimizes search based on detected filters
- History Management: Automatically trims conversation history to prevent token overflow
- Error Handling: Gracefully handles AWS token expiration and validation errors


### Customization Options
You can modify the search behavior by editing these parameters in the `retrieve_aggregate_facts()` method:
```
limit = 5      # Maximum results to return (default: 5)
candidates = 400  # Number of candidates to evaluate (default: 400)
```

### Troubleshooting
- Too Much History: The system automatically clears history when token limits are reached.
- No Results: Try broader search terms or remove filters.
- Connection Issues: Verify your MongoDB URI in settings.py.

### Exit the Program
Press `Ctrl+C` to stop the interactive session.


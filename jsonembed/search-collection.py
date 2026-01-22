import re
import time
from typing import Optional, List, Tuple, Any

from pymongo import MongoClient
from pymongo.server_api import ServerApi
from pymongo.collection import Collection
from bson.json_util import dumps

from openai import OpenAI
import voyageai

import settings


def _get_setting(*names: str, default=None):
    """Return the first settings.<name> that exists."""
    for n in names:
        if hasattr(settings, n):
            return getattr(settings, n)
    return default


class QueryProcessor:
    """
    Simple RAG example for Airbnb data using:
      - VoyageAI for query embeddings
      - MongoDB Atlas Vector Search for retrieval
      - OpenAI chat model for synthesis
    """

    def __init__(self):
        # Conversation history in OpenAI format: [{"role": "user"/"assistant", "content": "..."}]
        self.history: Optional[List[dict]] = None


        # Last retrieval context (for natural follow-up questions)
        self.last_results: Optional[List[str]] = None
        self.last_question: Optional[str] = None
        self.last_filters: Any = None
        # OpenAI client (LLM)
        self.openai = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.openai_model = _get_setting("OPENAI_MODEL", default="gpt-4o-mini")

        # VoyageAI client (embeddings)
        self.voyage = voyageai.Client(api_key=_get_setting("VOYAGE_API_KEY"))
        self.voyage_model = _get_setting("VOYAGE_MODEL", "VOYAGE_EMBED_MODEL", default="voyage-2")

        # MongoDB
        self.mongo_client = self._create_mongo_client()
        self.collection = self._get_vector_collection()

        # Vector index name
        self.vector_index = _get_setting("VECTOR_INDEX_NAME", "vecotr_index", default="vector_index")

    def _create_mongo_client(self) -> MongoClient:
        uri = _get_setting("MONGODB_URI", "MongoURI")
        if not uri:
            raise ValueError("Missing MongoDB URI in settings (MONGODB_URI or MongoURI).")
        return MongoClient(uri, server_api=ServerApi("1"))

    def _get_vector_collection(self) -> Collection:
        db_name = _get_setting("MONGODB_DB", "monogo_database")  # preserves your original typo too
        coll_name = _get_setting("MONGODB_COLLECTION", "vector_collection")

        if not db_name or not coll_name:
            raise ValueError(
                "Missing MongoDB DB/collection in settings "
                "(MONGODB_DB + MONGODB_COLLECTION or monogo_database + vector_collection)."
            )

        return self.mongo_client[db_name][coll_name]

    # -----------------------------
    # Embeddings (VoyageAI)
    # -----------------------------
    def generate_embedding(self, text: str) -> list:
        """
        Generates an embedding for the input text using VoyageAI.
        """
        resp = self.voyage.embed(texts=[text], model=self.voyage_model)
        return resp.embeddings[0]

    # -----------------------------
    # Retrieval (Atlas Vector Search)
    # -----------------------------
    def search_similar_documents(
        self,
        query_vector: list,
        filters: Optional[List[Tuple[str, Any]]] = None,
        limit: int = 5,
        candidates: int = 400,
        min_score: float = 0.50,
    ) -> list:
        pipeline = [
            {
                "$vectorSearch": {
                    "index": self.vector_index,
                    "path": "embedding",
                    "queryVector": query_vector,
                    "limit": limit,
                    "numCandidates": candidates,
                }
            },
            {
                "$project": {
                    "embedding": 0,
                    "images": 0,
                    "host": 0,
                    "neighborhood_overview": 0,
                    "summary": 0,
                    "space": 0,
                    "transit": 0,
                    "access": 0,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
            {"$sort": {"score": -1}},
        ]

        if filters:
            if len(filters) > 1:
                match_filter = {"$and": [{k: v} for k, v in filters]}
            else:
                k, v = filters[0]
                match_filter = {k: v}
            pipeline[0]["$vectorSearch"]["filter"] = match_filter

        output = []
        for result in self.collection.aggregate(pipeline):
            if result.get("score", 0) >= min_score:
                output.append(dumps(result))
        return output

    # -----------------------------
    # LLM (OpenAI)
    # -----------------------------
    def _invoke_openai(self, prompt: str) -> str:
        """
        Sends a prompt to an OpenAI chat model and updates conversation history.
        """
        if self.history is None:
            self.history = []

        self.history.append({"role": "user", "content": prompt})

        resp = self.openai.chat.completions.create(
            model=self.openai_model,
            messages=self.history,
            temperature=0.3,
            max_tokens=800,
        )
        assistant_message = resp.choices[0].message.content or ""

        self.history.append({"role": "assistant", "content": assistant_message})
        return assistant_message

    def query_llm(self, question: str, history: Optional[list] = None) -> tuple:
        if history:
            self.history = history
        assistant_message = self._invoke_openai(question)
        return assistant_message, self.history

    # -----------------------------
    # Filters (unchanged)
    # -----------------------------
    def _split_filters(self, pattern, question) -> Optional[str]:
        match = re.search(pattern, question)
        if match:
            temp = match.group(1)
            return temp.split(",", 1)[0]
        return None

    def extract_filters(self, question: str):
        filters = []

        # listing id: id=10006546
        pattern = r"(?i)id=(\d{8})"
        match = self._split_filters(pattern, question)
        if match:
            filters.append(("_id", match))
            print(f"found objectid, skipping vector search: {filters}")
            return (filters, True)

        pattern = r"(?i)country=([^\" ]+)"
        match = self._split_filters(pattern, question)
        if match:
            filters.append(("address.country_code", match))

        pattern = r"(?i)market=([^\" ]+)"
        match = self._split_filters(pattern, question)
        if match:
            filters.append(("address.market", match))

        pattern = r"(?i)beds=(\d+)"
        match = self._split_filters(pattern, question)
        if match:
            filters.append(("beds", int(match)))

        pattern = r"(?i)bedrooms=(\d+)"
        match = self._split_filters(pattern, question)
        if match:
            filters.append(("bedrooms", int(match)))

        if filters:
            print(filters)
            return (filters, False)
        return None

    # -----------------------------
    # RAG Orchestration
    # -----------------------------
    
    def _is_followup(self, question: str) -> bool:
        """Heuristic: detect follow-up questions that refer to prior results."""
        q = (question or "").strip().lower()
        return any(p in q for p in [
            "these", "those", "them", "it", "pricing", "price", "cost", "how much",
            "what about", "and what", "compare", "which one", "cheapest", "most expensive",
            "more details", "tell me more", "amenities", "availability", "location"
        ])

    def _build_retrieval_query(self, question: str, max_messages: int = 4) -> str:
        """Build a retrieval query that includes a small window of prior conversation."""
        if not self.history:
            return question
        recent = self.history[-max_messages:]
        convo = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in recent)
        return f"Conversation context:\n{convo}\n\nCurrent question:\n{question}".strip()


    def retrieve_aggregate_facts(self, question: str, history: Optional[list] = None) -> tuple:
        """Vector retrieval + LLM synthesis.

        Option D (recommended):
        - Follow-ups reuse the previous retrieval set for human-natural continuity.
        - New topics perform a fresh vector search using a small window of conversation history.
        """
        if history is not None:
            self.history = history

        response_message = "no context from vectors"

        # 1) Extract explicit filters first (so the user can override context)
        start_time = time.time()
        filters = self.extract_filters(question)
        print(f"extract_filters completed in {time.time() - start_time:.4f} seconds.")

        has_explicit_filter = bool(filters and (filters[1] or (isinstance(filters[0], list) and len(filters[0]) > 0)))

        # 2) If this looks like a follow-up and the user didn't supply new filters,
        #    reuse the last retrieved documents as context (skip vector search).
        if self.last_results and self._is_followup(question) and not has_explicit_filter:
            context = "\n".join(self.last_results)
            prompt = (
                "Use the following context to answer the question.\n"
                f"Context:\n{context}\n\n"
                f"Question:\n{question}"
            )

            start_time = time.time()
            try:
                response_message, _ = self.query_llm(prompt, self.history)
                if self.history and len(self.history) > 8:
                    self.history = self.history[-6:]
            except Exception as e:
                print("LLM call failed:", repr(e))
                self.history = None
            print(f"query_llm completed in {time.time() - start_time:.4f} seconds.")

            return response_message, self.history

        # 3) Otherwise, run retrieval
        mongo_results = None

        # direct doc fetch by id=...
        if filters and filters[1]:
            value = filters[0][0][1] if isinstance(filters[0], list) else filters[0][1]
            doc = self.collection.find_one({"_id": value})
            if doc:
                doc.pop("embedding", None)
                mongo_results = [dumps(doc)]
        else:
            filter_list = filters[0] if filters else None

            # Build a retrieval query that includes a small window of conversation context
            retrieval_query = self._build_retrieval_query(question)

            start_time = time.time()
            query_vector = self.generate_embedding(retrieval_query)
            print(f"generate_embedding completed in {time.time() - start_time:.4f} seconds.")

            start_time = time.time()
            mongo_results = self.search_similar_documents(query_vector, filter_list, limit=5, candidates=400)
            print(f"search_similar_documents completed in {time.time() - start_time:.4f} seconds.")

        # Save retrieval context for follow-ups
        if mongo_results:
            self.last_results = mongo_results
            self.last_question = question
            self.last_filters = filters

            context = "\n".join(mongo_results)
            prompt = (
                "Use the following context to answer the question.\n"
                f"Context:\n{context}\n\n"
                f"Question:\n{question}"
            )

            start_time = time.time()
            try:
                response_message, _ = self.query_llm(prompt, self.history)

                # Keep history from ballooning (simple sliding window)
                if self.history and len(self.history) > 8:
                    self.history = self.history[-6:]
            except Exception as e:
                print("LLM call failed:", repr(e))
                # reset history on hard failures to keep demo resilient
                self.history = None
            print(f"query_llm completed in {time.time() - start_time:.4f} seconds.")

        return response_message, self.history

    def run(self) -> None:
        print("Enter questions (Press Ctrl+C to stop):")
        print("Commands:")
        print("  ask <question> - Direct LLM query without vector search")
        print("  <question>     - Full query with vector search + LLM (classic RAG)")
        print("  clear          - Clear conversation history")

        try:
            while True:
                user_input = input("Question: ").strip()
                if not user_input:
                    print("Answer: Not a valid question")
                    continue

                if user_input.startswith("ask"):
                    user_input = user_input.removeprefix("ask").strip()
                    answer, _ = self.query_llm(user_input)
                elif user_input.startswith("clear"):
                    self.history = None
                    self.last_results = None
                    self.last_question = None
                    self.last_filters = None
                    answer = "history cleared..."
                else:
                    answer, _ = self.retrieve_aggregate_facts(user_input)

                print(f"Answer: {answer}")
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, exiting...")


def main():
    processor = QueryProcessor()
    processor.run()


if __name__ == "__main__":
    main()
import time
from typing import List

from pymongo import MongoClient
from pymongo import UpdateOne
import voyageai

import settings


class AirbnbVoyageVectorizer:
    def __init__(self):
        # MongoDB
        self.client = MongoClient(settings.MONGODB_URI)
        self.db = self.client[settings.MONGODB_DB]
        self.collection = self.db[settings.MONGODB_COLLECTION]

        # VoyageAI client
        self.voyage = voyageai.Client(api_key=settings.VOYAGE_API_KEY)

        # Model config
        self.model = settings.VOYAGE_MODEL
        self.batch_size = getattr(settings, "BATCH_SIZE", 32)

    def _build_text(self, doc: dict) -> str:
        """
        Build a semantically rich text field from an Airbnb document.
        """
        parts = [
            doc.get("name"),
            doc.get("summary"),
            doc.get("description"),
            doc.get("space"),
            doc.get("property_type"),
            doc.get("room_type"),
            doc.get("address", {}).get("market"),
            doc.get("address", {}).get("suburb"),
        ]

        # Filter out empty fields and join
        return " | ".join([p for p in parts if isinstance(p, str) and p.strip()])

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of text using VoyageAI.
        """
        response = self.voyage.embed(
            texts=texts,
            model=self.model
        )
        return response.embeddings

    def process_documents(self, limit: int = 1000):
        """
        Read Airbnb documents, generate embeddings, and store them back in MongoDB.
        """
        cursor = (
            self.collection
            .find({"embedding": {"$exists": False}})
            .limit(limit)
        )

        batch_docs = []
        batch_texts = []

        processed = 0

        for doc in cursor:
            text = self._build_text(doc)
            if not text:
                continue

            batch_docs.append(doc)
            batch_texts.append(text)

            if len(batch_texts) >= self.batch_size:
                self._process_batch(batch_docs, batch_texts)
                processed += len(batch_docs)
                batch_docs, batch_texts = [], []

        # Final partial batch
        if batch_docs:
            self._process_batch(batch_docs, batch_texts)
            processed += len(batch_docs)

        print(f"✅ Embedded {processed} documents using VoyageAI")

    def _process_batch(self, docs, texts):
        embeddings = self._embed_batch(texts)

        ops = [
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"embedding": embedding}},
                upsert=False
            )
            for doc, embedding in zip(docs, embeddings)
        ]

        if ops:
            result = self.collection.bulk_write(ops, ordered=False)
            print(f"Updated: {result.modified_count}, Matched: {result.matched_count}")

        # Be polite to the API
        time.sleep(0.25)


def main():
    vectorizer = AirbnbVoyageVectorizer()
    vectorizer.process_documents(settings.LIMIT)


if __name__ == "__main__":
    main()
from pymongo import MongoClient
import settings


def remove_embeddings(
    filter_query: dict | None = None,
    dry_run: bool = False
):
    """
    Remove the `embedding` field from MongoDB documents.

    :param filter_query: Optional MongoDB filter (default: all docs with embeddings)
    :param dry_run: If True, only prints how many docs would be updated
    """
    client = MongoClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB]
    collection = db[settings.MONGODB_COLLECTION]

    # Default: only documents that actually have embeddings
    query = filter_query or {"embedding": {"$exists": True}}

    count = collection.count_documents(query)

    if dry_run:
        print(f"[DRY RUN] Would remove embeddings from {count} documents")
        return

    if count == 0:
        print("No documents with embeddings found.")
        return

    result = collection.update_many(
        query,
        {"$unset": {"embedding": ""}}
    )

    print(
        f"✅ Removed embeddings from {result.modified_count} documents "
        f"in {settings.MONGODB_DB}.{settings.MONGODB_COLLECTION}"
    )


if __name__ == "__main__":
    # Example usage
    # Set dry_run=True first if you want to preview
    remove_embeddings(dry_run=False)
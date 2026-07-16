"""Chroma persistent vector store wrapper."""
import os
import json
from langchain_community.vectorstores import Chroma
from rag.embeddings import get_embeddings

PERSIST_DIR = os.path.join("database", "chroma")
COLLECTION_NAME = "policies"
HASH_REGISTRY_PATH = os.path.join("database", "ingested_hashes.json")

_vectorstore = None


def get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        os.makedirs(PERSIST_DIR, exist_ok=True)
        _vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=get_embeddings(),
            persist_directory=PERSIST_DIR,
            collection_metadata={"hnsw:space": "cosine"},
        )
    return _vectorstore


def clear_collection():
    """Deletes and recreates the collection so Rebuild Index can run without a restart."""
    global _vectorstore
    vs = get_vectorstore()
    try:
        vs.delete_collection()
    except Exception as e:
        print(f"[vectorstore] clear_collection warning: {e}")
    _vectorstore = None
    if os.path.exists(HASH_REGISTRY_PATH):
        os.remove(HASH_REGISTRY_PATH)
    return get_vectorstore()


def load_hash_registry() -> dict:
    if os.path.exists(HASH_REGISTRY_PATH):
        try:
            with open(HASH_REGISTRY_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_hash_registry(registry: dict):
    os.makedirs(os.path.dirname(HASH_REGISTRY_PATH), exist_ok=True)
    with open(HASH_REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)

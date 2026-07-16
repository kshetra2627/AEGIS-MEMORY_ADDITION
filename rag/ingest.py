"""Scans data/policies, dedupes by content hash, chunks, embeds, and indexes into Chroma."""
import os
from rag.loader import load_file, file_hash
from rag.splitter import split_documents
from rag.vectorstore import get_vectorstore, clear_collection, load_hash_registry, save_hash_registry
from rag.hybrid import invalidate_bm25_cache
from rag.query_rewrite import invalidate_vocabulary

POLICIES_DIR = os.path.join("data", "policies")
SUPPORTED_EXT = {".pdf", ".docx", ".txt"}


def _list_policy_files() -> list[str]:
    if not os.path.isdir(POLICIES_DIR):
        return []
    files = []
    for name in os.listdir(POLICIES_DIR):
        path = os.path.join(POLICIES_DIR, name)
        if os.path.isfile(path) and os.path.splitext(name)[1].lower() in SUPPORTED_EXT:
            files.append(path)
    return files


def ingest_all(force_rebuild: bool = False) -> dict:
    """Ingests every supported file in data/policies. Skips duplicates and corrupted files.
    Returns a summary dict for UI feedback.
    """
    if force_rebuild:
        clear_collection()
        invalidate_bm25_cache()
        invalidate_vocabulary()

    registry = load_hash_registry()
    files = _list_policy_files()
    summary = {"scanned": len(files), "ingested": [], "skipped_duplicate": [], "skipped_error": [], "chunks_added": 0,
               "duplicate_of": {}}

    if not files:
        return summary

    vs = get_vectorstore()
    hash_to_filename = {h: fn for fn, h in registry.items()}

    for path in files:
        filename = os.path.basename(path)
        try:
            h = file_hash(path)
        except Exception as e:
            summary["skipped_error"].append(filename)
            print(f"[ingest] hash failed for {filename}: {e}")
            continue

        if registry.get(filename) == h:
            summary["skipped_duplicate"].append(filename)
            continue

        existing_owner = hash_to_filename.get(h)
        if existing_owner and existing_owner != filename:
            summary["skipped_duplicate"].append(filename)
            summary["duplicate_of"][filename] = existing_owner
            registry[filename] = h  # tracked, but never embedded -- same content already indexed
            continue

        docs = load_file(path)
        if not docs:
            summary["skipped_error"].append(filename)
            continue

        try:
            chunks = split_documents(docs)
            if chunks:
                vs.add_documents(chunks)
                summary["chunks_added"] += len(chunks)
            registry[filename] = h
            hash_to_filename[h] = filename
            summary["ingested"].append(filename)
        except Exception as e:
            summary["skipped_error"].append(filename)
            print(f"[ingest] failed to index {filename}: {e}")

    save_hash_registry(registry)
    if summary["ingested"]:
        invalidate_bm25_cache()
        invalidate_vocabulary()
    return summary


def corpus_is_empty() -> bool:
    return len(_list_policy_files()) == 0


def list_indexed_documents() -> list[dict]:
    """Per-document stats for the Knowledge Base page: pages, chunks, indexed date, dedup status, hash."""
    registry = load_hash_registry()
    try:
        vs = get_vectorstore()
        data = vs.get(include=["metadatas"])
        metas = data.get("metadatas", []) or []
    except Exception as e:
        print(f"[ingest] could not read vectorstore for document stats: {e}")
        metas = []

    per_file_pages: dict[str, set] = {}
    per_file_chunks: dict[str, int] = {}
    for m in metas:
        fn = m.get("filename")
        if not fn:
            continue
        per_file_pages.setdefault(fn, set()).add(m.get("page"))
        per_file_chunks[fn] = per_file_chunks.get(fn, 0) + 1

    rows = []
    for filename, h in registry.items():
        path = os.path.join(POLICIES_DIR, filename)
        indexed_at = _mtime_str(path)
        original = next((fn for fn, hh in registry.items() if hh == h and fn != filename), None)
        status = f"Duplicate of {original}" if (filename not in per_file_chunks and original) else "Indexed"
        rows.append({
            "filename": filename,
            "pages": len(per_file_pages.get(filename, set())),
            "chunks": per_file_chunks.get(filename, 0),
            "date_indexed": indexed_at,
            "status": status,
            "hash": h[:16] + "...",
        })
    return rows


def _mtime_str(path: str) -> str:
    if os.path.exists(path):
        from datetime import datetime
        return datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
    return "N/A"

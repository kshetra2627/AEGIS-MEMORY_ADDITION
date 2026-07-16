"""Chunk page-level Documents while preserving/augmenting metadata (section, clause, chunk_id)."""
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

CLAUSE_PATTERNS = [
    r"\bArticle\s+\d+[A-Za-z]?\b",
    r"\bClause\s+\d+(\.\d+)*\b",
    r"\bSection\s+\d+(\.\d+)*\b",
    r"\bParagraph\s+\d+\b",
    r"§\s?\d+(\.\d+)*",
    r"\bRule\s+\d+(\.\d+)*\b",
]
HEADING_PATTERN = re.compile(r"^[A-Z][A-Z \-/&0-9]{6,80}$", re.MULTILINE)


def _find_clause(text: str) -> str | None:
    for pat in CLAUSE_PATTERNS:
        m = re.search(pat, text)
        if m:
            return m.group(0)
    return None


def _find_heading(text: str) -> str | None:
    m = HEADING_PATTERN.search(text)
    if m:
        return m.group(0).strip()
    return None


def split_documents(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    chunks: list[Document] = []
    for doc in docs:
        sub_chunks = splitter.split_text(doc.page_content)
        for idx, text in enumerate(sub_chunks):
            meta = dict(doc.metadata)
            filename = meta.get("filename", "unknown")
            page = meta.get("page", 1)
            meta["section"] = _find_heading(text) or ""
            meta["clause"] = _find_clause(text) or ""
            meta["chunk_id"] = f"{filename}_p{page}_c{idx}"
            chunks.append(Document(page_content=text, metadata=meta))
    return chunks

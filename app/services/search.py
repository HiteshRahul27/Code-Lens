import os
import json
from typing import List, Dict
from collections import Counter

from app.core.config import settings
from app.services.vector_store import load_index
from app.services.embedder import model
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("cross-encoder/ms-marco-TinyBERT-L-2-v2", max_length=512)


def search_repo(query: str, repo: str, top_k: int = 8) -> List[Dict]:
    repo_path = os.path.join(settings.DATA_DIR, repo)
    chunks_path = os.path.join(repo_path, "chunks.json")
    index_path = os.path.join(repo_path, "code_index.faiss")

    if not os.path.exists(chunks_path) or not os.path.exists(index_path):
        return []

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks: List[Dict] = json.load(f)

    index = load_index(index_path)

    query_vec = model.encode([query]).astype("float32")
    k = min(50, len(chunks))
    distances, indices = index.search(query_vec, k)

    candidates = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        chunk = chunks[idx].copy()
        chunk["faiss_distance"] = float(dist)
        candidates.append(chunk)

    if not candidates:
        return []

    query_lower = query.lower().strip()
    query_terms = query_lower.split()

    for chunk in candidates:
        name = chunk.get("name", "").lower()
        code_snippet = chunk.get("code", "").lower()
        c_type = chunk.get("type", "").lower()
        file_path = chunk.get("file_path", "").lower()

        score = 0

        for term in query_terms:
            if term in name:
                score += 4
            if term in code_snippet:
                score += 2

        if c_type == "class":
            score += 3
        elif c_type == "function":
            score += 2

        if any(k in name for k in ["app", "route", "router", "middleware", "request", "call", "dispatch"]):
            score += 10

        if any(k in file_path for k in ["routing", "applications", "middleware", "requests"]):
            score += 15

        if any(k in file_path for k in ["docs", "tests", "examples", "security", "oauth"]):
            score -= 10

        chunk["keyword_score"] = score

    rerank_pairs = [
        (query, f"Code:\n{c.get('code', '')[:500]}")
        for c in candidates
    ]

    rerank_scores = reranker.predict(rerank_pairs)

    for chunk, r_score in zip(candidates, rerank_scores):
        chunk["rerank_score"] = float(r_score)

    def calculate_final(c):
        return (
            c.get("rerank_score", 0) * 4.0 +
            c.get("keyword_score", 0) * 2.0 +
            (-c.get("faiss_distance", 0) * 0.8)
        )

    candidates.sort(key=calculate_final, reverse=True)

    filtered = []
    seen = set()

    for c in candidates:
        key = (c["file_path"], c.get("start_line", 0))
        if key in seen:
            continue
        seen.add(key)

        file_path = c["file_path"].lower()
        name = c.get("name", "").lower()

        if any(x in file_path for x in ["test", "__pycache__", "node_modules"]):
            continue

        if not any(k in file_path for k in ["routing", "applications", "middleware", "requests"]):
            continue

        if not any(k in name for k in ["call", "handle", "dispatch", "request", "route", "endpoint"]):
            continue

        filtered.append(c)

    return filtered[:8]


def prepare_context(results: List[Dict]) -> str:
    if not results:
        return "No relevant code chunks found."

    MAX_CHARS = 5000

    file_paths = [r['file_path'] for r in results]
    primary_file = Counter(file_paths).most_common(1)[0][0]

    full_file_code = ""

    if os.path.exists(primary_file):
        try:
            with open(primary_file, "r", encoding="utf-8", errors="ignore") as f:
                full_file_code = f.read()
        except:
            full_file_code = ""

    if full_file_code:
        trimmed_code = full_file_code[:MAX_CHARS]
        primary_context = f"""--- MAIN FILE (trimmed): {os.path.basename(primary_file)} ---
{trimmed_code}
"""
    else:
        primary_context = ""

    other_parts = []
    for i, r in enumerate(results, 1):
        if r['file_path'] == primary_file:
            continue

        code = r.get("code", "")[:800]

        part = f"""[Chunk {i}]
File: {r['file_path']}
Name: {r.get('name')}
Code:
{code}
"""
        other_parts.append(part)

    return primary_context + "\n--- OTHER RELEVANT SNIPPETS ---\n" + "\n\n".join(other_parts)
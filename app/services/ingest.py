import os
import json
from git import Repo
from app.core.config import settings
from app.services.ast_parser import ast_chunks
from app.services.embedder import embed_chunks
from app.services.vector_store import build_faiss_index, save_index


def ingest_repo(repo_url: str):
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")

    repo_path = os.path.join(settings.REPO_DIR, repo_name)
    repo_data_path = os.path.join(settings.DATA_DIR, repo_name)

    os.makedirs(repo_data_path, exist_ok=True)

    chunks_path = os.path.join(repo_data_path, "chunks.json")
    index_path = os.path.join(repo_data_path, "code_index.faiss")

    if not os.path.exists(repo_path):
        Repo.clone_from(repo_url, repo_path)

    all_chunks = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", "node_modules"]]

        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                all_chunks.extend(ast_chunks(file_path))

    if not all_chunks:
        return {"error": "No Python files found"}

    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2)

    embeddings = embed_chunks(all_chunks)
    index = build_faiss_index(embeddings)
    save_index(index, index_path)

    return {
        "status": "success",
        "repo": repo_name,
        "chunks": len(all_chunks)
    }
import os
import traceback
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from groq import Groq
import traceback

from app.services.ingest import ingest_repo   
from app.services.search import search_repo, prepare_context
from app.core.config import settings

router = APIRouter()

def get_client():
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")
    return Groq(api_key=settings.GROQ_API_KEY)

class IngestRequest(BaseModel):
    repo_url: str

@router.get("/")
def root():
    return {
        "status": "ok", 
        "service": "CodeLens", 
        "using_key": bool(settings.GROQ_API_KEY)
    }

@router.post("/ingest")
async def start_ingest(request: IngestRequest, background_tasks: BackgroundTasks):
    repo_name = request.repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    background_tasks.add_task(ingest_repo, request.repo_url)
    return {
        "status": "queued",
        "repo": repo_name
    }

try:
    client = get_client()
except Exception as e:
    print("Error initializing Groq client:", str(e))
    traceback.print_exc()
    client = None

@router.get("/search")
def search(query: str, repo: str):
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    results = search_repo(query, repo)

    if isinstance(results, dict) and "error" in results:
        raise HTTPException(status_code=404, detail=results["error"])

    if not results:
        return {"answer": "No relevant code found for this query.", "sources": []}

    context = prepare_context(results)

    prompt = f"""
You are a strict code execution tracer.

Your job is to extract the REAL execution flow from the given code.

Rules:
- Output MUST be a numbered flow (1 → N)
- Each step MUST reference a real function/class from the context
- Use format: STEP X → <function/class> → what it does
- DO NOT give high-level abstractions like "ASGI handles request"
- DO NOT generalize or summarize
- ONLY use concrete names from code (functions, classes, methods)
- If exact flow is not visible, say: "Flow not fully visible in provided code"
- Keep steps tight and technical

Context:
{context}

Question: {query}

Answer:
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1200
        )
        raw_answer = response.choices[0].message.content
        answer = raw_answer.strip()
    except Exception as e:
        answer = f"Failed to generate answer: {str(e)}"

    sources = [
        {
            "file": r["file_path"],
            "lines": f"{r.get('start_line', 0)}-{r.get('end_line', 0)}",
            "name": r.get("name", "unknown"),
            "type": r.get("type", "chunk")
        }
        for r in results
    ]

    return {
        "answer": answer,
        "sources": sources,
        "chunks_used": len(results)
    }
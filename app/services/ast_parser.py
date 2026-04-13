import ast
from typing import List, Dict

MAX_CHARS = 2800
MIN_CHARS = 120

def get_docstring(node) -> str:
    return ast.get_docstring(node) or ""

def extract_calls(node) -> List[str]:
    calls = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                calls.append(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                calls.append(child.func.attr)
    return list(set(calls))

def _extract_chunks(node, lines: list, file_path: str, parent_name: str = None) -> List[Dict]:
    chunks = []
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return chunks

    start = node.lineno - 1
    end = getattr(node, 'end_lineno', len(lines))
    chunk_code = "".join(lines[start:end]).strip()

    if len(chunk_code) < MIN_CHARS:
        return chunks

    chunk_type = "function" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "class"
    docstring = get_docstring(node)
    calls = extract_calls(node)

    chunk = {
        "type": chunk_type,
        "name": node.name,
        "file_path": file_path,
        "code": chunk_code,
        "start_line": start,
        "end_line": end - 1,
        "docstring": docstring,
        "calls": calls,
        "parent": parent_name
    }
    chunks.append(chunk)

    if isinstance(node, ast.ClassDef):
        for child in node.body:
            chunks.extend(_extract_chunks(child, lines, file_path, parent_name=node.name))

    return chunks

def ast_chunks(path: str) -> List[Dict]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
    except Exception:
        return []

    try:
        tree = ast.parse(code)
    except Exception:
        return []

    lines = code.splitlines(keepends=True)
    all_chunks = []

    for node in tree.body:
        all_chunks.extend(_extract_chunks(node, lines, path))

    return all_chunks
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_chunks(chunks):
    texts = []
    for chunk in chunks:
        doc = chunk.get("docstring", "")
        text = f"{chunk['type']} {chunk['name']}\n{doc}\n{chunk['code']}"
        texts.append(text)

    embeddings = model.encode(texts, batch_size=32, show_progress_bar=False)
    return np.array(embeddings).astype("float32")
import faiss


def build_faiss_index(embeddings):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index


def save_index(index, path: str):
    faiss.write_index(index, path)


def load_index(path: str):
    return faiss.read_index(path)
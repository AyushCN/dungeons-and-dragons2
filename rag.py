import os
import requests
import numpy as np
import faiss

EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"

def get_embedding(text):
    res = requests.post(
        EMBED_URL,
        json={"model": EMBED_MODEL, "prompt": text}
    )
    return np.array(res.json()["embedding"], dtype="float32")

def load_rule_chunks():
    chunks = []
    for filename in os.listdir("rules"):
        with open(f"rules/{filename}", "r") as f:
            content = f.read()

            # Split rules by blank line
            parts = content.split("\n\n")
            for part in parts:
                if part.strip():
                    chunks.append(part.strip())

    return chunks

def build_index(chunks):
    embeddings = [get_embedding(chunk) for chunk in chunks]
    dimension = len(embeddings[0])

    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings))

    return index

def retrieve(query, chunks, index, top_k=2):
    query_vec = get_embedding(query)
    D, I = index.search(np.array([query_vec]), top_k)
    return [chunks[i] for i in I[0]]

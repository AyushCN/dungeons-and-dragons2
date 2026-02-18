import requests

res = requests.post(
    "http://localhost:11434/api/embeddings",
    json={
        "model": "nomic-embed-text",
        "prompt": "attack roll rules"
    }
)

print(res.status_code)
print(len(res.json()["embedding"]))

from rag import load_rule_chunks, build_index, retrieve

chunks = load_rule_chunks()
index = build_index(chunks)

query = "What happens on a critical hit?"
results = retrieve(query, chunks, index)

for r in results:
    print("----")
    print(r)

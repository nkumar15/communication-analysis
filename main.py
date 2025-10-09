import numpy as np
from sentence_transformers import SentenceTransformer
import faiss


# Step 1: Prepare sample documents
documents = [
    "AI helps doctors detect diseases faster.",
    "Machine learning models analyze medical data.",
    "Cats and dogs are common pets.",
    "Hospitals use AI to improve diagnostics.",
    "Deep learning enhances computer vision tasks."
]

# Step 2: Load a pre-trained sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Step 3 : Chunk the documents with 20% overlap
def chunk_document(doc, chunk_size=10, overlap=2):
    words = doc.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = words[i:i + chunk_size]
        if chunk:
            chunks.append(' '.join(chunk))
    return chunks

documents = [chunk for doc in documents for chunk in chunk_document(doc)]

# Step 4: Generate embeddings for the documents
embeddings = model.encode(documents)

# Step 5: Create a FAISS index and add embeddings
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings).astype('float32'))
print(f"Number of documents indexed: {index.ntotal}")

# Step 6: Perform a similarity search
query = "How is AI used in healthcare?"
query_embedding = model.encode([query]).astype('float32')
k = 3  # Number of nearest neighbors to retrieve
distances, indices = index.search(query_embedding, k)  
print("Top 3 similar documents:")
for idx in indices[0]:
    print(f"- {documents[idx]}")
    
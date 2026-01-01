from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import os

print("Testing HuggingFaceEmbedding instantiation...")

try:
    # Try cache_folder
    print("Attempt 1: cache_folder='./cache'")
    model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5", cache_folder="./cache")
    print("Success with cache_folder")
except Exception as e:
    print(f"Failed with cache_folder: {e}")

try:
    # Try cache_dir (common alternative)
    print("\nAttempt 2: cache_dir='./cache'")
    model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5", cache_dir="./cache")
    print("Success with cache_dir")
except Exception as e:
    print(f"Failed with cache_dir: {e}")

try:
    # Try without explicit cache (relying on Env)
    print("\nAttempt 3: No cache arg")
    model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    print("Success with No cache arg")
except Exception as e:
    print(f"Failed with No cache arg: {e}")

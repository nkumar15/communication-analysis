from llama_index.embeddings.openai import OpenAIEmbedding
import os

print("Testing OpenAIEmbedding instantiation...")

try:
    print("Attempt 1: model='text-embedding-3-small'")
    embed = OpenAIEmbedding(model="text-embedding-3-small")
    print("Success with model arg")
    print(embed.get_text_embedding("test"))
    print("Success generating embedding")
except Exception as e:
    print(f"Failed execution: {e}")

try:
    print("\nAttempt 2: model_name='text-embedding-3-small'")
    embed = OpenAIEmbedding(model_name="text-embedding-3-small")
    print("Success with model_name arg")
except Exception as e:
    print(f"Failed with model_name arg: {e}")

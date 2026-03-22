import os
from dotenv import load_dotenv
load_dotenv()
# Test 1 - env keys loaded
groq_key = os.getenv("GROQ_API_KEY")
spoon_key = os.getenv("SPOONACULAR_API_KEY")
print("Groq key loaded:", "YES" if groq_key else "NO - check .env")
print("Spoonacular key loaded:", "YES" if spoon_key else "NO - check .env")
# Test 2 - chromadb works
import chromadb
client = chromadb.Client()
print("ChromaDB works: YES")
# Test 3 - sentence transformers works
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
vec = model.encode("test sentence")
print("Sentence Transformers works: YES, vector size:", len(vec))
# Test 4 - groq connection
from langchain_groq import ChatGroq
llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=groq_key)
response = llm.invoke([("human", "say hello in one word")])
print("Groq LLM works: YES, response:", response.content)

print("\n✅ ALL SYSTEMS GO — ready to build NourishIQ")
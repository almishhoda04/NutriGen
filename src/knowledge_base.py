import json
import os
import chromadb
from sentence_transformers import SentenceTransformer

# ── Paths ────────────────────────────────────────────────────────────────────
CLEAN_RECIPES_PATH = "data/recipes_clean.json"
CHROMA_PATH        = "data/chroma_db"
COLLECTION_NAME    = "recipes"

# ── Load model once at module level (reused across calls) ────────────────────
print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("✓ Model loaded")


def get_collection():
    """Returns the ChromaDB collection — creates it if it doesn't exist"""
    client     = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}  # cosine similarity
    )
    return collection


def build_document_string(recipe: dict) -> str:
    """
    Creates the text that gets embedded for each recipe.
    Richer text = better semantic search results.
    """
    cuisines  = ", ".join(recipe.get("cuisines", ["International"]))
    diets     = ", ".join(recipe.get("diets", []))
    allergens = ", ".join(recipe.get("allergens", []))

    doc = (
        f"{recipe['title']}. "
        f"Ingredients: {recipe['ingredients_text']}. "
        f"Cuisine: {cuisines}. "
        f"Diet tags: {diets}. "
        f"Ready in {recipe['prep_time_min']} minutes. "
        f"Calories: {recipe['calories']} kcal. "
        f"Protein: {recipe['protein_g']}g."
    )
    return doc


def build_knowledge_base():
    """Embeds all recipes and stores in ChromaDB"""

    # Load cleaned recipes
    with open(CLEAN_RECIPES_PATH, "r", encoding="utf-8") as f:
        recipes = json.load(f)
    print(f"✓ Loaded {len(recipes)} recipes from {CLEAN_RECIPES_PATH}")

    collection = get_collection()

    # Check if already built
    existing = collection.count()
    if existing > 0:
        print(f"⚠ Collection already has {existing} recipes.")
        answer = input("Rebuild from scratch? (y/n): ").strip().lower()
        if answer != "y":
            print("Skipping rebuild. Using existing knowledge base.")
            return
        # Delete and recreate
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        client.delete_collection(COLLECTION_NAME)
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        print("✓ Old collection deleted. Rebuilding...")

    print(f"\nEmbedding {len(recipes)} recipes...")

    ids         = []
    embeddings  = []
    documents   = []
    metadatas   = []

    for i, recipe in enumerate(recipes):
        doc       = build_document_string(recipe)
        embedding = model.encode(doc).tolist()

        ids.append(recipe["id"])
        embeddings.append(embedding)
        documents.append(doc)
        metadatas.append({
            "title":         recipe["title"],
            "calories":      int(recipe["calories"]),
            "protein_g":     float(recipe["protein_g"]),
            "carbs_g":       float(recipe["carbs_g"]),
            "fat_g":         float(recipe["fat_g"]),
            "prep_time_min": int(recipe["prep_time_min"]),
            "cuisines":      ", ".join(recipe.get("cuisines", [])),
            "diets":         ", ".join(recipe.get("diets", [])),
            "allergens":     ", ".join(recipe.get("allergens", [])),
        })

        if (i + 1) % 10 == 0:
            print(f"  Embedded {i+1}/{len(recipes)} recipes...")

    # Store everything in ChromaDB in one batch
    collection.add(
        ids        = ids,
        embeddings = embeddings,
        documents  = documents,
        metadatas  = metadatas,
    )

    print(f"\n✅ Knowledge base built. {collection.count()} recipes stored in ChromaDB.")


def test_search(query: str, n=3):
    """Quick test — search the knowledge base with a plain text query"""
    collection      = get_collection()
    query_embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n,
    )

    print(f"\nTop {n} results for: '{query}'")
    print("-" * 40)
    for i, (doc, meta) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0]
    )):
        print(f"{i+1}. {meta['title']}")
        print(f"   Calories: {meta['calories']} kcal | "
              f"Protein: {meta['protein_g']}g | "
              f"Prep: {meta['prep_time_min']} mins")
        print()


# ── Run directly to build + test ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("NutriGen — Knowledge Base Builder")
    print("=" * 50 + "\n")

    build_knowledge_base()

    print("\n--- Testing search ---")
    test_search("high protein Indian breakfast")
    test_search("quick low carb dinner")
    test_search("gluten free vegetarian lunch")
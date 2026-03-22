import os
import json
from sentence_transformers import SentenceTransformer
import chromadb
from src.user_profile import UserProfile, CONDITION_MODIFIERS
from src.drug_food import get_foods_to_avoid

# ── Paths ────────────────────────────────────────────────────────────────────
CHROMA_PATH     = "data/chroma_db"
COLLECTION_NAME = "recipes"
CLEAN_PATH      = "data/recipes_clean.json"

# ── Load model once ───────────────────────────────────────────────────────────
model = SentenceTransformer('all-MiniLM-L6-v2')


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )


def load_recipe_by_id(recipe_id: str) -> dict:
    """Fetch full recipe details from the JSON file by ID"""
    with open(CLEAN_PATH, "r", encoding="utf-8") as f:
        recipes = json.load(f)
    for r in recipes:
        if r["id"] == recipe_id:
            return r
    return {}


def build_query(profile: UserProfile, meal_slot: str) -> str:
    """
    Builds a rich semantic query string from the user profile.
    The better the query, the more relevant the results.
    """
    # Base: meal slot + cuisine preference
    cuisines = " or ".join(profile.cuisine_preference) if profile.cuisine_preference else "healthy"
    query    = f"{meal_slot} {cuisines} meal"

    # Add condition-based modifiers
    modifiers = profile.get_condition_query_modifiers()
    if modifiers:
        query += f" {modifiers}"

    # Add goal-based modifier
    if profile.goal == "muscle_gain":
        query += " high protein"
    elif profile.goal == "weight_loss":
        query += " low calorie light"
    elif profile.goal == "maintain":
        query += " balanced nutritious"

    return query


def is_recipe_safe(meta: dict, profile: UserProfile, foods_to_avoid: list) -> bool:
    """
    Hard constraint checker — returns False if recipe violates
    any of the user's intolerances or medication restrictions.
    This runs AFTER retrieval to filter out unsafe results.
    """
    recipe_allergens = [a.strip().lower() for a in meta.get("allergens", "").split(",")]
    recipe_text      = (meta.get("title", "") + " " + meta.get("diets", "")).lower()

    # Check intolerances
    for intolerance in profile.intolerances:
        if intolerance.lower() in recipe_allergens:
            return False

    # Check drug-food interactions
    for food in foods_to_avoid:
        if food.lower() in recipe_text:
            return False

    return True

def get_suitable_recipes(
    profile:   UserProfile,
    meal_slot: str,
    n:         int = 8,
    exclude_titles: list = [],
) -> list:
    """
    Main retriever function.
    Strategy: fetch more than needed → filter hard constraints → return top n.
    exclude_titles: list of recipe titles already used — avoids repetition.
    """
    import random

    collection     = get_collection()
    targets        = profile.calculate_targets()
    cal_per_meal   = targets["calories"] // profile.meals_per_day
    foods_to_avoid = get_foods_to_avoid(profile.medications)

    # ── Build semantic query ─────────────────────────────────────────────────
    query           = build_query(profile, meal_slot)
    query_embedding = model.encode(query).tolist()

    # ── Fetch top 60 candidates ──────────────────────────────────────────────
    fetch_count = min(60, collection.count())
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=fetch_count,
    )

    docs      = results["documents"][0]
    metadatas = results["metadatas"][0]
    ids       = results["ids"][0]

    # ── Apply hard constraint filters ────────────────────────────────────────
    suitable = []
    for doc, meta, rid in zip(docs, metadatas, ids):

        # 1. Skip already used recipes
        if meta.get("title", "") in exclude_titles:
            continue

        # 2. Prep time must fit
        if meta.get("prep_time_min", 999) > profile.meal_prep_time:
            continue

        # 3. Calorie range check
        cal = meta.get("calories", 0)
        if cal > 0:
            if cal > cal_per_meal * 1.5:
                continue
            if cal < cal_per_meal * 0.3:
                continue

        # 4. Safety check
        if not is_recipe_safe(meta, profile, foods_to_avoid):
            continue

        suitable.append({
            "id":            rid,
            "title":         meta.get("title", "Unknown"),
            "calories":      meta.get("calories", 0),
            "protein_g":     meta.get("protein_g", 0),
            "carbs_g":       meta.get("carbs_g", 0),
            "fat_g":         meta.get("fat_g", 0),
            "prep_time_min": meta.get("prep_time_min", 0),
            "cuisines":      meta.get("cuisines", ""),
            "diets":         meta.get("diets", ""),
            "allergens":     meta.get("allergens", ""),
            "document":      doc,
        })

    # ── Shuffle the suitable pool so we don't always get the same top N ──────
    random.shuffle(suitable)

    # ── Fallback: relax calorie constraint if too few ────────────────────────
    if len(suitable) < 2:
        suitable = []
        for doc, meta, rid in zip(docs, metadatas, ids):
            if meta.get("title", "") in exclude_titles:
                continue
            if meta.get("prep_time_min", 999) > profile.meal_prep_time:
                continue
            if not is_recipe_safe(meta, profile, foods_to_avoid):
                continue
            suitable.append({
                "id":            rid,
                "title":         meta.get("title", "Unknown"),
                "calories":      meta.get("calories", 0),
                "protein_g":     meta.get("protein_g", 0),
                "carbs_g":       meta.get("carbs_g", 0),
                "fat_g":         meta.get("fat_g", 0),
                "prep_time_min": meta.get("prep_time_min", 0),
                "cuisines":      meta.get("cuisines", ""),
                "diets":         meta.get("diets", ""),
                "allergens":     meta.get("allergens", ""),
                "document":      doc,
            })
        random.shuffle(suitable)

    return suitable[:n]


# ── Run directly to test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    from src.user_profile import UserProfile

    print("=" * 50)
    print("NutriGen — Retriever Test")
    print("=" * 50)

    # Test Profile 1 — Diabetic vegetarian
    p1 = UserProfile(
        name="Priya", age=35, gender="female",
        weight_kg=62, height_cm=160,
        activity_level="light", goal="weight_loss",
        health_conditions=["diabetes_type2"],
        intolerances=["lactose"],
        cuisine_preference=["Indian", "Mediterranean"],
        meal_prep_time=30, meals_per_day=3,
    )

    print(f"\nProfile: {p1.name} | Goal: {p1.goal} | Conditions: {p1.health_conditions}")
    print(f"Targets: {p1.calculate_targets()}")
    print(f"Query built: '{build_query(p1, 'breakfast')}'")

    for slot in ["breakfast", "lunch", "dinner"]:
        recipes = get_suitable_recipes(p1, slot, n=3)
        print(f"\n── {slot.upper()} options ({len(recipes)} found) ──")
        for r in recipes:
            print(f"  • {r['title']:<40} | {r['calories']} kcal | "
                  f"P:{r['protein_g']}g | Prep:{r['prep_time_min']}min")

    print("\n" + "=" * 50)

    # Test Profile 2 — Gym goer with nut allergy
    p2 = UserProfile(
        name="Arjun", age=22, gender="male",
        weight_kg=75, height_cm=178,
        activity_level="active", goal="muscle_gain",
        health_conditions=[],
        intolerances=["nuts"],
        cuisine_preference=["Continental"],
        meal_prep_time=45, meals_per_day=3,
    )

    print(f"\nProfile: {p2.name} | Goal: {p2.goal} | Intolerances: {p2.intolerances}")
    print(f"Targets: {p2.calculate_targets()}")

    for slot in ["breakfast", "lunch", "dinner"]:
        recipes = get_suitable_recipes(p2, slot, n=3)
        print(f"\n── {slot.upper()} options ({len(recipes)} found) ──")
        for r in recipes:
            print(f"  • {r['title']:<40} | {r['calories']} kcal | "
                  f"P:{r['protein_g']}g | Prep:{r['prep_time_min']}min")
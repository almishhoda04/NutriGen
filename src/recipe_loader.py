import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("SPOONACULAR_API_KEY")

# ── These queries give you diverse, well-distributed recipes ─────────────────
# SEARCH_QUERIES = [
#     "high protein breakfast",
#     "low carb dinner",
#     "diabetic friendly meal",
#     "Indian vegetarian",
#     "Mediterranean lunch",
#     "low sodium heart healthy",
#     "gluten free meal",
#     "quick healthy meal",
#     "high fiber vegetarian",
#     "muscle gain meal prep",
# ]
# SEARCH_QUERIES = [
#     "low calorie lunch",
#     "high protein lunch",
#     "vegetarian dinner",
#     "weight loss breakfast",
#     "anti inflammatory meal",
#     "low fat dinner",
#     "iron rich meal",
#     "calcium rich meal",
#     "keto friendly dinner",
#     "high fiber breakfast",
# ]
# SEARCH_QUERIES = [
#     "paneer Indian curry",
#     "dal lentil Indian",
#     "chicken tikka masala",
#     "idli dosa South Indian",
#     "rajma chana Indian",
#     "Greek salad Mediterranean",
#     "hummus chickpea Mediterranean",
#     "Japanese miso soup",
#     "Mexican black bean",
#     "French omelette breakfast",
# ]
# SEARCH_QUERIES = [
#     "pcos friendly meal",
#     "thyroid friendly recipe",
#     "IBS low fodmap dinner",
#     "diabetic Indian recipe",
#     "high protein egg breakfast",
#     "post workout chicken meal",
#     "iron rich spinach meal",
#     "calcium rich dairy free",
#     "heart healthy oats breakfast",
#     "anti inflammatory turmeric meal",
# ]
# SEARCH_QUERIES = [
#     "stuffed bell pepper dinner",
#     "quinoa salad lunch",
#     "turkey meatball meal",
#     "baked salmon dinner",
#     "tofu stir fry Asian",
#     "lentil soup vegetarian",
#     "chickpea curry Indian",
#     "avocado egg breakfast",
#     "sweet potato meal",
#     "mushroom risotto dinner",
# ]
SEARCH_QUERIES = [
    "cottage cheese high protein breakfast",
    "cauliflower rice low carb",
    "beetroot salad iron rich",
    "moong dal Indian breakfast",
    "palak paneer spinach",
    "grilled chicken Mediterranean",
    "black bean burrito Mexican",
    "overnight oats breakfast",
    "zucchini noodles low calorie",
    "tempeh vegan protein",
]

# ── How many recipes per query (150 points/day limit on free tier) ───────────
PER_QUERY = 10   # 10 queries x 10 = 100 recipes per run, safe within free limit


def fetch_recipes(queries: list, per_query: int) -> list:
    """Fetch recipes from Spoonacular with full nutrition info"""
    all_recipes = []
    seen_ids = set()

    for i, query in enumerate(queries):
        print(f"Fetching query {i+1}/{len(queries)}: '{query}'...")

        url = "https://api.spoonacular.com/recipes/complexSearch"
        params = {
            "apiKey":               API_KEY,
            "query":                query,
            "number":               per_query,
            "addRecipeInformation": True,
            "addRecipeNutrition":   True,
            "fillIngredients":      True,
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()

            if "results" not in data:
                print(f"  ⚠ No results or API error: {data.get('message', 'unknown error')}")
                continue

            new_count = 0
            for recipe in data["results"]:
                if recipe["id"] not in seen_ids:
                    seen_ids.add(recipe["id"])
                    all_recipes.append(recipe)
                    new_count += 1

            print(f"  ✓ Got {new_count} new recipes (total so far: {len(all_recipes)})")

        except Exception as e:
            print(f"  ✗ Error on query '{query}': {e}")

        time.sleep(1)  # be polite to the API

    return all_recipes


def extract_nutrients(nutrition_data: dict) -> dict:
    """Pull calories, protein, carbs, fat from Spoonacular nutrition block"""
    nutrients = {}
    if not nutrition_data:
        return {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}

    for n in nutrition_data.get("nutrients", []):
        name = n.get("name", "").lower()
        amount = n.get("amount", 0)
        if "calorie" in name:
            nutrients["calories"] = round(amount)
        elif name == "protein":
            nutrients["protein_g"] = round(amount, 1)
        elif name == "carbohydrates":
            nutrients["carbs_g"] = round(amount, 1)
        elif name == "fat":
            nutrients["fat_g"] = round(amount, 1)

    # fill missing keys with 0
    for key in ["calories", "protein_g", "carbs_g", "fat_g"]:
        nutrients.setdefault(key, 0)

    return nutrients


def clean_recipes(raw_recipes: list) -> list:
    """Convert raw Spoonacular response into clean flat dicts"""
    cleaned = []

    for r in raw_recipes:
        try:
            # ── Ingredients as a readable string ────────────────────────────
            ingredients = r.get("extendedIngredients", [])
            ingredients_text = ", ".join(
                [ing.get("originalName", ing.get("name", "")) for ing in ingredients]
            )

            # ── Instructions as plain text ───────────────────────────────────
            instructions_list = r.get("analyzedInstructions", [])
            steps = []
            if instructions_list:
                for step in instructions_list[0].get("steps", []):
                    steps.append(step.get("step", ""))
            instructions_text = " ".join(steps)

            # ── Diets and dish types ─────────────────────────────────────────
            diets     = r.get("diets", [])
            cuisines  = r.get("cuisines", []) or ["International"]
            dish_types = r.get("dishTypes", [])

            # ── Allergens from Spoonacular's boolean flags ───────────────────
            allergens = []
            if not r.get("dairyFree", True):     allergens.append("lactose")
            if not r.get("glutenFree", True):    allergens.append("gluten")
            if r.get("veryPopular", False) is False:
                pass  # not an allergen signal
            # check ingredient text for common allergens
            ing_lower = ingredients_text.lower()
            if "peanut" in ing_lower or "almond" in ing_lower or "walnut" in ing_lower:
                allergens.append("nuts")
            if "egg" in ing_lower:
                allergens.append("eggs")
            if "soy" in ing_lower or "tofu" in ing_lower:
                allergens.append("soy")

            # ── Nutrition ────────────────────────────────────────────────────
            nutrients = extract_nutrients(r.get("nutrition", {}))

            cleaned.append({
                "id":                str(r["id"]),
                "title":             r.get("title", "Unknown Recipe"),
                "ingredients_text":  ingredients_text,
                "instructions_text": instructions_text[:500],  # cap length
                "prep_time_min":     r.get("readyInMinutes", 30),
                "servings":          r.get("servings", 2),
                "cuisines":          cuisines,
                "diets":             diets,
                "dish_types":        dish_types,
                "allergens":         allergens,
                "calories":          nutrients["calories"],
                "protein_g":         nutrients["protein_g"],
                "carbs_g":           nutrients["carbs_g"],
                "fat_g":             nutrients["fat_g"],
                "source_url":        r.get("sourceUrl", ""),
                "image":             r.get("image", ""),
            })

        except Exception as e:
            print(f"  ⚠ Skipping recipe '{r.get('title', 'unknown')}': {e}")
            continue

    return cleaned


def save_recipes(recipes: list, path: str):
    """Save cleaned recipes to JSON"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(recipes, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved {len(recipes)} recipes to {path}")


def load_recipes(path: str) -> list:
    """Load recipes from saved JSON"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Run this file directly to fetch and save recipes ────────────────────────
if __name__ == "__main__":
    RAW_PATH   = "data/recipes_raw.json"
    CLEAN_PATH = "data/recipes_clean.json"

    print("=" * 50)
    print("NutriGen — Recipe Fetcher")
    print("=" * 50)

    # Fetch new batch
    raw = fetch_recipes(SEARCH_QUERIES, PER_QUERY)
    save_recipes(raw, RAW_PATH)

    # Clean new batch
    print("\nCleaning recipes...")
    new_cleaned = clean_recipes(raw)

    # Load existing recipes if file exists and MERGE
    if os.path.exists(CLEAN_PATH):
        with open(CLEAN_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)
        existing_ids = {r["id"] for r in existing}
        added  = [r for r in new_cleaned if r["id"] not in existing_ids]
        merged = existing + added
        print(f"✓ Added {len(added)} new unique recipes to existing {len(existing)}")
    else:
        merged = new_cleaned
        print(f"✓ Starting fresh with {len(merged)} recipes")

    save_recipes(merged, CLEAN_PATH)
    print(f"\n✅ Total recipes now: {len(merged)} in {CLEAN_PATH}")

    # Quick preview
    if new_cleaned:
        print("\nSample new recipe:")
        sample = new_cleaned[0]
        print(f"  Title:     {sample['title']}")
        print(f"  Calories:  {sample['calories']} kcal")
        print(f"  Cuisines:  {sample['cuisines']}")
        print(f"  Allergens: {sample['allergens']}")
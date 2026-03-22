import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from src.user_profile import UserProfile
from src.retriever import get_suitable_recipes

load_dotenv()

# ── LLM setup ────────────────────────────────────────────────────────────────
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3,
)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are NutriGen, a clinical nutritionist AI.
Your job is to generate a personalized 7-day meal plan.

User Details:
- Name: {name}
- Goal: {goal}
- Daily Targets: {calories} kcal | {protein_g}g protein | {carbs_g}g carbs | {fat_g}g fat
- Health Conditions: {conditions}
- Intolerances (NEVER include these): {intolerances}
- Max prep time per meal: {prep_time} minutes
- Meals per day: {meals_per_day}

Rules:
1. ONLY recommend recipes from the provided candidate list
2. NEVER recommend anything containing the user's intolerances
3. Balance calories across the day to hit the daily target
4. Vary the meals — do not repeat the same recipe more than twice in a week
5. Output ONLY valid JSON — no explanation, no markdown, no extra text

Output format (strictly follow this):
{{
  "day_1": {{
    "breakfast": {{"recipe": "Recipe Name Here", "calories": 000, "note": "one line why this fits"}},
    "lunch":     {{"recipe": "Recipe Name Here", "calories": 000, "note": "one line why this fits"}},
    "dinner":    {{"recipe": "Recipe Name Here", "calories": 000, "note": "one line why this fits"}}
  }},
  "day_2": {{ ... }},
  "day_3": {{ ... }},
  "day_4": {{ ... }},
  "day_5": {{ ... }},
  "day_6": {{ ... }},
  "day_7": {{ ... }}
}}"""


def format_candidates(candidates: list) -> str:
    """Formats recipe candidates into a readable string for the LLM prompt"""
    if not candidates:
        return "No specific candidates — use your nutritional knowledge."
    lines = []
    for r in candidates:
        lines.append(
            f"- {r['title']} | {r['calories']} kcal | "
            f"Protein: {r['protein_g']}g | Prep: {r['prep_time_min']} mins"
        )
    return "\n".join(lines)


def generate_meal_plan(profile: UserProfile) -> dict:
    """
    Generates a 7-day meal plan.
    Each day gets freshly shuffled candidates.
    Used recipes are tracked to prevent repetition across the week.
    """
    targets = profile.calculate_targets()
    full_plan = {}
    used_titles = []  # track all used recipes across the week

    print("Generating 7-day meal plan day by day...")

    for day_num in range(1, 8):
        print(f"  Planning day {day_num}...")

        # Fresh candidates per day — shuffled differently each call
        breakfast_options = get_suitable_recipes(
            profile, "breakfast", n=8, exclude_titles=used_titles)
        lunch_options = get_suitable_recipes(
            profile, "lunch", n=8, exclude_titles=used_titles)
        dinner_options = get_suitable_recipes(
            profile, "dinner", n=8, exclude_titles=used_titles)

        system = SYSTEM_PROMPT.format(
            name          = profile.name,
            goal          = profile.goal,
            calories      = targets["calories"],
            protein_g     = targets["protein_g"],
            carbs_g       = targets["carbs_g"],
            fat_g         = targets["fat_g"],
            conditions    = ", ".join(profile.health_conditions) or "none",
            intolerances  = ", ".join(profile.intolerances) or "none",
            prep_time     = profile.meal_prep_time,
            meals_per_day = profile.meals_per_day,
        )

        user_message = f"""
Generate the meal plan for DAY {day_num} ONLY.

BREAKFAST OPTIONS (pick exactly 1):
{format_candidates(breakfast_options)}

LUNCH OPTIONS (pick exactly 1):
{format_candidates(lunch_options)}

DINNER OPTIONS (pick exactly 1):
{format_candidates(dinner_options)}

Already used this week (DO NOT repeat these):
{', '.join(used_titles) if used_titles else 'none yet'}

Output ONLY this JSON for day {day_num}:
{{
  "breakfast": {{"recipe": "Exact Recipe Name", "calories": 000, "note": "one line reason"}},
  "lunch":     {{"recipe": "Exact Recipe Name", "calories": 000, "note": "one line reason"}},
  "dinner":    {{"recipe": "Exact Recipe Name", "calories": 000, "note": "one line reason"}}
}}
"""

        response = llm.invoke([
            ("system", system),
            ("human",  user_message),
        ])

        raw = response.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            day_plan = json.loads(raw)
            full_plan[f"day_{day_num}"] = day_plan

            # Track used recipes so next day avoids them
            for slot in ["breakfast", "lunch", "dinner"]:
                title = day_plan.get(slot, {}).get("recipe", "")
                if title and title not in used_titles:
                    used_titles.append(title)

        except json.JSONDecodeError as e:
            print(f"  ✗ JSON parse error on day {day_num}: {e}")
            # Use empty placeholder so plan still continues
            full_plan[f"day_{day_num}"] = {
                "breakfast": {"recipe": "Parse error", "calories": 0, "note": ""},
                "lunch":     {"recipe": "Parse error", "calories": 0, "note": ""},
                "dinner":    {"recipe": "Parse error", "calories": 0, "note": ""},
            }

    print(f"✓ Plan complete. Used {len(used_titles)} unique recipes across the week.")
    return full_plan

def display_plan(plan: dict, targets: dict):
    """Pretty prints the meal plan in the terminal"""
    if not plan:
        print("No plan to display.")
        return

    print("\n" + "=" * 60)
    print("YOUR 7-DAY MEAL PLAN")
    print(f"Daily target: {targets['calories']} kcal | "
          f"P:{targets['protein_g']}g | "
          f"C:{targets['carbs_g']}g | "
          f"F:{targets['fat_g']}g")
    print("=" * 60)

    for day, meals in plan.items():
        print(f"\n📅 {day.replace('_', ' ').upper()}")
        for slot, details in meals.items():
            print(f"  {slot.capitalize():<12} {details['recipe']:<45} "
                  f"~{details.get('calories', '?')} kcal")
            print(f"  {'':12} {details.get('note', '')}")


# ── Run directly to test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("NutriGen — Meal Plan Generator Test")
    print("=" * 60)

    test_profile = UserProfile(
        name="Priya", age=35, gender="female",
        weight_kg=62, height_cm=160,
        activity_level="light", goal="weight_loss",
        health_conditions=["diabetes_type2"],
        intolerances=["lactose"],
        cuisine_preference=["Indian", "Mediterranean"],
        meal_prep_time=30, meals_per_day=3,
    )

    plan    = generate_meal_plan(test_profile)
    targets = test_profile.calculate_targets()
    display_plan(plan, targets)

    # Save for inspection
    with open("data/test_plan.json", "w") as f:
        json.dump(plan, f, indent=2)
    print("\n✓ Plan saved to data/test_plan.json")